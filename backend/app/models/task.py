"""Task model for MongoDB storage

A task represents a work item that can be assigned to users and tracked
through different statuses (todo, in_progress, review, completed).
"""

from datetime import datetime
from bson import ObjectId


class Task:
    """Task model for MongoDB storage"""

    def __init__(self, **kwargs):
        self._id = kwargs.get("_id")
        
        # Core task data
        self.title = kwargs.get("title")
        self.description = kwargs.get("description", "")
        self.priority = kwargs.get("priority", "medium")  # low, medium, high
        self.status = kwargs.get("status", "todo")  # todo, in_progress, review, completed
        self.is_completed = kwargs.get("is_completed", False)
        # Optional linkage to domain objects
        self.inspection_id = kwargs.get("inspection_id")  # ObjectId of related inspection
        self.template_id = kwargs.get("template_id")      # ObjectId of related template (optional)
        self.template_title = kwargs.get("template_title")  # convenience for display
        
        # Assignment
        self.assigned_to_id = kwargs.get("assigned_to_id")  # ObjectId of assigned user
        self.assigned_by_id = kwargs.get("assigned_by_id")  # ObjectId of user who assigned
        self.assigned_to_name = kwargs.get("assigned_to_name", "")
        self.assigned_by_name = kwargs.get("assigned_by_name", "")
        
        # Dates
        self.due_date = kwargs.get("due_date")
        self.completed_at = kwargs.get("completed_at")
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------
    def to_dict(self, include_id: bool = True):
        doc = {
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "is_completed": self.is_completed,
            "inspection_id": ObjectId(self.inspection_id) if isinstance(self.inspection_id, str) else self.inspection_id,
            "template_id": ObjectId(self.template_id) if isinstance(self.template_id, str) else self.template_id,
            "template_title": self.template_title,
            "assigned_to_id": ObjectId(self.assigned_to_id) if isinstance(self.assigned_to_id, str) else self.assigned_to_id,
            "assigned_by_id": ObjectId(self.assigned_by_id) if isinstance(self.assigned_by_id, str) else self.assigned_by_id,
            "assigned_to_name": self.assigned_to_name,
            "assigned_by_name": self.assigned_by_name,
            "due_date": self.due_date,
            "completed_at": self.completed_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_id and self._id is not None:
            doc["_id"] = self._id
        return doc

    @classmethod
    def from_dict(cls, data: dict):
        """Re-hydrate from MongoDB document"""
        return cls(**data)

    # ------------------------------------------------------------------
    # Public view (for API)
    # ------------------------------------------------------------------
    def public_view(self):
        return {
            "id": str(self._id) if self._id else None,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "is_completed": self.is_completed,
            "inspection_id": str(self.inspection_id) if isinstance(self.inspection_id, ObjectId) else (self.inspection_id or None),
            "template_id": str(self.template_id) if isinstance(self.template_id, ObjectId) else (self.template_id or None),
            "template_title": self.template_title,
            "assigned_to_id": str(self.assigned_to_id) if isinstance(self.assigned_to_id, ObjectId) else self.assigned_to_id,
            "assigned_by_id": str(self.assigned_by_id) if isinstance(self.assigned_by_id, ObjectId) else self.assigned_by_id,
            "assigned_to_name": self.assigned_to_name,
            "assigned_by_name": self.assigned_by_name,
            # roles are optionally enriched at route layer
            "assigned_to_role": getattr(self, "assigned_to_role", None),
            "assigned_by_role": getattr(self, "assigned_by_role", None),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------
    def mark_completed(self):
        """Mark task as completed"""
        self.status = "completed"
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_status(self, new_status: str):
        """Update task status"""
        valid_statuses = ["todo", "in_progress", "review", "completed"]
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        self.status = new_status
        if new_status == "completed":
            self.is_completed = True
            self.completed_at = datetime.utcnow()
        else:
            self.is_completed = False
            self.completed_at = None
        
        self.updated_at = datetime.utcnow()
