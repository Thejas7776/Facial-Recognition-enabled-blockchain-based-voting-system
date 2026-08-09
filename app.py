from dotenv import load_dotenv
load_dotenv() # Load environment variables from .env file

import os
import logging
from flask import Flask
from extensions import db, Base
from werkzeug.middleware.proxy_fix import ProxyFix
from blockchain_utils import Blockchain

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Face Encodings and Uploads folder if they don't exist
FACE_ENCODINGS_FOLDER = 'face_encodings'
UPLOAD_FOLDER = 'static/uploads/symbols'

# create the app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key' # Change this in production
# Configuration for PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:7777@localhost:5432/voting_system' # REPLACE with your PostgreSQL credentials
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads/symbols'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# SMTP Configuration for Email Sending
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Example for Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER') or 'mailserviceforproject@gmail.com'  # Use environment variable or placeholder
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS') or 'bxqmwcvwpcnjujgu' # Use environment variable or placeholder
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or ('VoteSense Admin', app.config['MAIL_USERNAME'])

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['UPLOAD_FOLDER'] = 'static/uploads/symbols'

# initialize the app with the extension
db.init_app(app)


with app.app_context():
    # Initialize blockchain and attach to app
    app.blockchain = Blockchain()

    # Create face_encodings directory if it doesn't exist
    os.makedirs('face_encodings', exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Import models and routes
    import models
    
    # Create all database tables
    db.create_all()
    
    # Create default admin if none exists (with migration safety)
    try:
        from werkzeug.security import generate_password_hash
        admin_exists = models.Admin.query.first()
        if not admin_exists:
            default_admin = models.Admin(
                username='admin',
                email='admin@votingsystem.com',
                password_hash=generate_password_hash('admin123'),
                role='super_admin'
            )
            db.session.add(default_admin)
            db.session.commit()
            logging.info("Default admin created: username=admin, password=admin123")
    except Exception as e:
        logging.warning(f"Could not create default admin during startup: {str(e)}")
        logging.info("This is normal during database migrations. Run create_db.py to initialize the database.")

from routes import bp
app.register_blueprint(bp)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
