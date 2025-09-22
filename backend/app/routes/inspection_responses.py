from flask import Blueprint, request, jsonify
from bson import ObjectId

from ..utils.auth import require_auth
from ..utils.database import get_db
from ..models.inspection_response import InspectionResponse

responses_bp = Blueprint("responses", __name__, url_prefix="/api/responses")

# -----------------------------------------------------------------------------
# Inspector submits completed inspection
# -----------------------------------------------------------------------------
@responses_bp.route("/", methods=["POST"])
@require_auth
def submit_response():
    user = request.current_user
    if user.get("role") != "inspector":
        return jsonify({"success": False, "message": "Only inspectors can submit"}), 403

    payload = request.get_json() or {}
    required = ["template_id", "task_id", "answers", "manager_id"]
    if not all(k in payload for k in required):
        return jsonify({"success": False, "message": "Missing fields"}), 400

    resp = InspectionResponse(
        template_id=payload["template_id"],
        task_id=payload["task_id"],
        inspector_id=user["user_id"],
        manager_id=payload["manager_id"],
        answers=payload["answers"],
    )

    coll = get_db().get_collection("inspection_responses")
    coll.insert_one(resp.to_dict())
    return jsonify({"success": True, "message": "Response saved"})

# -----------------------------------------------------------------------------
# List responses for manager or inspector (own)
# -----------------------------------------------------------------------------
@responses_bp.route("/", methods=["GET"])
@require_auth
def list_responses():
    user = request.current_user
    role = user.get("role")
    if role not in ("manager", "inspector"):
        return jsonify({"success": False, "message": "Forbidden"}), 403

    coll = get_db().get_collection("inspection_responses")
    query = {"manager_id" if role == "manager" else "inspector_id": ObjectId(user["user_id"])}
    cursor = coll.find(query).sort("created_at", -1)

    out = []
    for d in cursor:
        out.append({
            "id": str(d["_id"]),
            "template_id": str(d["template_id"]),
            "task_id": d["task_id"],
            "created_at": d["created_at"].isoformat(),
        })
    return jsonify({"success": True, "data": out})

# -----------------------------------------------------------------------------
# Get single response
# -----------------------------------------------------------------------------
@responses_bp.route("/<resp_id>", methods=["GET"])
@require_auth
def get_response(resp_id):
    user = request.current_user
    try:
        obj_id = ObjectId(resp_id)
    except Exception:
        return jsonify({"success": False, "message": "Invalid id"}), 400

    coll = get_db().get_collection("inspection_responses")
    doc = coll.find_one({"_id": obj_id})
    if not doc:
        return jsonify({"success": False, "message": "Not found"}), 404

    if str(doc["manager_id"]) != user["user_id"] and str(doc["inspector_id"]) != user["user_id"]:
        return jsonify({"success": False, "message": "Forbidden"}), 403

    return jsonify({"success": True, "data": InspectionResponse.from_dict(doc).to_dict()})