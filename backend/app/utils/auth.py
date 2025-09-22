import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from bson import ObjectId

logger = logging.getLogger(__name__)

class AuthUtils:
    """JWT Authentication utilities"""
    
    @staticmethod
    def generate_tokens(user_id, email, role):
        """Generate access and refresh tokens"""
        try:
            # Access token payload
            access_payload = {
                'user_id': str(user_id),
                'email': email,
                'role': role,
                'type': 'access',
                'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
                'iat': datetime.utcnow()
            }
            
            # Refresh token payload
            refresh_payload = {
                'user_id': str(user_id),
                'email': email,
                'type': 'refresh',
                'exp': datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
                'iat': datetime.utcnow()
            }
            
            # Generate tokens
            access_token = jwt.encode(
                access_payload,
                current_app.config['JWT_SECRET_KEY'],
                algorithm='HS256'
            )
            
            refresh_token = jwt.encode(
                refresh_payload,
                current_app.config['JWT_SECRET_KEY'],
                algorithm='HS256'
            )
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'Bearer',
                'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
            }
            
        except Exception as e:
            logger.error(f"Error generating tokens: {e}")
            raise
    
    @staticmethod
    def verify_token(token, token_type='access'):
        """Verify JWT token"""
        try:
            # Decode token
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=['HS256']
            )
            
            # Check token type
            if payload.get('type') != token_type:
                raise jwt.InvalidTokenError("Invalid token type")
            
            # Check if token is expired
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                raise jwt.ExpiredSignatureError("Token has expired")
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            raise
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            raise
    
    @staticmethod
    def get_token_from_header():
        """Extract token from Authorization header"""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return None
        
        try:
            # Check if header starts with 'Bearer '
            if not auth_header.startswith('Bearer '):
                return None
            
            # Extract token
            token = auth_header.split(' ')[1]
            return token
            
        except Exception as e:
            logger.error(f"Error extracting token from header: {e}")
            return None
    
    @staticmethod
    def get_current_user():
        """Get current user from token"""
        try:
            token = AuthUtils.get_token_from_header()
            if not token:
                return None
            
            payload = AuthUtils.verify_token(token, 'access')
            return payload
            
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Get current user from token
            current_user = AuthUtils.get_current_user()
            
            if not current_user:
                return jsonify({
                    'success': False,
                    'message': 'Authentication required',
                    'error': 'MISSING_TOKEN'
                }), 401
            
            # Add user info to request context
            request.current_user = current_user
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'success': False,
                'message': 'Token has expired',
                'error': 'TOKEN_EXPIRED'
            }), 401
            
        except jwt.InvalidTokenError:
            return jsonify({
                'success': False,
                'message': 'Invalid token',
                'error': 'INVALID_TOKEN'
            }), 401
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return jsonify({
                'success': False,
                'message': 'Authentication failed',
                'error': 'AUTH_ERROR'
            }), 401
    
    return decorated_function

def require_role(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get current user from token
                current_user = AuthUtils.get_current_user()
                
                if not current_user:
                    return jsonify({
                        'success': False,
                        'message': 'Authentication required',
                        'error': 'MISSING_TOKEN'
                    }), 401
                
                # Check if user has required role
                user_role = current_user.get('role')
                if user_role != required_role:
                    return jsonify({
                        'success': False,
                        'message': 'Insufficient permissions',
                        'error': 'INSUFFICIENT_PERMISSIONS'
                    }), 403
                
                # Add user info to request context
                request.current_user = current_user
                
                return f(*args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                return jsonify({
                    'success': False,
                    'message': 'Token has expired',
                    'error': 'TOKEN_EXPIRED'
                }), 401
                
            except jwt.InvalidTokenError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid token',
                    'error': 'INVALID_TOKEN'
                }), 401
                
            except Exception as e:
                logger.error(f"Role-based authentication error: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Authentication failed',
                    'error': 'AUTH_ERROR'
                }), 401
        
        return decorated_function
    return decorator

def require_roles(required_roles):
    """Decorator to require one of the specified roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get current user from token
                current_user = AuthUtils.get_current_user()
                
                if not current_user:
                    return jsonify({
                        'success': False,
                        'message': 'Authentication required',
                        'error': 'MISSING_TOKEN'
                    }), 401
                
                # Check if user has one of the required roles
                user_role = current_user.get('role')
                if user_role not in required_roles:
                    return jsonify({
                        'success': False,
                        'message': 'Insufficient permissions',
                        'error': 'INSUFFICIENT_PERMISSIONS'
                    }), 403
                
                # Add user info to request context
                request.current_user = current_user
                
                return f(*args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                return jsonify({
                    'success': False,
                    'message': 'Token has expired',
                    'error': 'TOKEN_EXPIRED'
                }), 401
                
            except jwt.InvalidTokenError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid token',
                    'error': 'INVALID_TOKEN'
                }), 401
                
            except Exception as e:
                logger.error(f"Role-based authentication error: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Authentication failed',
                    'error': 'AUTH_ERROR'
                }), 401
        
        return decorated_function
    return decorator 