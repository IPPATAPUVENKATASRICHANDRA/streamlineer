from datetime import datetime
from bson import ObjectId
from .database import get_db

def log_user_event(user_id: ObjectId | str, email: str, first_name: str | None, last_name: str | None, event: str):
    """Persist a simple user-centric audit log entry to MongoDB.

    Parameters
    ----------
    user_id : ObjectId | str
        The MongoDB identifier of the user (will be cast to ObjectId if
        given as a string).
    email : str
        User e-mail address.
    first_name, last_name : str | None
        Names to display in human-readable dashboards.
    event : str
        Short event label, e.g. "ACCOUNT_CREATED", "LOGIN_SUCCESS".
    """
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except Exception:
            # leave as string if it cannot be parsed
            pass

    db = get_db()
    logs = db.get_collection("user_logs")
    logs.insert_one({
        "user_id": user_id,
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "event": event,
        "timestamp": datetime.utcnow(),
    }) 


def log_inspection_audit(
    inspection_id: ObjectId | str,
    user_id: ObjectId | str,
    action: str,
    details: dict | None = None,
):
    """Persist an inspection-specific audit log entry.

    action examples: SUBMIT, EDIT, PHOTO_UPLOAD, DEFECT_ADD, DEFECT_EDIT, DEFECT_DELETE, OVERRIDE_DECISION
    """
    try:
        if isinstance(inspection_id, str):
            inspection_id = ObjectId(inspection_id)
    except Exception:
        # keep as string if cannot be parsed
        pass

    try:
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
    except Exception:
        pass

    db = get_db()
    logs = db.get_collection("inspection_audits")
    logs.insert_one({
        "inspection_id": inspection_id,
        "user_id": user_id,
        "action": action,
        "details": details or {},
        "timestamp": datetime.utcnow(),
    })