"""Inspection scheduling and response submission endpoints"""

from datetime import datetime
from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask import send_file
from gridfs import GridFS
from io import BytesIO
from pymongo.errors import DuplicateKeyError
import logging

from ..utils.auth import require_auth
from ..utils.database import get_db
from ..models.inspection import Inspection
from ..models.task import Task
from ..models.template import Template  # for projection to inspector list
from ..models.inspection_response import InspectionResponse
from ..utils.aql import AQLResultProcessor
from ..utils.audit import log_inspection_audit

logger = logging.getLogger(__name__)

inspection_bp = Blueprint("inspection", __name__, url_prefix="/api/inspections")
# Public file fetch for embedding images in PDF (signatures, etc.)
@inspection_bp.route("/file/<file_id>", methods=["GET"])
def get_uploaded_file(file_id):
    try:
        from bson import ObjectId as _ObjectId
        dbi = get_db()
        fs = GridFS(dbi.db)
        file_obj = fs.get(_ObjectId(file_id))
        data = file_obj.read()
        content_type = getattr(file_obj, "contentType", "application/octet-stream")
        return send_file(BytesIO(data), mimetype=content_type, as_attachment=False, download_name=getattr(file_obj, "filename", "file"))
    except Exception as e:
        logger.error(f"Failed to fetch file {file_id}: {e}")
        return jsonify({"success": False, "message": "File not found"}), 404


# -----------------------------------------------------------------------------
# Manager – schedule/assign an inspection
# -----------------------------------------------------------------------------

@inspection_bp.route("/assign", methods=["POST"])
@require_auth
def assign_inspection():
    """Manager schedules a published template for an inspector.

    Expected JSON payload: {
        "template_id": str (optional if template_title provided),
        "template_title": str (optional),
        "inspector_email": str,
        "date": "YYYY-MM-DD",  # optional – scheduled date
        "time": "HH:MM"         # optional – scheduled time
    }
    """
    user = request.current_user
    if user["role"] != "manager":
        return jsonify({"success": False, "message": "Only managers can schedule inspections"}), 403

    payload = request.get_json() or {}
    if not payload.get("template_id") and not payload.get("template_title"):
        return jsonify({"success": False, "message": "template_id or template_title required"}), 400

    db = get_db()
    templates_coll = db.get_collection("templates")
    users_coll = db.get_collection("users")
    inspections_coll = db.get_collection("inspections")

    # ------------------------------------------------------------------
    # Resolve template
    # ------------------------------------------------------------------
    template_doc = None
    if payload.get("template_id"):
        try:
            template_id = ObjectId(payload["template_id"])
            template_doc = templates_coll.find_one({"_id": template_id})
        except Exception:
            return jsonify({"success": False, "message": "Invalid template_id"}), 400
    else:
        # Search by title
        template_doc = templates_coll.find_one({"title": payload["template_title"]})

    if not template_doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    template = Template.from_dict(template_doc)
    if str(template.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    if template.status != "published":
        return jsonify({"success": False, "message": "Template must be published"}), 400

    # ------------------------------------------------------------------
    # Resolve inspector
    # ------------------------------------------------------------------
    inspector_doc = users_coll.find_one({"email": payload["inspector_email"]})
    if not inspector_doc:
        return jsonify({"success": False, "message": f"Inspector with email '{payload['inspector_email']}' not found"}), 400
    if inspector_doc.get("role") != "inspector":
        return jsonify({"success": False, "message": f"User '{payload['inspector_email']}' is not an inspector"}), 400

    # ------------------------------------------------------------------
    # Parse scheduled date/time
    # ------------------------------------------------------------------
    scheduled_date = None
    if payload.get("date"):
        try:
            date_str = payload["date"]
            if payload.get("time"):
                date_str += f" {payload['time']}:00"
            else:
                date_str += " 00:00:00"
            scheduled_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return jsonify({"success": False, "message": "Invalid date/time format"}), 400

    # ------------------------------------------------------------------
    # Create inspection
    # ------------------------------------------------------------------
    inspection = Inspection(
        template_id=template._id,
        inspector_id=inspector_doc["_id"],
        manager_id=ObjectId(user["user_id"]),
        scheduled_date=scheduled_date,
    )

    try:
        inspection_dict = inspection.to_dict()
        result = inspections_coll.insert_one(inspection_dict)
        inspection._id = result.inserted_id

        # Create linked task
        tasks_coll = db.get_collection("tasks")
        task = Task(
            title=f"Inspection: {template.title}",
            description=f"Inspection assigned by {user.get('firstName', 'Manager')}",
            assigned_to_id=inspector_doc["_id"],
            assigned_by_id=ObjectId(user["user_id"]),
            assigned_to_name=f"{inspector_doc.get('firstName', '')} {inspector_doc.get('lastName', '')}",
            assigned_by_name=f"{user.get('firstName', '')} {user.get('lastName', '')}",
            priority="medium",
            inspection_id=inspection._id,
            template_title=template.title,
        )
        tasks_coll.insert_one(task.to_dict())

        return jsonify({
            "success": True,
            "message": "Inspection assigned successfully",
            "data": inspection.public_view()
        })

    except DuplicateKeyError:
        return jsonify({"success": False, "message": "Inspection already exists"}), 409
    except Exception as e:
        logger.error(f"Error assigning inspection: {e}")
        return jsonify({"success": False, "message": "Failed to assign inspection"}), 500


# -----------------------------------------------------------------------------
# Inspector – list assigned inspections
# -----------------------------------------------------------------------------

@inspection_bp.route("/assigned", methods=["GET"])
@require_auth
def list_assigned():
    """List inspections assigned to the current inspector."""
    user = request.current_user
    if user["role"] != "inspector":
        return jsonify({"success": False, "message": "Only inspectors can view assigned inspections"}), 403

    db = get_db()
    inspections_coll = db.get_collection("inspections")
    templates_coll = db.get_collection("templates")

    cursor = inspections_coll.find({"inspector_id": ObjectId(user["user_id"])}).sort("created_at", -1)
    results = []
    for doc in cursor:
        inspection = Inspection.from_dict(doc)
        template_doc = templates_coll.find_one({"_id": inspection.template_id})
        template = Template.from_dict(template_doc) if template_doc else None
        
        result = inspection.public_view()
        result["template_title"] = template.title if template else "Unknown Template"
        result["template_description"] = template.description if template else ""
        results.append(result)

    return jsonify({"success": True, "data": results})


# -----------------------------------------------------------------------------
# Inspector & Manager – get single inspection (includes template details)
# -----------------------------------------------------------------------------

@inspection_bp.route("/<inspection_id>", methods=["GET"])
@require_auth
def get_inspection(inspection_id):
    user = request.current_user
    db = get_db()
    inspections_coll = db.get_collection("inspections")
    templates_coll = db.get_collection("templates")

    try:
        insp_id = ObjectId(inspection_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid inspection id"}), 400

    insp_doc = inspections_coll.find_one({"_id": insp_id})
    if not insp_doc:
        return jsonify({"success": False, "message": "Inspection not found"}), 404

    insp = Inspection.from_dict(insp_doc)

    # Access control – inspector or manager who created
    if user["role"] == "inspector" and str(insp.inspector_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403
    if user["role"] == "manager" and str(insp.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    tpl_doc = templates_coll.find_one({"_id": insp.template_id})

    # Get inspection view
    inspection_view = insp.public_view()

    return jsonify({
        "success": True,
        "data": {
            "inspection": inspection_view,
            "template": Template.from_dict(tpl_doc).public_view() if tpl_doc else None,
        }
    })


# -----------------------------------------------------------------------------
# Inspector – submit responses
# -----------------------------------------------------------------------------

@inspection_bp.route("/<inspection_id>/submit", methods=["POST"])
@require_auth
def submit_inspection(inspection_id):
    user = request.current_user
    # Allow saving/submitting from any role; finalization remains gated by manager approval

    db = get_db()
    inspections_coll = db.get_collection("inspections")
    templates_coll = db.get_collection("templates")
    notifications_coll = db.get_collection("notifications")

    try:
        insp_id = ObjectId(inspection_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid inspection id"}), 400

    insp_doc = inspections_coll.find_one({"_id": insp_id})
    if not insp_doc:
        return jsonify({"success": False, "message": "Inspection not found"}), 404
    # If not owner, still allow saving progress (role-based workflows enforced elsewhere)
    # So we skip strict access check here to enable broader save capability

    payload = request.get_json() or {}
    responses = payload.get("responses")
    override = payload.get("override")  # { decision: 'ACCEPT'|'REJECT', reason: string }
    if not isinstance(responses, dict):
        return jsonify({"success": False, "message": "responses must be a JSON object"}), 400

    # Get template for AQL processing
    template_doc = templates_coll.find_one({"_id": insp_doc["template_id"]})
    if not template_doc:
        return jsonify({"success": False, "message": "Template not found"}), 404

    template = Template.from_dict(template_doc)
    
    # Process AQL results if template has AQL configuration
    aql_results = {}
    defect_counts = {"critical": 0, "major": 0, "minor": 0}
    aql_passed = True
    aql_rejection_reasons = []
    
    if template.lot_size and template.aql_level:
        aql_config = {
            "aql_level": template.aql_level,
            "lot_size": template.lot_size,
            "sample_size": template.sample_size,
            "major_defects_allowed": template.major_defects_allowed,
            "minor_defects_allowed": template.minor_defects_allowed,
            "critical_defects_allowed": template.critical_defects_allowed
        }
        # Ensure counts present: also aggregate from per-question numeric fields if globals missing
        try:
            def _sum_suffix(suffix: str) -> int:
                total = 0
                for k, v in (responses or {}).items():
                    if isinstance(k, str) and k.endswith(suffix):
                        try:
                            total += int(str(v))
                        except Exception:
                            pass
                return total
            if not responses.get("critical_defects"):
                responses["critical_defects"] = _sum_suffix("__critical_text")
            if not responses.get("major_defects"):
                responses["major_defects"] = _sum_suffix("__major_text")
            if not responses.get("minor_defects"):
                responses["minor_defects"] = _sum_suffix("__minor_text")
        except Exception:
            pass

        aql_results = AQLResultProcessor.process_inspection_results(
            responses, 
            aql_config, 
            template.defect_categories
        )
        
        defect_counts = aql_results["defect_counts"]
        aql_passed = aql_results["passed"]
        aql_rejection_reasons = aql_results["rejection_reasons"]

    # Apply optional inspector override with mandatory reason
    overridden = False
    override_meta = None
    if isinstance(override, dict) and override.get("decision") in ("ACCEPT", "REJECT"):
        if not override.get("reason"):
            return jsonify({"success": False, "message": "Override reason is required"}), 400
        overridden = True
        aql_passed = True if override["decision"] == "ACCEPT" else False
        if not aql_passed and "aql_rejection_reasons" in locals():
            aql_rejection_reasons = list(aql_rejection_reasons or []) + ["OVERRIDDEN_BY_INSPECTOR"]
        override_meta = {
            "actor_user_id": str(user["user_id"]),
            "actor_role": user.get("role"),
            "decision": override.get("decision"),
            "reason": override.get("reason"),
            "at": datetime.utcnow(),
            "previous": {
                "aql_passed": bool(aql_results.get("passed")) if aql_results else None,
                "rejection_reasons": list(aql_rejection_reasons or []),
            },
        }

    # ------------------------------------------------------------------
    # Evaluate simple per-question rules saved in template.pages[].questions[].rules
    # Each rule item: { equals, require_text, require_media, notify, message }
    # If a rule matches, enforce evidence presence and queue a notification.
    # ------------------------------------------------------------------
    rule_notifications = []
    matched_actions = []
    missing_evidence_errors = []
    try:
        pages = (template.pages or [])
        for page in pages:
            for q in (page.get("questions") or []):
                qid = q.get("id")
                if not qid:
                    continue
                q_rules = q.get("rules") or []
                if not q_rules:
                    continue
                ans = (responses or {}).get(str(qid))
                for r in q_rules:
                    if str(ans) == str(r.get("equals")):
                        # Evidence checks
                        if r.get("require_text"):
                            txt_key = f"{qid}__evidence_text"
                            if not (responses or {}).get(txt_key):
                                missing_evidence_errors.append({"question_id": qid, "missing": "text"})
                        if r.get("require_media"):
                            media_key = f"{qid}__evidence_media"
                            if not (responses or {}).get(media_key):
                                missing_evidence_errors.append({"question_id": qid, "missing": "media"})

                        # Record matched action
                        matched_actions.append({
                            "question_id": qid,
                            "value": ans,
                            "require_text": bool(r.get("require_text")),
                            "require_media": bool(r.get("require_media")),
                            "notify": bool(r.get("notify")),
                            "message": r.get("message") or None,
                        })
                        # Queue notification to manager if requested or if media evidence is required
                        if r.get("notify") or r.get("require_media"):
                            notify_msg = (
                                r.get("message")
                                or (f"Media evidence required for question '{q.get('text') or qid}' (value '{ans}')" if r.get("require_media") else None)
                                or f"Rule matched for question {qid}: value '{ans}'"
                            )
                            rule_notifications.append({
                                "template_id": insp_doc.get("template_id"),
                                "inspection_id": insp_id,
                                "manager_id": insp_doc.get("manager_id"),
                                "inspector_id": insp_doc.get("inspector_id"),
                                "question_id": qid,
                                "question_text": q.get("text"),
                                "message": notify_msg,
                                "created_at": datetime.utcnow(),
                                "type": "RULE_TRIGGER",
                                "read": False,
                            })
    except Exception as _e:
        logger.error(f"Rule evaluation failed for inspection {inspection_id}: {_e}")

    if missing_evidence_errors:
        return jsonify({
            "success": False,
            "message": "Required evidence is missing for one or more answers",
            "errors": missing_evidence_errors
        }), 400

    # Persist notifications (best-effort) and store matched actions summary in inspection
    if rule_notifications:
        try:
            notifications_coll.insert_many(rule_notifications)
        except Exception as _e:
            logger.error(f"Failed to insert notifications for inspection {inspection_id}: {_e}")
    # Attach notified flag to matched actions where applicable
    if matched_actions and rule_notifications:
        notified_set = {(str(n.get("question_id")) if n.get("question_id") is not None else None) for n in rule_notifications}
        for ma in matched_actions:
            if str(ma.get("question_id")) in notified_set:
                ma["notified"] = True

    completed_at = datetime.utcnow()
    update = {
        "responses": responses,
        # When non-inspectors save, keep it in progress; inspectors send for review
        "status": "submitted" if user.get("role") == "inspector" else "in_progress",
        # completed_at intentionally omitted until manager approval
        "updated_at": completed_at,
        "aql_results": { **(aql_results or {}), "overridden": overridden, "override_meta": override_meta },
        "defect_counts": defect_counts,
        "aql_passed": aql_passed,
        "aql_rejection_reasons": aql_rejection_reasons,
        # Backward compatibility: keep rule_actions for any existing consumers
        "rule_actions": matched_actions,
        # New unified field name
        "remaining_actions": matched_actions
    }
    inspections_coll.update_one({"_id": insp_id}, {"$set": update})

    # Do not persist to inspection_responses yet; will be stored on manager approval

    insp_doc.update(update)
    insp = Inspection.from_dict(insp_doc)

    try:
        log_inspection_audit(
            inspection_id=insp_id,
            user_id=user["user_id"],
            action="SUBMIT",
            details={
                "defect_counts": defect_counts,
                "aql_passed": aql_passed,
                "rejection_reasons": aql_rejection_reasons,
                "overridden": overridden,
                "override": override_meta or override or {},
            },
        )
    except Exception as e:  # noqa: BLE001 – audit should not block
        logger.error(f"Failed to write inspection audit for {inspection_id}: {e}")

    # Update linked tasks: move inspector task to 'review' and create manager review task
    try:
        tasks_coll = db.get_collection("tasks")
        # 1) Inspector's task -> status 'review'
        tasks_coll.update_many(
            {"inspection_id": insp_id},
            {"$set": {"status": "review", "updated_at": completed_at}}
        )
        # 2) Create (or upsert) a manager review task so it appears on manager's board
        # Avoid duplicates by checking existing task for manager on this inspection
        existing_mgr_task = tasks_coll.find_one({
            "inspection_id": insp_id,
            "assigned_to_id": insp_doc.get("manager_id"),
            "status": {"$in": ["review", "todo", "in_progress"]}
        })
        if not existing_mgr_task:
            # Get template title for display
            tpl = templates_coll.find_one({"_id": insp_doc.get("template_id")}) or {}
            # Resolve names for display
            users_coll = db.get_collection("users")
            mgr_doc = users_coll.find_one({"_id": insp_doc.get("manager_id")}) or {}
            insp_user = users_coll.find_one({"_id": insp_doc.get("inspector_id")}) or {}
            manager_name = f"{mgr_doc.get('firstName','')} {mgr_doc.get('lastName','')}".strip()
            inspector_name = f"{insp_user.get('firstName','')} {insp_user.get('lastName','')}".strip()
            manager_task = Task(
                title=f"Review: {tpl.get('title', 'Inspection')}",
                description="From inspector",
                priority="medium",
                status="review",
                inspection_id=insp_id,
                template_title=tpl.get("title"),
                assigned_to_id=insp_doc.get("manager_id"),
                assigned_by_id=insp_doc.get("inspector_id"),
                assigned_to_name=manager_name,
                assigned_by_name=inspector_name,
            )
            try:
                tasks_coll.insert_one(manager_task.to_dict())
            except Exception:
                pass
    except Exception as e:  # noqa: BLE001 – non-critical
        logger.error(f"Failed to update/create tasks for inspection {inspection_id}: {e}")

    # CAR creation and task completion will happen after manager approval

    return jsonify({
        "success": True, 
        "message": "Inspection submitted for manager review", 
        "data": insp.public_view()
    })


# -----------------------------------------------------------------------------
# Manager – list inspections pending review
# -----------------------------------------------------------------------------

@inspection_bp.route("/pending", methods=["GET"])
@require_auth
def list_pending_reviews():
    user = request.current_user
    if user["role"] != "manager":
        return jsonify({"success": False, "message": "Only managers can view pending reviews"}), 403

    db = get_db()
    inspections_coll = db.get_collection("inspections")
    templates_coll = db.get_collection("templates")

    cursor = inspections_coll.find({
        "manager_id": ObjectId(user["user_id"]),
        "status": "submitted"
    }).sort("updated_at", -1)

    results = []
    for doc in cursor:
        inspection = Inspection.from_dict(doc)
        template_doc = templates_coll.find_one({"_id": inspection.template_id})
        template = Template.from_dict(template_doc) if template_doc else None
        result = inspection.public_view()
        result["template_title"] = template.title if template else "Unknown Template"
        result["template_description"] = template.description if template else ""
        results.append(result)

    return jsonify({"success": True, "data": results})


# -----------------------------------------------------------------------------
# Manager – approve inspection (finalize and store response)
# -----------------------------------------------------------------------------

@inspection_bp.route("/<inspection_id>/approve", methods=["POST"])
@require_auth
def approve_inspection(inspection_id):
    user = request.current_user
    if user["role"] != "manager":
        return jsonify({"success": False, "message": "Only managers can approve"}), 403

    db = get_db()
    inspections_coll = db.get_collection("inspections")

    try:
        insp_id = ObjectId(inspection_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid inspection id"}), 400

    insp_doc = inspections_coll.find_one({"_id": insp_id})
    if not insp_doc:
        return jsonify({"success": False, "message": "Inspection not found"}), 404
    if str(insp_doc.get("manager_id")) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403
    if insp_doc.get("status") != "submitted":
        return jsonify({"success": False, "message": "Inspection is not pending review"}), 400

    # Finalize inspection
    now = datetime.utcnow()
    inspections_coll.update_one({"_id": insp_id}, {"$set": {
        "status": "completed",
        "completed_at": now,
        "updated_at": now,
    }})

    # Store inspection response now
    try:
        inspection_responses_coll = db.get_collection("inspection_responses")
        inspection_response = InspectionResponse(
            template_id=insp_doc.get("template_id"),
            task_id=None,
            inspector_id=insp_doc.get("inspector_id"),
            manager_id=insp_doc.get("manager_id"),
            answers=insp_doc.get("responses") or {},
            created_at=now
        )

        existing_response = inspection_responses_coll.find_one({
            "template_id": insp_doc.get("template_id"),
            "inspector_id": insp_doc.get("inspector_id")
        })

        if existing_response:
            inspection_responses_coll.update_one(
                {"_id": existing_response["_id"]},
                {"$set": inspection_response.to_dict(include_id=False)}
            )
        else:
            inspection_responses_coll.insert_one(inspection_response.to_dict())
    except Exception as e:
        logger.error(f"Failed to persist inspection response on approval for {inspection_id}: {e}")

    # Create CAR if AQL failed
    try:
        if not bool(insp_doc.get("aql_passed", True)):
            cars = db.get_collection("corrective_actions")
            responses = insp_doc.get("responses") or {}
            defect_counts = insp_doc.get("defect_counts") or {}
            aql_rejection_reasons = insp_doc.get("aql_rejection_reasons") or []
            top_codes = {}
            try:
                for sample in (responses or {}).get("samples", []):
                    for d in sample.get("defects", []) or []:
                        code = d.get("code") or d.get("defect_code")
                        if not code:
                            continue
                        top_codes[code] = top_codes.get(code, 0) + int(d.get("count") or 1)
            except Exception:
                top_codes = {}
            cars.insert_one({
                "inspection_id": insp_id,
                "template_id": insp_doc.get("template_id"),
                "manager_id": insp_doc.get("manager_id"),
                "inspector_id": insp_doc.get("inspector_id"),
                "defect_counts": defect_counts,
                "rejection_reasons": aql_rejection_reasons,
                "top_defect_codes": sorted([{ "code": k, "count": v } for k, v in top_codes.items()], key=lambda x: -x["count"])[:5],
                "created_at": now,
                "status": "open",
            })
    except Exception as e:
        logger.error(f"Failed to create CAR on approval for inspection {inspection_id}: {e}")

    # Mark linked tasks as completed
    try:
        tasks_coll = db.get_collection("tasks")
        # Inspector task -> completed
        tasks_coll.update_many(
            {"inspection_id": insp_id, "assigned_to_id": insp_doc.get("inspector_id")},
            {"$set": {"status": "completed", "is_completed": True, "completed_at": now, "updated_at": now}}
        )
        # Manager review task -> completed
        tasks_coll.update_many(
            {"inspection_id": insp_id, "assigned_to_id": insp_doc.get("manager_id")},
            {"$set": {"status": "completed", "is_completed": True, "completed_at": now, "updated_at": now}}
        )
    except Exception as e:  # noqa: BLE001 – non-critical
        logger.error(f"Failed to update linked task on approval for inspection {inspection_id}: {e}")

    # Audit
    try:
        log_inspection_audit(
            inspection_id=insp_id,
            user_id=user["user_id"],
            action="APPROVE",
            details={}
        )
    except Exception as e:
        logger.error(f"Failed to write approval audit for {inspection_id}: {e}")

    # Return finalized view
    insp_doc = inspections_coll.find_one({"_id": insp_id})
    insp = Inspection.from_dict(insp_doc)
    return jsonify({
        "success": True,
        "message": "Inspection approved",
        "data": insp.public_view()
    })


# -----------------------------------------------------------------------------
# Completed inspections list – role dependent
# -----------------------------------------------------------------------------

@inspection_bp.route("/completed", methods=["GET"])
@require_auth
def list_completed():
    user = request.current_user
    db = get_db()
    inspections_coll = db.get_collection("inspections")
    templates_coll = db.get_collection("templates")

    # Build query based on role
    if user["role"] == "inspector":
        query = {
            "inspector_id": ObjectId(user["user_id"]),
            "status": "completed"
        }
    elif user["role"] == "manager":
        query = {
            "manager_id": ObjectId(user["user_id"]),
            "status": "completed"
        }
    else:
        query = {"status": "completed"}

    cursor = inspections_coll.find(query).sort("completed_at", -1)
    results = []
    for doc in cursor:
        inspection = Inspection.from_dict(doc)
        template_doc = templates_coll.find_one({"_id": inspection.template_id})
        template = Template.from_dict(template_doc) if template_doc else None
        
        result = inspection.public_view()
        result["template_title"] = template.title if template else "Unknown Template"
        result["template_description"] = template.description if template else ""
        results.append(result)

    return jsonify({"success": True, "data": results})


# -----------------------------------------------------------------------------
# AQL Results endpoint
# -----------------------------------------------------------------------------

@inspection_bp.route("/<inspection_id>/aql-results", methods=["GET"])
@require_auth
def get_aql_results(inspection_id):
    """Get detailed AQL results for an inspection"""
    user = request.current_user
    db = get_db()
    inspections_coll = db.get_collection("inspections")
    templates_coll = db.get_collection("templates")

    try:
        insp_id = ObjectId(inspection_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid inspection id"}), 400

    insp_doc = inspections_coll.find_one({"_id": insp_id})
    if not insp_doc:
        return jsonify({"success": False, "message": "Inspection not found"}), 404

    inspection = Inspection.from_dict(insp_doc)

    # Access control
    if user["role"] == "inspector" and str(inspection.inspector_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403
    if user["role"] == "manager" and str(inspection.manager_id) != str(user["user_id"]):
        return jsonify({"success": False, "message": "Access denied"}), 403

    template_doc = templates_coll.find_one({"_id": inspection.template_id})
    template = Template.from_dict(template_doc) if template_doc else None

    if not template or not template.lot_size:
        return jsonify({"success": False, "message": "No AQL configuration found"}), 404

    return jsonify({
        "success": True,
        "data": {
            "inspection": inspection.public_view(),
            "template": template.public_view(),
            "aql_summary": {
                "passed": inspection.aql_passed,
                "defect_counts": inspection.defect_counts,
                "rejection_reasons": inspection.aql_rejection_reasons,
                "aql_level": template.aql_level,
                "lot_size": template.lot_size,
                "sample_size": template.sample_size,
                "criteria": {
                    "major_defects_allowed": template.major_defects_allowed,
                    "minor_defects_allowed": template.minor_defects_allowed,
                    "critical_defects_allowed": template.critical_defects_allowed
                }
            }
        }
    })


# -----------------------------------------------------------------------------
# Upload media for answers/evidence (GridFS-backed)
# -----------------------------------------------------------------------------

@inspection_bp.route("/<inspection_id>/upload", methods=["POST"])
@require_auth
def upload_media(inspection_id):
    """Upload media (image/video/audio/document) up to 20MB. Returns file_id and metadata.

    Form-Data fields:
    - file: binary
    - context: json string (e.g., {"sample_index":1, "type":"evidence"|"answer", "question_id":"...", "media_kind":"image|video|audio|document"})
    """
    user = request.current_user
    if user["role"] != "inspector":
        return jsonify({"success": False, "message": "Only inspectors can upload"}), 403

    from gridfs import GridFS
    from ..utils.database import get_db

    dbi = get_db()
    fs = GridFS(dbi.db)

    try:
        insp_id = ObjectId(inspection_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid inspection id"}), 400

    file = request.files.get("file")
    if not file:
        return jsonify({"success": False, "message": "file is required"}), 400

    # Validate type and size
    content_type = (file.mimetype or "").lower()
    allowed_types = (
        # images
        "image/jpeg", "image/png", "image/jpg", "image/webp", "image/gif",
        # video
        "video/mp4", "video/quicktime", "video/webm",
        # audio
        "audio/mpeg", "audio/mp4", "audio/wav", "audio/webm",
        # documents
        "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    if content_type not in allowed_types:
        return jsonify({"success": False, "message": "Unsupported file type"}), 400
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > 20 * 1024 * 1024:
        return jsonify({"success": False, "message": "Max file size 20MB"}), 400

    # Optional context metadata
    context = request.form.get("context")
    try:
        import json as _json
        context_obj = _json.loads(context) if context else {}
    except Exception:
        context_obj = {}

    # Derive stored filename safely
    stored_filename = file.filename or "upload.bin"
    kind = (context_obj.get("type") or "inspection_media").lower()
    file_id = fs.put(
        file.stream.read(),
        filename=stored_filename,
        contentType=content_type,
        inspection_id=str(insp_id),
        uploaded_by=str(user["user_id"]),
        context=context_obj,
        kind=kind,
    )

    try:
        log_inspection_audit(
            inspection_id=insp_id,
            user_id=user["user_id"],
            action="MEDIA_UPLOAD",
            details={"file_id": str(file_id), "context": context_obj},
        )
    except Exception as e:
        logger.error(f"Failed to audit photo upload for {inspection_id}: {e}")

    return jsonify({
        "success": True,
        "data": {"file_id": str(file_id)}
    })
