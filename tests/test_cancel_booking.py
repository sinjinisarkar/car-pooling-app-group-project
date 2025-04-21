import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride, book_ride, Payment
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# -------- FIXTURES --------

@pytest.fixture
def client():
    """Sets up and tears down the Flask test client with an in-memory database."""
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        db.session.remove()
        db.drop_all()

@pytest.fixture
def setup_ride_and_booking(client):
    """Registers user, logs in, creates a ride, and books it."""
    with app.app_context():
        # Ensure no existing users with the same email
        existing_user = User.query.filter_by(email="commuter@gmail.com").first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        # Register and Login (Ensure the correct field names)
        client.post("/register", json={
            "username": "commuter",
            "email": "commuter@gmail.com",
            "password": "Test@1234",
            "confirm_password": "Test@1234"
        })
        client.post("/login", json={"email": "commuter@gmail.com", "password": "Test@1234"})
        
        # Create a user to assign as driver (with correct password field)
        driver = User(username="driver1", email="driver1@gmail.com", password_hash=generate_password_hash("driverpassword123"))
        db.session.add(driver)
        db.session.commit()
        
        ride = publish_ride(
            from_location="Leeds", 
            to_location="Manchester", 
            category="one-time", 
            date_time=datetime(2025, 10, 17, 12, 30), 
            available_seats_per_date={ "2025-10-17": 5 }, 
            price_per_seat=10.0,
            driver_id=driver.id,  # Assign the driver_id here
            driver_name=driver.username  # Set the driver_name field here
        )
        db.session.add(ride)
        db.session.commit()

        # Create a booking
        booking = book_ride(
            user_id=1, 
            ride_id=ride.id, 
            seats_selected=2, 
            ride_date=datetime(2025, 10, 17, 12, 30), 
            status="Booked", 
            total_price=20.0, 
            confirmation_email="user123@gmail.com"
        )
        db.session.add(booking)
        db.session.commit()

        # Add payment with ride_id and user_id from booking
        payment = Payment(
            user_id=booking.user_id,  # Assign the user_id from the booking
            book_ride_id=booking.id, 
            ride_id=ride.id,  # Assign the ride_id from the created ride
            amount=20.0, 
            status="Paid"
        )
        db.session.add(payment)
        db.session.commit()
    
    return booking, payment

# -------- TEST CASES --------

def test_cancel_booking_valid(client, setup_ride_and_booking):
    """Test that a valid booking cancellation works as expected."""
    booking, payment = setup_ride_and_booking
    
    # Simulate cancellation request
    response = client.post(f"/cancel_booking/{booking.id}")
    
    assert response.status_code == 200
    data = request.get_json()
    assert data['success'] is True
    assert "Booking successfully canceled" in data['message']
    assert payment.status == "Refunded"  # Check payment status
    assert booking.status == "Canceled"  # Check booking status

def test_cancel_booking_time_limit(client, setup_ride_and_booking):
    """Test that cancellation within 15 minutes is handled correctly."""
    booking, payment = setup_ride_and_booking
    
    # Simulate cancellation within 15 minutes of the ride time
    ride_time = datetime(2025, 10, 17, 12, 30)
    current_time = ride_time - timedelta(minutes=10)  # 10 minutes before the ride
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(datetime, 'now', lambda: current_time)
        response = client.post(f"/cancel_booking/{booking.id}")
    
    assert response.status_code == 200
    data = response.get_json()
    assert "Charged 75% cancellation fee" in data['message']
    assert payment.status == "Partially Refunded"  # Check payment status
    assert booking.status == "Canceled"  # Check booking status

def test_cancel_booking_full_refund(client, setup_ride_and_booking):
    """Test that cancellation before the ride time (15 minutes) returns a full refund."""
    booking, payment = setup_ride_and_booking
    
    # Simulate cancellation more than 15 minutes before the ride time
    ride_time = datetime(2025, 10, 17, 12, 30)
    current_time = ride_time - timedelta(minutes=20)  # 20 minutes before the ride
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(datetime, 'now', lambda: current_time)
        response = client.post(f"/cancel_booking/{booking.id}")
    
    assert response.status_code == 200
    data = response.get_json()
    assert "Full refund issued." in data['message']
    assert payment.status == "Refunded"  # Check payment status
    assert booking.status == "Canceled"  # Check booking status
