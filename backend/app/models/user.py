from datetime import datetime
from bson import ObjectId
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from marshmallow import Schema, fields, validate, ValidationError
import re

# Initialize password hasher
ph = PasswordHasher()

class UserSchema(Schema):
    """Marshmallow schema for user validation"""
    
    email = fields.Email(required=True, validate=validate.Length(min=5, max=255))
    firstName = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    lastName = fields.Str(required=True, validate=validate.Length(min=1, max=50))
    organization = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    location = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    phone = fields.Str(required=True, validate=validate.Length(min=6, max=15))
    country_code = fields.Str(required=True, validate=validate.Length(min=1, max=5))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    role = fields.Str(required=True, validate=validate.OneOf(['inspector', 'it', 'manager']))
    terms = fields.Bool(required=True, validate=validate.Equal(True))

class User:
    """User model for MongoDB"""
    
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id')
        self.email = kwargs.get('email')
        self.firstName = kwargs.get('firstName')
        self.lastName = kwargs.get('lastName')
        self.organization = kwargs.get('organization')
        self.location = kwargs.get('location')
        self.phone = kwargs.get('phone')
        self.country_code = kwargs.get('country_code')
        self.password_hash = kwargs.get('password_hash')
        self.role = kwargs.get('role')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.is_active = kwargs.get('is_active', True)
        self.email_verified = kwargs.get('email_verified', False)
        self.last_login = kwargs.get('last_login')
        self.login_attempts = kwargs.get('login_attempts', 0)
        self.account_locked = kwargs.get('account_locked', False)
        self.lockout_until = kwargs.get('lockout_until')
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number")
        
        return True
    
    @staticmethod
    def hash_password(password):
        """Hash password using Argon2"""
        return ph.hash(password)
    
    @staticmethod
    def verify_password(password_hash, password):
        """Verify password against hash"""
        try:
            ph.verify(password_hash, password)
            return True
        except VerifyMismatchError:
            return False
    
    def to_dict(self, include_id=True):
        """Convert user object to dictionary for MongoDB.

        Parameters
        ----------
        include_id : bool, optional
            Whether to include the MongoDB `_id` field. This should be
            *False* when building an update payload for an existing
            document because MongoDB does not allow updating the immutable
            `_id` field. Defaults to *True* so that inserts keep the
            existing behaviour.
        """

        user_dict = {
            'email': self.email,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'organization': self.organization,
            'location': self.location,
            'phone': self.phone,
            'country_code': self.country_code,
            'password_hash': self.password_hash,
            'role': self.role,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'last_login': self.last_login,
            'login_attempts': self.login_attempts,
            'account_locked': self.account_locked,
            'lockout_until': self.lockout_until
        }

        # Only include the identifier when explicitly requested. This keeps
        # the original behaviour for inserts while avoiding immutable field
        # errors during updates.
        if include_id and self._id is not None:
            user_dict['_id'] = self._id

        return user_dict
    
    @classmethod
    def from_dict(cls, data):
        """Create user object from dictionary"""
        return cls(**data)
    
    def to_public_dict(self):
        """Convert user object to public dictionary (without sensitive data)"""
        return {
            'id': str(self._id) if self._id else None,
            'email': self.email,
            'firstName': self.firstName,
            'lastName': self.lastName,
            'organization': self.organization,
            'location': self.location,
            'phone': self.phone,
            'country_code': self.country_code,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def increment_login_attempts(self):
        """Increment failed login attempts"""
        self.login_attempts += 1
        self.updated_at = datetime.utcnow()
    
    def reset_login_attempts(self):
        """Reset login attempts"""
        self.login_attempts = 0
        self.account_locked = False
        self.lockout_until = None
        self.updated_at = datetime.utcnow()
    
    def lock_account(self, lockout_duration=900):  # 15 minutes default
        """Lock account due to too many failed attempts"""
        from datetime import timedelta
        self.account_locked = True
        self.lockout_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
        self.updated_at = datetime.utcnow()
    
    def is_account_locked(self):
        """Check if account is currently locked"""
        if not self.account_locked:
            return False
        
        if self.lockout_until and datetime.utcnow() > self.lockout_until:
            # Lockout period expired, unlock account
            self.account_locked = False
            self.lockout_until = None
            return False
        
        return True

# User validation schema instance
user_schema = UserSchema() 