"""Template management endpoints"""

from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
import logging

from ..utils.auth import require_auth
from ..utils.database import get_db
from ..models.template import Template, template_schema
from ..utils.aql import AQLCalculator
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)

template_bp = Blueprint("template", __name__, url_prefix="/api/templates")

# -----------------------------------------------------------------------------
# List templates (role dependent)
# -----------------------------------------------------------------------------

@template_bp.route("/", methods=["GET"])
@require_auth
def list_templates():
    """List templates based on user role."""
    user = request.current_user
    db = get_db()
    collection = db.get_collection("templates")

    # Build query based on role
    if user["role"] == "manager":
        # Managers see templates assigned to them
        query = {"manager_id": ObjectId(user["user_id"])}
    elif user["role"] == "inspector":
        # Inspectors see published templates
        query = {"status": "published"}
    else:
        # IT staff see all templates
        query = {}

    # Optional status filter (?status=published,submitted,manager_edit)
    status = (request.args.get("status") or "").strip()
    if status:
        query["status"] = status

    cursor = collection.find(query).sort("created_at", -1)
    tpl_list = []
    for doc in cursor:
        tpl = Template.from_dict(doc)
        tpl_list.append(tpl.public_view())

    return jsonify({"success": True, "data": tpl_list})


# -----------------------------------------------------------------------------
# Manager – list templates awaiting review (assigned to manager)
# -----------------------------------------------------------------------------

@template_bp.route("/assigned", methods=["GET"])
@require_auth
def list_assigned_to_manager():
    user = request.current_user
    if user["role"] != "manager":
        return jsonify({"success": False, "message": "Only managers can view assigned templates"}), 403

    db = get_db()
    collection = db.get_collection("templates")
    query = {
        "manager_id": ObjectId(user["user_id"]),
        "status": {"$in": ["submitted", "manager_edit"]}
    }
    cursor = collection.find(query).sort("updated_at", -1)
    out = [Template.from_dict(doc).public_view() for doc in cursor]
    return jsonify({"success": True, "data": out})


# -----------------------------------------------------------------------------
# Defect master list (managed by IT)
# -----------------------------------------------------------------------------

@template_bp.route("/defects", methods=["GET", "PUT"])
@require_auth
def defect_master_list():
    """GET returns the current defect master list (codes mapped to categories).

    PUT (IT only) updates the master list. Payload example:
    {
      "critical": ["CRIT_001", "CRIT_002"],
      "major": ["MAJ_001"],
      "minor": ["MIN_001", "MIN_010"]
    }
    """
    user = request.current_user
    db = get_db()
    coll = db.get_collection("defect_master")

    if request.method == "GET":
        doc = coll.find_one({}) or {"critical": [], "major": [], "minor": []}
        if doc.get("_id"):
            doc["_id"] = str(doc["_id"])  # hide ObjectId
        return jsonify({"success": True, "data": doc})

    # PUT
    if user["role"] != "it":
        return jsonify({"success": False, "message": "Only IT can update defect master list"}), 403
    payload = request.get_json() or {}
    allowed = {"critical": list, "major": list, "minor": list}
    update_doc = {k: (payload.get(k) or []) for k in allowed.keys()}

    # Upsert single master-list doc
    coll.update_one({}, {"$set": update_doc}, upsert=True)
    doc = coll.find_one({})
    if doc.get("_id"):
        doc["_id"] = str(doc["_id"])  # hide ObjectId
    return jsonify({"success": True, "data": doc})


@template_bp.route("/", methods=["POST"])
@require_auth
def create_template():
    """IT person submits a new template and assigns to manager."""
    user = request.current_user
    if user["role"] != "it":
        return jsonify({"success": False, "message": "Only IT staff can create templates."}), 403

    payload = request.get_json() or {}
    print(f"Received template creation request from user {user['user_id']}: {payload}")
    
    # Basic validation before schema validation
    if not payload.get("title") or not payload["title"].strip():
        print("Validation failed: Template title is required")
        return jsonify({"success": False, "message": "Template title is required"}), 400
    
    if not payload.get("manager_email"):
        print("Validation failed: Manager email is required")
        return jsonify({"success": False, "message": "Manager email is required"}), 400
    
    if not payload.get("organization") or not payload["organization"].strip():
        print("Validation failed: Organization is required")
        return jsonify({"success": False, "message": "Organization is required"}), 400
    
    if not payload.get("location") or not payload["location"].strip():
        print("Validation failed: Location is required")
        return jsonify({"success": False, "message": "Location is required"}), 400
    
    if not payload.get("pages") or not isinstance(payload["pages"], list) or len(payload["pages"]) == 0:
        print("Validation failed: Template must have at least one page")
        return jsonify({"success": False, "message": "Template must have at least one page"}), 400
    
    try:
        validated = template_schema.load(payload)
        print(f"Schema validation passed for template: {validated['title']}")
    except ValidationError as e:
        print(f"Schema validation failed: {e.messages}")
        error_messages = []
        for field, errors in e.messages.items():
            if isinstance(errors, list):
                error_messages.extend([f"{field}: {error}" for error in errors])
            else:
                error_messages.append(f"{field}: {errors}")
        return jsonify({
            "success": False, 
            "message": "Validation error", 
            "details": error_messages
        }), 400

    db = get_db()
    collection = db.get_collection("templates")

    # ensure manager exists
    users_coll = db.get_collection("users")
    mgr_doc = users_coll.find_one({"email": validated["manager_email"]})
    if not mgr_doc:
        print(f"Manager not found: {validated['manager_email']}")
        return jsonify({"success": False, "message": f"Manager with email '{validated['manager_email']}' not found"}), 400
    if mgr_doc.get("role") != "manager":
        print(f"User is not a manager: {validated['manager_email']}")
        return jsonify({"success": False, "message": f"User '{validated['manager_email']}' is not a manager"}), 400

    print(f"Creating template for manager: {mgr_doc.get('firstName')} {mgr_doc.get('lastName')}")
    
    # Calculate AQL criteria if lot_size is provided
    aql_criteria = None
    if validated.get("lot_size") and validated.get("aql_level"):
        aql_criteria = AQLCalculator.calculate_aql_criteria(
            validated["lot_size"], 
            validated["aql_level"]
        )
        validated.update(aql_criteria)
    
    template = Template(
        title=validated["title"].strip(),
        description=validated.get("description", "").strip(),
        image_url=validated.get("image_url"),
        pages=validated["pages"],
        manager_id=mgr_doc["_id"],
        organization=validated["organization"].strip(),
        location=validated["location"].strip(),
        creator_id=ObjectId(user["user_id"]),
        status="submitted",
        manager_firstName=mgr_doc.get("firstName"),
        manager_lastName=mgr_doc.get("lastName"),
        aql_level=validated.get("aql_level", 2.5),
        lot_size=validated.get("lot_size"),
        sample_size=aql_criteria["sample_size"] if aql_criteria else None,
        major_defects_allowed=aql_criteria["major_defects_allowed"] if aql_criteria else None,
        minor_defects_allowed=aql_criteria["minor_defects_allowed"] if aql_criteria else None,
        critical_defects_allowed=aql_criteria["critical_defects_allowed"] if aql_criteria else None,
        letter_of_code=validated.get("letter_of_code"),
        defect_categories=validated.get("defect_categories", {
            "critical": [],
            "major": [],
            "minor": []
        })
    )
    try:
        template_dict = template.to_dict()
        result = collection.insert_one(template_dict)
        template._id = result.inserted_id
        print(f"Template created successfully with ID: {result.inserted_id}")
        return jsonify({
            "success": True, 
            "message": "Template created successfully",
            "data": template.public_view()
        })
    except Exception as e:
        print(f"Database error creating template: {e}")
        return jsonify({"success": False, "message": "Failed to create template"}), 500


@template_bp.route("/draft", methods=["POST"])
@require_auth
def create_draft_template():
    """Create a draft template without requiring manager assignment.

    Allowed roles: IT (optionally allow manager to draft their own). Minimal payload:
    {
      "title": str,
      "description": str|optional,
      "image_url": str|optional,
      "pages": [ ... ]
    }
    """
    user = request.current_user
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    payload = request.get_json() or {}
    title = (payload.get("title") or "").strip()
    pages = payload.get("pages")
    if not title:
        return jsonify({"success": False, "message": "Template title is required"}), 400
    if not isinstance(pages, list) or len(pages) == 0:
        return jsonify({"success": False, "message": "Template must have at least one page"}), 400

    db = get_db()
    collection = db.get_collection("templates")

    # If a manager is drafting, associate the draft to that manager for permissions
    manager_id = None
    manager_first = None
    manager_last = None
    if user["role"] == "manager":
        try:
            manager_id = ObjectId(user["user_id"])  # type: ignore
        except Exception:
            manager_id = None
        # Best-effort names from auth payload (keys may vary)
        manager_first = user.get("firstName") or user.get("first_name")
        manager_last = user.get("lastName") or user.get("last_name")

    tpl = Template(
        title=title,
        description=(payload.get("description") or "").strip(),
        image_url=payload.get("image_url"),
        pages=pages,
        creator_id=ObjectId(user["user_id"]),
        status="draft",
        # Optionally accept organization/location if provided, but not required
        organization=(payload.get("organization") or None),
        location=(payload.get("location") or None),
        manager_id=manager_id,
        manager_firstName=manager_first,
        manager_lastName=manager_last,
    )

    try:
        result = collection.insert_one(tpl.to_dict())
        tpl._id = result.inserted_id
        return jsonify({"success": True, "data": tpl.public_view()})
    except Exception as e:
        logger.error(f"Failed to create draft template: {e}")
        return jsonify({"success": False, "message": "Failed to create draft template"}), 500

# -----------------------------------------------------------------------------
# Delete template (IT or assigned Manager)
# -----------------------------------------------------------------------------

@template_bp.route("/<template_id>", methods=["DELETE"])
@require_auth
def delete_template(template_id):
    user = request.current_user
    try:
        tpl_id = ObjectId(template_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid template id"}), 400

    db = get_db()
    collection = db.get_collection("templates")
    template_doc = collection.find_one({"_id": tpl_id})
    if not template_doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    template = Template.from_dict(template_doc)

    # Only IT or the assigned manager can delete
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403
    if user["role"] == "manager" and str(template.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    collection.delete_one({"_id": tpl_id})
    return jsonify({"success": True, "message": "Template deleted"})

# -----------------------------------------------------------------------------
# AQL Calculation endpoints
# -----------------------------------------------------------------------------

@template_bp.route("/calculate-aql", methods=["POST"])
@require_auth
def calculate_aql():
    """Calculate AQL criteria based on lot size and AQL level"""
    user = request.current_user
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    payload = request.get_json() or {}
    lot_size = payload.get("lot_size")
    aql_level = payload.get("aql_level", 2.5)

    if not lot_size or not isinstance(lot_size, int) or lot_size < 1:
        return jsonify({"success": False, "message": "Valid lot_size is required"}), 400

    try:
        aql_criteria = AQLCalculator.calculate_aql_criteria(lot_size, aql_level)
        return jsonify({
            "success": True,
            "data": aql_criteria
        })
    except Exception as e:
        logger.error(f"Error calculating AQL: {e}")
        return jsonify({"success": False, "message": "Error calculating AQL criteria"}), 500


@template_bp.route("/aql-reference", methods=["GET"])
@require_auth
def get_aql_reference_tables():
    """Return the first two sheets of the AQL Excel as tables for the UI Reference Tables modal.

    Source path priority:
      1. Query param ?path= (absolute path)
      2. Env var AQL_EXCEL_PATH
    """
    user = request.current_user
    # Allow IT and manager to view; inspectors don't need this in the field
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    excel_path = request.args.get("path") or os.environ.get("AQL_EXCEL_PATH")
    if not excel_path:
        return jsonify({"success": False, "message": "AQL_EXCEL_PATH not configured"}), 400

    try:
        # Lazy import so that app can start even if pandas is missing until installed
        import pandas as pd  # type: ignore
        xls = pd.ExcelFile(excel_path)
        sheet_names = xls.sheet_names[:2]
        out_sheets = []
        for name in sheet_names:
            df = pd.read_excel(excel_path, sheet_name=name, engine="openpyxl")
            df = df.fillna("")
            headers = [str(c) for c in df.columns]
            rows = [[str(v) if v is not None else "" for v in row] for row in df.values.tolist()]
            out_sheets.append({
                "name": name,
                "headers": headers,
                "rows": rows,
            })
        return jsonify({"success": True, "data": {"sheets": out_sheets}})
    except FileNotFoundError:
        return jsonify({"success": False, "message": f"Excel not found: {excel_path}"}), 404
    except Exception as e:
        logger.error(f"Failed to read AQL Excel: {e}")
        return jsonify({"success": False, "message": "Failed to read AQL reference tables"}), 500


@template_bp.route("/aql-reference-files", methods=["GET"])
@require_auth
def get_aql_reference_from_files():
    """Return AQL reference tables from JSON files under aql_output/ (Sheet2 and Sheet4).

    Response format matches the Excel endpoint: {"sheets": [{name, headers, rows}, ...]}
    Order: page-1 => Sheet2, page-2 => Sheet4.
    """
    user = request.current_user
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    try:
        project_root = Path(__file__).resolve().parents[3]
        output_dir = project_root / "aql_output"
        s2_path = output_dir / "Sheet2.json"
        s4_path = output_dir / "Sheet4.json"

        if not s2_path.exists() or not s4_path.exists():
            return jsonify({"success": False, "message": "AQL JSON files not found in aql_output"}), 404

        def to_table(json_path: Path):
            with json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list) or not data:
                return {"name": json_path.stem, "headers": [], "rows": []}
            # Use the first object's keys as headers, preserving order
            first = data[0]
            headers = list(first.keys())
            rows = [[str((row.get(h, ""))) for h in headers] for row in data]
            return {"name": json_path.stem, "headers": headers, "rows": rows}

        sheet2 = to_table(s2_path)
        sheet4 = to_table(s4_path)

        return jsonify({"success": True, "data": {"sheets": [sheet2, sheet4]}})
    except Exception as e:
        logger.error(f"Failed to read AQL JSON files: {e}")
        return jsonify({"success": False, "message": "Failed to read AQL reference tables from files"}), 500


# -----------------------------------------------------------------------------
# Defects library from aql_output/garments_defects.json (for auto-populating sections)
# -----------------------------------------------------------------------------

@template_bp.route("/defects-library", methods=["GET"])
@require_auth
def get_defects_library_from_file():
    """Return a mapping of defect categories -> list of defect descriptions

    The source file `aql_output/garments_defects.json` is expected to be an
    array of rows with keys: "Defect Category" and "Defect Description (English)".
    Rows where the category is null inherit the most recent non-null category.
    """
    user = request.current_user
    # Allow IT and manager to use this in the template builder
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    try:
        project_root = Path(__file__).resolve().parents[3]
        output_dir = project_root / "aql_output"
        defects_path = output_dir / "garments_defects.json"

        if not defects_path.exists():
            return jsonify({"success": False, "message": "garments_defects.json not found in aql_output"}), 404

        with defects_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        categories = {}
        current_cat = None
        for row in (data or []):
            cat = row.get("Defect Category")
            desc = row.get("Defect Description (English)")
            if cat is not None and str(cat).strip() != "":
                current_cat = str(cat).strip()
                categories.setdefault(current_cat, [])
            if desc is None:
                continue
            if current_cat is None:
                # Skip descriptions until a first category appears
                continue
            categories.setdefault(current_cat, []).append(str(desc).strip())

        return jsonify({"success": True, "data": {"categories": categories}})
    except Exception as e:
        logger.error(f"Failed to read defects library JSON: {e}")
        return jsonify({"success": False, "message": "Failed to read defects library"}), 500


@template_bp.route("/<template_id>/aql-config", methods=["PUT"])
@require_auth
def update_aql_config(template_id):
    """Update AQL configuration for a template"""
    user = request.current_user
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403

    try:
        tpl_id = ObjectId(template_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid template id"}), 400

    payload = request.get_json() or {}
    db = get_db()
    collection = db.get_collection("templates")

    # Check if template exists and user has access
    template_doc = collection.find_one({"_id": tpl_id})
    if not template_doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    template = Template.from_dict(template_doc)
    
    # Check access permissions
    if user["role"] == "manager" and str(template.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    # Update AQL fields
    update_fields = {}
    
    if "aql_level" in payload:
        update_fields["aql_level"] = payload["aql_level"]
    if "aql_level_critical" in payload:
        update_fields["aql_level_critical"] = payload["aql_level_critical"]
    if "aql_level_major" in payload:
        update_fields["aql_level_major"] = payload["aql_level_major"]
    if "aql_level_minor" in payload:
        update_fields["aql_level_minor"] = payload["aql_level_minor"]
    
    if "lot_size" in payload:
        update_fields["lot_size"] = payload["lot_size"]
    
    # Newly added: persist the chosen letter(s) of code
    if "letter_of_code" in payload:
        update_fields["letter_of_code"] = payload["letter_of_code"]
    if "letter_of_code_critical" in payload:
        update_fields["letter_of_code_critical"] = payload["letter_of_code_critical"]
    if "letter_of_code_major" in payload:
        update_fields["letter_of_code_major"] = payload["letter_of_code_major"]
    if "letter_of_code_minor" in payload:
        update_fields["letter_of_code_minor"] = payload["letter_of_code_minor"]

    if "defect_categories" in payload:
        update_fields["defect_categories"] = payload["defect_categories"]

    # Persist optional AQL reference tables if provided
    if isinstance(payload.get("aql_tables"), dict):
        update_fields["aql_tables"] = payload.get("aql_tables")

    # Recalculate AQL criteria if lot_size, aql_level, or letter_of_code changed
    # If a letter_of_code is provided, we keep existing logic here as-is (simple calculator)
    # because the frontend uses Sheet2/Sheet4 to compute precise values and sends them explicitly.
    if "lot_size" in payload or "aql_level" in payload:
        new_lot_size = payload.get("lot_size", template.lot_size)
        new_aql_level = payload.get("aql_level", template.aql_level)
        
        if new_lot_size:
            aql_criteria = AQLCalculator.calculate_aql_criteria(new_lot_size, new_aql_level)
            update_fields.update({
                "sample_size": aql_criteria["sample_size"],
                "major_defects_allowed": aql_criteria["major_defects_allowed"],
                "minor_defects_allowed": aql_criteria["minor_defects_allowed"],
                "critical_defects_allowed": aql_criteria["critical_defects_allowed"]
            })

    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        collection.update_one({"_id": tpl_id}, {"$set": update_fields})
        
        # Return updated template
        updated_doc = collection.find_one({"_id": tpl_id})
        updated_template = Template.from_dict(updated_doc)
        
        return jsonify({
            "success": True,
            "message": "AQL configuration updated",
            "data": updated_template.public_view()
        })
    
    return jsonify({"success": False, "message": "No valid fields to update"}), 400


# -----------------------------------------------------------------------------
# Get single template
# -----------------------------------------------------------------------------

@template_bp.route("/inspection/<template_id>", methods=["GET"])
@require_auth
def get_template_for_inspection(template_id):
    """Get template for inspection/testing purposes (for inspectors and IT)."""
    user = request.current_user
    
    # Only inspectors and IT can access this endpoint
    if user["role"] not in ["inspector", "it"]:
        return jsonify({"success": False, "message": "Access denied"}), 403
    
    try:
        tpl_id = ObjectId(template_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid template ID"}), 400
    
    db = get_db()
    collection = db.get_collection("templates")
    
    # Find the template - only published templates for inspectors, any for IT
    query = {"_id": tpl_id}
    if user["role"] == "inspector":
        query["status"] = "published"
    
    doc = collection.find_one(query)
    if not doc:
        return jsonify({"success": False, "message": "Template not found"}), 404
    
    template = Template.from_dict(doc)
    return jsonify({"success": True, "data": template.public_view()})


@template_bp.route("/<template_id>", methods=["GET"])
@require_auth
def get_template(template_id):
    """Get a single template by ID"""
    user = request.current_user
    
    try:
        tpl_id = ObjectId(template_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid template id"}), 400

    db = get_db()
    collection = db.get_collection("templates")
    
    template_doc = collection.find_one({"_id": tpl_id})
    if not template_doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    template = Template.from_dict(template_doc)
    
    # Check access permissions
    if user["role"] == "manager" and str(template.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403
    elif user["role"] == "inspector" and template.status != "published":
        return jsonify({"success": False, "message": "Template not available"}), 403

    return jsonify({
        "success": True,
        "data": template.public_view()
    })


# -----------------------------------------------------------------------------
# Update template content (pages/title/description/image) – manager or IT
# -----------------------------------------------------------------------------

@template_bp.route("/<template_id>", methods=["PUT"])
@require_auth
def update_template(template_id):
    user = request.current_user
    try:
        tpl_id = ObjectId(template_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid template id"}), 400

    db = get_db()
    collection = db.get_collection("templates")
    template_doc = collection.find_one({"_id": tpl_id})
    if not template_doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    template = Template.from_dict(template_doc)

    # Only IT or the assigned manager can update
    if user["role"] not in ["it", "manager"]:
        return jsonify({"success": False, "message": "Access denied"}), 403
    if user["role"] == "manager" and str(template.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    payload = request.get_json() or {}

    update_fields = {}
    if isinstance(payload.get("pages"), list):
        update_fields["pages"] = payload["pages"]
    if isinstance(payload.get("title"), str):
        update_fields["title"] = payload["title"].strip()
        update_fields["name"] = payload["title"].strip()  # legacy index
    if isinstance(payload.get("description"), str):
        update_fields["description"] = payload["description"].strip()
    if payload.get("image_url") is not None:
        update_fields["image_url"] = payload.get("image_url")

    if not update_fields:
        return jsonify({"success": False, "message": "No valid fields to update"}), 400

    update_fields["updated_at"] = datetime.utcnow()
    collection.update_one({"_id": tpl_id}, {"$set": update_fields})

    updated_doc = collection.find_one({"_id": tpl_id})
    return jsonify({"success": True, "data": Template.from_dict(updated_doc).public_view()})


# -----------------------------------------------------------------------------
# Manager – publish a template
# -----------------------------------------------------------------------------

@template_bp.route("/<template_id>/publish", methods=["POST"])
@require_auth
def publish_template(template_id):
    user = request.current_user
    if user["role"] != "manager":
        return jsonify({"success": False, "message": "Only managers can publish templates"}), 403

    try:
        tpl_id = ObjectId(template_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid template id"}), 400

    db = get_db()
    collection = db.get_collection("templates")
    doc = collection.find_one({"_id": tpl_id})
    if not doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    tpl = Template.from_dict(doc)
    if str(tpl.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    # If lot_size present but sample_size missing, calculate AQL criteria
    update_fields = {"status": "published", "updated_at": datetime.utcnow()}
    if tpl.lot_size and not tpl.sample_size:
        try:
            crit = AQLCalculator.calculate_aql_criteria(tpl.lot_size, tpl.aql_level or 2.5)
            update_fields.update({
                "sample_size": crit["sample_size"],
                "major_defects_allowed": crit["major_defects_allowed"],
                "minor_defects_allowed": crit["minor_defects_allowed"],
                "critical_defects_allowed": crit["critical_defects_allowed"],
            })
        except Exception:
            # ignore calc errors; publish anyway
            pass

    collection.update_one({"_id": tpl_id}, {"$set": update_fields})
    updated = collection.find_one({"_id": tpl_id})
    return jsonify({"success": True, "data": Template.from_dict(updated).public_view()})