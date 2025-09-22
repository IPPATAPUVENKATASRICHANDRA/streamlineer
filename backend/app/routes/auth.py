from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError
from bson import ObjectId
import logging
from datetime import datetime

from ..models.user import User, user_schema
from ..utils.auth import AuthUtils, require_auth
from ..utils.database import get_db
from ..utils.audit import log_user_event

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided',
                'error': 'NO_DATA'
            }), 400
        
        # Validate user data
        try:
            validated_data = user_schema.load(data)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'message': 'Validation error',
                'error': 'VALIDATION_ERROR',
                'details': e.messages
            }), 400
        
        # Validate password strength
        try:
            User.validate_password(validated_data['password'])
        except ValidationError as e:
            return jsonify({
                'success': False,
                'message': str(e),
                'error': 'WEAK_PASSWORD'
            }), 400
        
        # Get database connection
        db = get_db()
        users_collection = db.get_collection('users')
        
        # Check if user already exists
        existing_user = users_collection.find_one({'email': validated_data['email']})
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'User with this email already exists',
                'error': 'EMAIL_EXISTS'
            }), 409
        
        # Hash password
        password_hash = User.hash_password(validated_data['password'])
        
        # Create user object
        user = User(
            email=validated_data['email'],
            firstName=validated_data['firstName'],
            lastName=validated_data['lastName'],
            organization=validated_data['organization'],
            location=validated_data['location'],
            phone=validated_data['phone'],
            country_code=validated_data['country_code'],
            password_hash=password_hash,
            role=validated_data['role']
        )
        
        # Insert user into database
        result = users_collection.insert_one(user.to_dict())
        user._id = result.inserted_id

        # Audit log – account created
        log_user_event(
            user_id=user._id,
            email=user.email,
            first_name=user.firstName,
            last_name=user.lastName,
            event="ACCOUNT_CREATED"
        )

        # Developer-friendly console message
        print(f"✅ Account created: {user.firstName} ({user.role})")
        
        # Generate tokens
        tokens = AuthUtils.generate_tokens(
            user._id,
            user.email,
            user.role
        )
        
        logger.info(f"User registered successfully: {user.email}")
        
        return jsonify({
            'success': True,
            'message': f"Account created for {user.firstName} as {user.role}",
            'data': {
                'user': user.to_public_dict(),
                'tokens': tokens
            },
            'mongo_notification': 'ACCOUNT_CREATED'
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({
            'success': False,
            'message': 'Registration failed',
            'error': 'REGISTRATION_ERROR'
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        # Get request data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided',
                'error': 'NO_DATA'
            }), 400
        
        # Validate required fields
        email = data.get('email')
        password = data.get('password')
        organization = data.get('organization')
        location = data.get('location')
        
        if not all([email, password, organization, location]):
            return jsonify({
                'success': False,
                'message': 'Missing required fields',
                'error': 'MISSING_FIELDS'
            }), 400
        
        # Get database connection
        db = get_db()
        users_collection = db.get_collection('users')
        
        # Find user by email
        user_data = users_collection.find_one({'email': email})
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'Invalid credentials',
                'error': 'INVALID_CREDENTIALS'
            }), 401
        
        # Create user object
        user = User.from_dict(user_data)
        
        # Check if account is locked
        if user.is_account_locked():
            return jsonify({
                'success': False,
                'message': 'Account is locked due to too many failed attempts',
                'error': 'ACCOUNT_LOCKED'
            }), 423
        
        # Check if account is active
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated',
                'error': 'ACCOUNT_DEACTIVATED'
            }), 401
        
        # Verify password
        if not User.verify_password(user.password_hash, password):
            # Increment login attempts
            user.increment_login_attempts()
            
            # Check if account should be locked
            if user.login_attempts >= current_app.config['MAX_LOGIN_ATTEMPTS']:
                user.lock_account(current_app.config['ACCOUNT_LOCKOUT_DURATION'])
            
            # Update user in database
            # Exclude `_id` when performing an update to avoid immutable
            # field errors.
            users_collection.update_one(
                {'_id': user._id},
                {'$set': user.to_dict(include_id=False)}
            )
            
            return jsonify({
                'success': False,
                'message': 'Invalid credentials',
                'error': 'INVALID_CREDENTIALS'
            }), 401
        
        # Check organization and location
        if user.organization != organization or user.location != location:
            return jsonify({
                'success': False,
                'message': 'Invalid organization or location',
                'error': 'INVALID_ORGANIZATION_LOCATION'
            }), 401
        
        # Reset login attempts and update last login
        user.reset_login_attempts()
        user.update_last_login()
        
        # Persist the reset login attempts and last login timestamp. Again
        # we omit the immutable `_id` field.
        users_collection.update_one(
            {'_id': user._id},
            {'$set': user.to_dict(include_id=False)}
        )
        
        # Generate tokens
        tokens = AuthUtils.generate_tokens(
            user._id,
            user.email,
            user.role
        )
        
        # Audit log – successful login
        log_user_event(
            user_id=user._id,
            email=user.email,
            first_name=user.firstName,
            last_name=user.lastName,
            event="LOGIN_SUCCESS"
        )

        print(f"✅ Login success: {user.firstName} ({user.role})")
        
        return jsonify({
            'success': True,
            'message': f"Welcome {user.firstName} to Streamlineer!",
            'data': {
                'user': user.to_public_dict(),
                'tokens': tokens
            },
            'mongo_notification': 'LOGIN_SUCCESS'
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({
            'success': False,
            'message': 'Login failed',
            'error': 'LOGIN_ERROR'
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token endpoint"""
    try:
        # Get refresh token from request
        data = request.get_json()
        
        if not data or 'refresh_token' not in data:
            return jsonify({
                'success': False,
                'message': 'Refresh token required',
                'error': 'MISSING_REFRESH_TOKEN'
            }), 400
        
        refresh_token = data['refresh_token']
        
        # Verify refresh token
        try:
            payload = AuthUtils.verify_token(refresh_token, 'refresh')
        except Exception as e:
            return jsonify({
                'success': False,
                'message': 'Invalid refresh token',
                'error': 'INVALID_REFRESH_TOKEN'
            }), 401
        
        # Get user from database
        db = get_db()
        users_collection = db.get_collection('users')
        
        user_data = users_collection.find_one({'_id': ObjectId(payload['user_id'])})
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'User not found',
                'error': 'USER_NOT_FOUND'
            }), 404
        
        user = User.from_dict(user_data)
        
        # Check if user is active
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated',
                'error': 'ACCOUNT_DEACTIVATED'
            }), 401
        
        # Generate new tokens
        tokens = AuthUtils.generate_tokens(
            user._id,
            user.email,
            user.role
        )
        
        return jsonify({
            'success': True,
            'message': 'Token refreshed successfully',
            'data': {
                'tokens': tokens
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return jsonify({
            'success': False,
            'message': 'Token refresh failed',
            'error': 'REFRESH_ERROR'
        }), 500

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user profile"""
    try:
        # Get user from database
        db = get_db()
        users_collection = db.get_collection('users')
        
        user_data = users_collection.find_one({'_id': ObjectId(request.current_user['user_id'])})
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'User not found',
                'error': 'USER_NOT_FOUND'
            }), 404
        
        user = User.from_dict(user_data)
        
        return jsonify({
            'success': True,
            'message': 'User profile retrieved successfully',
            'data': {
                'user': user.to_public_dict()
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Get current user error: {e}")
        return jsonify({
            'success': False,
            'message': 'Failed to get user profile',
            'error': 'PROFILE_ERROR'
        }), 500

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """User logout endpoint"""
    try:
        # Get user information for the logout message
        db = get_db()
        users_collection = db.get_collection('users')
        
        user_data = users_collection.find_one({'_id': ObjectId(request.current_user['user_id'])})
        user_name = "User"
        if user_data:
            user_name = user_data.get('firstName', 'User')
        
        # In a stateless JWT system, logout is handled client-side
        # by removing the token from storage
        # However, you could implement a blacklist for additional security
        
        return jsonify({
            'success': True,
            'message': f'You are successfully logged out, {user_name}!'
        }), 200
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({
            'success': False,
            'message': 'Logout failed',
            'error': 'LOGOUT_ERROR'
        }), 500 