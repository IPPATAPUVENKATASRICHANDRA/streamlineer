from flask import Flask
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os

from .config import config
from .utils.database import init_db
from .routes.auth import auth_bp

def create_app(config_name='default'):
    """Application factory function"""
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/streamlineer.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Streamlineer startup')
    
    # Initialize CORS
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Initialize database
    if not init_db(app):
        app.logger.error("Failed to initialize database")
        # Continue running but log the error
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    # Template management endpoints
    from .routes.template import template_bp
    app.register_blueprint(template_bp)

    from .routes.inspection import inspection_bp
    app.register_blueprint(inspection_bp)

    from .routes.users import users_bp
    app.register_blueprint(users_bp)

    # Inspection responses (inspector submissions)
    from .routes.inspection_responses import responses_bp
    app.register_blueprint(responses_bp)

    # Task management endpoints
    from .routes.tasks import tasks_bp
    app.register_blueprint(tasks_bp)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        return {
            'status': 'healthy',
            'message': 'Streamlineer API is running',
            'version': '1.0.0'
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {
            'success': False,
            'message': 'Endpoint not found',
            'error': 'NOT_FOUND'
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return {
            'success': False,
            'message': 'Internal server error',
            'error': 'INTERNAL_ERROR'
        }, 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Unhandled Exception: {e}')
        return {
            'success': False,
            'message': 'An unexpected error occurred',
            'error': 'UNEXPECTED_ERROR'
        }, 500
    
    return app 