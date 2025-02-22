from config import SQLALCHEMY_DATABASE_URI
from app import db
from models import User, publish_ride, view_ride, book_ride  # Import all models

# Create all database tables
db.create_all()

print("Database tables created successfully!")
