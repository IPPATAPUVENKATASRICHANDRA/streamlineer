from flask import Blueprint, request, jsonify
from bson import ObjectId, regex
from ..utils.auth import require_auth
from ..utils.database import get_db

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

@users_bp.route("/managers", methods=["GET"])
@require_auth
def list_managers():
    """Return list of manager users. Accepts ?q= search string."""
    current_user = request.current_user
    if current_user.get("role") != "it":
        return jsonify({"success": False, "message": "Only IT role can list managers"}), 403

    q = request.args.get("q", "").strip()
    db = get_db()
    coll = db.get_collection("users")

    query = {"role": "manager"}
    if q:
        regex_q = {"$regex": q, "$options": "i"}
        # match on firstName, lastName, or email
        query["$or"] = [
            {"firstName": regex_q},
            {"lastName": regex_q},
            {"email": regex_q},
        ]

    cursor = coll.find(query).limit(20)
    managers = []
    for doc in cursor:
        managers.append({
            "id": str(doc["_id"]),
            "firstName": doc.get("firstName"),
            "lastName": doc.get("lastName"),
            "fullName": f"{doc.get('firstName','')} {doc.get('lastName','')}",
            "email": doc.get("email"),
            "organization": doc.get("organization"),
            "location": doc.get("location"),
        })

    return jsonify({"success": True, "data": managers})

# -----------------------------------------------------------------------------
# Inspectors list
# -----------------------------------------------------------------------------
@users_bp.route("/inspectors", methods=["GET"])
@require_auth
def list_inspectors():
    """Return list of inspector users (for manager assignment). Accepts ?q= search string."""
    current_user = request.current_user
    if current_user.get("role") != "manager":
        return jsonify({"success": False, "message": "Only manager role can list inspectors"}), 403

    q = request.args.get("q", "").strip()
    db = get_db()
    coll = db.get_collection("users")

    query = {"role": "inspector"}
    if q:
        regex_q = {"$regex": q, "$options": "i"}
        query["$or"] = [
            {"firstName": regex_q},
            {"lastName": regex_q},
            {"email": regex_q},
        ]

    cursor = coll.find(query).limit(20)
    inspectors = []
    for doc in cursor:
        inspectors.append({
            "id": str(doc["_id"]),
            "firstName": doc.get("firstName"),
            "lastName": doc.get("lastName"),
            "fullName": f"{doc.get('firstName','')} {doc.get('lastName','')}",
            "email": doc.get("email"),
            "organization": doc.get("organization"),
            "location": doc.get("location"),
        })
    return jsonify({"success": True, "data": inspectors})