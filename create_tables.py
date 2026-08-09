import os
import logging
from datetime import datetime
import pytz

from app import app
from extensions import db
from models import Admin, Election

logging.basicConfig(level=logging.INFO)

# Define IST timezone
ist_timezone = pytz.timezone('Asia/Kolkata')


with app.app_context():
    logging.info("Dropping existing tables...")
    db.drop_all()
    logging.info("Creating new tables...")
    db.create_all()

    # Create a default admin user
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin', email='admin@example.com', role='super_admin')
        admin.set_password('admin123')
        db.session.add(admin)
        logging.info("Default admin created: username=admin, password=admin123, role=super_admin")
    
    db.session.commit()
    logging.info("Database setup completed successfully! ✅")

print("Database created successfully!")
