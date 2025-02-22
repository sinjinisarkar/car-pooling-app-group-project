from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db
from datetime import date, datetime

db = SQLAlchemy()

# User Table for Login and Accounts 
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # Store hashed passwords
    date_of_birth = db.Column(db.Date, nullable=False)  # Stores user's date of birth
    is_active = db.Column(db.Boolean, default=True) # to check if the user activation (user authentication)

    rides = db.relationship('publish_ride', backref='driver', lazy=True)  # A driver can post multiple rides

    def __repr__(self):
        return f"<User {self.username}>"
    
    # Flask-Login requires this method to return True if the user is active
    def is_active(self):
        return self.is_active

# Publish ride Table for driver to publish their rides
class publish_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    from_location = db.Column(db.String(200), nullable=False)
    to_location = db.Column(db.String(200), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    available_seats = db.Column(db.Integer, nullable=False)
    price_per_seat = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(20), nullable=False)  # "commuting" or "one-time"
    is_available = db.Column(db.Boolean, default=True)  # New field to track availability

    def __repr__(self):
        return f"<Published Ride {self.from_location} to {self.to_location} ({self.category}) Available: {self.is_available}>"

# Journey Table for viewing available journeys (user)
class view_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    from_location = db.Column(db.String(200), nullable=False)
    to_location = db.Column(db.String(200), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    price_per_seat = db.Column(db.Float, nullable=False)
    bookings = db.relationship('book_ride', backref='ride', lazy=True)  # One ride can have multiple bookings

# Booking Table for selecting and booking a journey (user)
class book_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('view_ride.id'), nullable=False)
    status = db.Column(db.String(20), default="Pending")  # Pending, Confirmed, Canceled


