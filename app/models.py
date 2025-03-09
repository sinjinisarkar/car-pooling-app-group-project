from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db
from datetime import date, datetime
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash

# Association table to track which passengers booked which rides
passenger_rides = db.Table(
    'passenger_rides',
    db.Column('passenger_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('ride_id', db.Integer, db.ForeignKey('publish_ride.id'), primary_key=True)
)

# Table for user Login and Accounts 
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # Stores hashed passwords
    is_active = db.Column(db.Boolean, default=True) # to check if the user activation (user authentication)

     # Relationship: A driver can publish multiple rides
    published_rides = db.relationship('publish_ride', backref='driver', lazy=True)

    # Relationship: A passenger can book multiple rides
    booked_rides = db.relationship('publish_ride', secondary=passenger_rides, backref='passengers')
        
     # Method to set hashed password
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Method to check hashed password
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

     # Generate Password Reset Token
    def generate_reset_password_token(self, secret_key, expires_in=600):
        """Generates a secure token for password reset."""
        serializer = URLSafeTimedSerializer(secret_key)
        return serializer.dumps({'email': self.email}, salt=self.password_hash)
    
    # Validate Password Reset Token
    @staticmethod
    def validate_reset_password_token(token, secret_key, user_id):
        """Validates the reset token and returns the user if valid."""
        serializer = URLSafeTimedSerializer(secret_key)
        user = User.query.get(user_id)
        if not user:
            return None
        try:
            data = serializer.loads(token, salt=user.password_hash, max_age=600)  # 10 min expiry
        except Exception:
            return None
        return user if data.get('email') == user.email else None
    
    def __repr__(self):
        return f"<User {self.username}>"

# Table for driver to publish ride
class publish_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)  # Added Driver Name
    from_location = db.Column(db.String(200), nullable=False)
    to_location = db.Column(db.String(200), nullable=False)
    date_time = db.Column(db.DateTime, nullable=True)  # Now optional
    available_seats_per_date = db.Column(db.JSON, nullable=True)  
    price_per_seat = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    recurrence_dates = db.Column(db.String(255), nullable=True)  
    commute_times = db.Column(db.String(255), nullable=True)  # Stores commute time slots
    is_available = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Published Ride {self.from_location} to {self.to_location}>"


# Table booking a journey from avaliable journeys (user/passenger)
class book_ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('publish_ride.id'), nullable=False)
    status = db.Column(db.String(20), default="Booked")
    total_price = db.Column(db.Float, nullable=False)  # Stores the total price of the booking
    seats_selected = db.Column(db.Integer, nullable=False)  # Stores the number of seats selected
    confirmation_email = db.Column(db.String(150), nullable=False)  # Stores the email address for confirmation
    ride_date = db.Column(db.DateTime, nullable=True)  # ✅ Make this nullable for commuting rides
    
    ride = db.relationship('publish_ride', backref='bookings')

    def __repr__(self):
        return f"<Booking for {self.ride.from_location} to {self.ride.to_location}>"

# Table for saved journey for easy rebooking for a commuting ride
class SavedRide(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('publish_ride.id'), nullable=False)
    recurrence_days = db.Column(db.String(100), nullable=True)  # Stored as "Monday, Wednesday"
    
    # Define relationships
    user = db.relationship('User', backref='saved_rides')
    ride = db.relationship('publish_ride', backref='saved_rides')

# Table for payment of the booked journeys
class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ride_id = db.Column(db.Integer, db.ForeignKey('publish_ride.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Success")  # Simulated Payment Success
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
