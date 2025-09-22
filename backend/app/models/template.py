from datetime import datetime
from bson import ObjectId
from marshmallow import Schema, fields, validate

class TemplateSchema(Schema):
    """Marshmallow schema for Template validation"""

    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    pages = fields.List(fields.Dict(), required=True)
    manager_email = fields.Email(required=True)
    organization = fields.Str(required=True)
    location = fields.Str(required=True)
    status = fields.Str(validate=validate.OneOf(["draft", "submitted", "manager_edit", "published"]))
    
    # AQL Configuration fields
    aql_level = fields.Float(allow_none=True, validate=validate.Range(min=0.0, max=15.0))
    aql_level_critical = fields.Float(allow_none=True, validate=validate.Range(min=0.0, max=15.0))
    aql_level_major = fields.Float(allow_none=True, validate=validate.Range(min=0.0, max=15.0))
    aql_level_minor = fields.Float(allow_none=True, validate=validate.Range(min=0.0, max=15.0))
    lot_size = fields.Int(allow_none=True, validate=validate.Range(min=1))
    sample_size = fields.Int(allow_none=True, validate=validate.Range(min=1))
    major_defects_allowed = fields.Int(allow_none=True, validate=validate.Range(min=0))
    minor_defects_allowed = fields.Int(allow_none=True, validate=validate.Range(min=0))
    critical_defects_allowed = fields.Int(allow_none=True, validate=validate.Range(min=0))
    # Newly added: persist the chosen letter of code (e.g., 'J')
    letter_of_code = fields.Str(allow_none=True, validate=validate.Length(max=4))
    # Per-category code letters
    letter_of_code_critical = fields.Str(allow_none=True, validate=validate.Length(max=4))
    letter_of_code_major = fields.Str(allow_none=True, validate=validate.Length(max=4))
    letter_of_code_minor = fields.Str(allow_none=True, validate=validate.Length(max=4))
    defect_categories = fields.Dict(allow_none=True)
    # Optional: Store AQL reference tables (code letters and acceptance levels)
    aql_tables = fields.Dict(allow_none=True)
    # Optional rule structure will be embedded inside pages[].questions[].rules
    # We do not strictly validate here to allow flexible UI-driven schema.


class Template:
    """Template model for MongoDB storage"""

    def __init__(self, **kwargs):
        # Database identifier
        self._id = kwargs.get("_id")

        # Core data
        self.title = kwargs.get("title")
        self.description = kwargs.get("description", "")
        self.image_url = kwargs.get("image_url")
        self.pages = kwargs.get("pages", [])

        # Relations & metadata
        self.creator_id = kwargs.get("creator_id")  # IT person who created the template
        self.manager_id = kwargs.get("manager_id")
        self.manager_firstName = kwargs.get("manager_firstName")
        self.manager_lastName = kwargs.get("manager_lastName")
        self.organization = kwargs.get("organization")
        self.location = kwargs.get("location")
        self.status = kwargs.get("status", "draft")

        # AQL Configuration
        self.aql_level = kwargs.get("aql_level", 2.5)  # Default AQL level
        self.aql_level_critical = kwargs.get("aql_level_critical")
        self.aql_level_major = kwargs.get("aql_level_major")
        self.aql_level_minor = kwargs.get("aql_level_minor")
        self.lot_size = kwargs.get("lot_size")
        self.sample_size = kwargs.get("sample_size")
        self.major_defects_allowed = kwargs.get("major_defects_allowed")
        self.minor_defects_allowed = kwargs.get("minor_defects_allowed")
        self.critical_defects_allowed = kwargs.get("critical_defects_allowed")
        self.letter_of_code = kwargs.get("letter_of_code")
        self.letter_of_code_critical = kwargs.get("letter_of_code_critical")
        self.letter_of_code_major = kwargs.get("letter_of_code_major")
        self.letter_of_code_minor = kwargs.get("letter_of_code_minor")
        self.defect_categories = kwargs.get("defect_categories", {
            "critical": [],
            "major": [],
            "minor": []
        })
        # Reference tables for AQL (optional, for future use)
        self.aql_tables = kwargs.get("aql_tables")

        # Timestamps
        self.created_at = kwargs.get("created_at", datetime.utcnow())
        self.updated_at = kwargs.get("updated_at", datetime.utcnow())

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self, include_id: bool = True):
        """Convert the Template object to a dict ready for MongoDB."""
        doc = {
            "name": self.title,  # legacy compatibility with old unique index
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "pages": self.pages,
            "creator_id": self.creator_id,
            "manager_id": self.manager_id,
            "manager_firstName": self.manager_firstName,
            "manager_lastName": self.manager_lastName,
            "organization": self.organization,
            "location": self.location,
            "status": self.status,
            "aql_level": self.aql_level,
            "aql_level_critical": self.aql_level_critical,
            "aql_level_major": self.aql_level_major,
            "aql_level_minor": self.aql_level_minor,
            "lot_size": self.lot_size,
            "sample_size": self.sample_size,
            "major_defects_allowed": self.major_defects_allowed,
            "minor_defects_allowed": self.minor_defects_allowed,
            "critical_defects_allowed": self.critical_defects_allowed,
            "letter_of_code": self.letter_of_code,
            "letter_of_code_critical": self.letter_of_code_critical,
            "letter_of_code_major": self.letter_of_code_major,
            "letter_of_code_minor": self.letter_of_code_minor,
            "defect_categories": self.defect_categories,
            "aql_tables": self.aql_tables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_id and self._id is not None:
            doc["_id"] = self._id
        return doc

    @classmethod
    def from_dict(cls, data: dict):
        """Rehydrate a Template object from a MongoDB document."""
        return cls(**data)

    # ------------------------------------------------------------------
    # Public view
    # ------------------------------------------------------------------

    def public_view(self):
        """Return a dict safe for exposure via API (convert ObjectIds)."""
        return {
            "id": str(self._id) if self._id else None,
            "title": self.title,
            "description": self.description,
            "image_url": self.image_url,
            "pages": self.pages,
            "creator_id": str(self.creator_id) if isinstance(self.creator_id, ObjectId) else self.creator_id,
            "manager_id": str(self.manager_id) if isinstance(self.manager_id, ObjectId) else self.manager_id,
            "manager_firstName": self.manager_firstName,
            "manager_lastName": self.manager_lastName,
            "organization": self.organization,
            "location": self.location,
            "status": self.status,
            "aql_level": self.aql_level,
            "aql_level_critical": self.aql_level_critical,
            "aql_level_major": self.aql_level_major,
            "aql_level_minor": self.aql_level_minor,
            "lot_size": self.lot_size,
            "sample_size": self.sample_size,
            "major_defects_allowed": self.major_defects_allowed,
            "minor_defects_allowed": self.minor_defects_allowed,
            "critical_defects_allowed": self.critical_defects_allowed,
            "letter_of_code": self.letter_of_code,
            "letter_of_code_critical": self.letter_of_code_critical,
            "letter_of_code_major": self.letter_of_code_major,
            "letter_of_code_minor": self.letter_of_code_minor,
            "defect_categories": self.defect_categories,
            "aql_tables": self.aql_tables,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


template_schema = TemplateSchema()
