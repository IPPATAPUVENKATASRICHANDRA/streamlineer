from datetime import datetime
from bson import ObjectId

class InspectionResponse:
    """Mongo document representing a completed inspection by an inspector"""

    def __init__(self, **kwargs):
        self._id = kwargs.get("_id")
        # ids --------------------------------------------------------------
        self.template_id = kwargs.get("template_id")  # ObjectId
        self.task_id     = kwargs.get("task_id")      # scheduler local id (string/number)
        self.inspector_id = kwargs.get("inspector_id")  # ObjectId
        self.manager_id   = kwargs.get("manager_id")    # ObjectId – who assigned
        # payload ----------------------------------------------------------
        self.answers   = kwargs.get("answers", {})      # dict or list – UI defined
        self.created_at = kwargs.get("created_at", datetime.utcnow())

    # ------------------------------------------------------------------
    def to_dict(self, include_id: bool = True):
        doc = {
            "template_id": ObjectId(self.template_id) if not isinstance(self.template_id, ObjectId) else self.template_id,
            "task_id": self.task_id,
            "inspector_id": ObjectId(self.inspector_id) if not isinstance(self.inspector_id, ObjectId) else self.inspector_id,
            "manager_id": ObjectId(self.manager_id) if not isinstance(self.manager_id, ObjectId) else self.manager_id,
            "answers": self.answers,
            "created_at": self.created_at,
        }
        if include_id and self._id is not None:
            doc["_id"] = self._id
        return doc

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)
