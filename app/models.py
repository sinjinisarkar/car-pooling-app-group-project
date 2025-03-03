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

class publish_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)  # Added Driver Name
    from_location = db.Column(db.String(200), nullable=False)
    to_location = db.Column(db.String(200), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    available_seats = db.Column(db.Integer, nullable=False)
    price_per_seat = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Published Ride {self.from_location} to {self.to_location}>"

# Journey Table for viewing available journeys (user)
class view_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)  # Add this line
    from_location = db.Column(db.String(100), nullable=False)
    to_location = db.Column(db.String(100), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    price_per_seat = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Ensure this line exists

    driver = db.relationship('User', backref='rides')

# Table for user/passenger to book a ride  
class book_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('publish_ride.id'), nullable=False)
    status = db.Column(db.String(20), default="Booked")
    total_price = db.Column(db.Float, nullable=False)  # Stores the total price of the booking
    seats_selected = db.Column(db.Integer, nullable=False)  # Stores the number of seats selected
    confirmation_email = db.Column(db.String(150), nullable=False)  # Stores the email address for confirmation
    ride_date = db.Column(db.DateTime, nullable=False)  # Stores the date and time of the booked ride
    
    # Define the relationship to the publish_ride model
    ride = db.relationship('publish_ride', backref='bookings')

    def __repr__(self):
        return f"<Booking for {self.ride.from_location} to {self.ride.to_location}>"