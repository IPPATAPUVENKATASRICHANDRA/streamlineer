import os
from app import create_app

# Ensure Flask CLI does not attempt to re-load the .env file with strict UTF-8
# decoding after we've already loaded it safely in `app.config`. This avoids
# a second UnicodeDecodeError when the file was saved with a non-UTF-8
# encoding (common on Windows when using Notepad).
os.environ.setdefault("FLASK_SKIP_DOTENV", "1")

# Create Flask app
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config['DEBUG']
    ) 
