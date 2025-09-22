"""Inspection / Scheduled template model

An inspection represents a published template that has been scheduled by a
manager to be completed by an inspector.  It stores the link back to the
template as well as the responses once the inspector has completed the
inspection.
"""

from datetime import datetime
from bson import ObjectId


class Inspection:  # pylint: disable=too-many-instance-attributes
    """Inspection model for MongoDB storage"""

    def __init__(self, **kwargs):
        self._id = kwargs.get("_id")
        # Foreign keys
        self.template_id = kwargs.get("template_id")  # ObjectId of template
        self.inspector_id = kwargs.get("inspector_id")  # ObjectId of inspector user
        self.manager_id = kwargs.get("manager_id")  # ObjectId of manager user (creator)

        # Scheduling meta
        # Optional – when the manager wants the inspection performed.
        self.scheduled_date = kwargs.get("scheduled_date")  # datetime or None

        # Progress / data
        self.status = kwargs.get("status", "assigned")  # assigned, in_progress, completed
        self.responses = kwargs.get("responses", {})  # dict(question_id -> answer)
        self.completed_at = kwargs.get("completed_at")
        # Actions derived from rule evaluations
        # Fallback to legacy field name 'rule_actions' if present
        self.remaining_actions = kwargs.get("remaining_actions", kwargs.get("rule_actions", []))

        # AQL Results
        self.aql_results = kwargs.get("aql_results", {})  # AQL analysis results
        self.defect_counts = kwargs.get("defect_counts", {
            "critical": 0,
            "major": 0,
            "minor": 0
        })
        self.aql_passed = kwargs.get("aql_passed", True)
        self.aql_rejection_reasons = kwargs.get("aql_rejection_reasons", [])

        # Audit
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self, include_id: bool = True):
        """Convert the Inspection object to a dict ready for MongoDB."""
        doc = {
            "template_id": ObjectId(self.template_id) if not isinstance(self.template_id, ObjectId) else self.template_id,
            "inspector_id": ObjectId(self.inspector_id) if not isinstance(self.inspector_id, ObjectId) else self.inspector_id,
            "manager_id": ObjectId(self.manager_id) if not isinstance(self.manager_id, ObjectId) else self.manager_id,
            "scheduled_date": self.scheduled_date,
            "status": self.status,
            "responses": self.responses,
            "completed_at": self.completed_at,
            "remaining_actions": self.remaining_actions,
            "aql_results": self.aql_results,
            "defect_counts": self.defect_counts,
            "aql_passed": self.aql_passed,
            "aql_rejection_reasons": self.aql_rejection_reasons,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_id and self._id is not None:
            doc["_id"] = self._id
        return doc

    @classmethod
    def from_dict(cls, data: dict):
        """Rehydrate an Inspection object from a MongoDB document."""
        return cls(**data)

    # ------------------------------------------------------------------
    # Public view
    # ------------------------------------------------------------------

    def public_view(self):
        """Return a dict safe for exposure via API (convert ObjectIds)."""
        return {
            "id": str(self._id) if self._id else None,
            "template_id": str(self.template_id) if isinstance(self.template_id, ObjectId) else self.template_id,
            "inspector_id": str(self.inspector_id) if isinstance(self.inspector_id, ObjectId) else self.inspector_id,
            "manager_id": str(self.manager_id) if isinstance(self.manager_id, ObjectId) else self.manager_id,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "status": self.status,
            "responses": self.responses,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "remaining_actions": self.remaining_actions,
            "aql_results": self.aql_results,
            "defect_counts": self.defect_counts,
            "aql_passed": self.aql_passed,
            "aql_rejection_reasons": self.aql_rejection_reasons,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
