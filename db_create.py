from config import SQLALCHEMY_DATABASE_URI
from app import app, db
import os.path
from app.models import User, publish_ride, book_ride

# Create all database tables
with app.app_context():
    db.create_all()
