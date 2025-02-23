from config import SQLALCHEMY_DATABASE_URI
from app import app, db
import os.path
from app.models import User, publish_ride, view_ride, book_ride  # Import all models

# Create all database tables
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")
