from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db
from datetime import date, datetime

# Association table to track which passengers booked which rides
passenger_rides = db.Table(
    'passenger_rides',
    db.Column('passenger_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('ride_id', db.Integer, db.ForeignKey('publish_ride.id'), primary_key=True)
)

# User Table for Login and Accounts 
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # Stores hashed passwords
    date_of_birth = db.Column(db.String(10), nullable=True)  # Store DOB
    is_active = db.Column(db.Boolean, default=True) # to check if the user activation (user authentication)

     # Relationship: A driver can publish multiple rides
    published_rides = db.relationship('publish_ride', backref='driver', lazy=True)

    # Relationship: A passenger can book multiple rides
    booked_rides = db.relationship('publish_ride', secondary=passenger_rides, backref='passengers')
    
    def __repr__(self):
        return f"<User {self.username}>"
    
     # Method to set hashed password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Method to check hashed password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)



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
