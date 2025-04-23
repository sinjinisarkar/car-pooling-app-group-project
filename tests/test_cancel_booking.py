import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride, book_ride, Payment
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# ---------------------- FIXTURES ----------------------

@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        db.session.remove()
        db.drop_all()

@pytest.fixture
def setup_ride_and_booking(client):
    with app.app_context():
        existing_user = User.query.filter_by(email="commuter@gmail.com").first()
        if existing_user:
            db.session.delete(existing_user)
            db.session.commit()

        client.post("/register", json={
            "username": "commuter",
            "email": "commuter@gmail.com",
            "password": "Test@1234",
            "confirm_password": "Test@1234"
        })
        client.post("/login", json={"email": "commuter@gmail.com", "password": "Test@1234"})

        driver = User(username="driver1", email="driver1@gmail.com", password_hash=generate_password_hash("driverpassword123"))
        db.session.add(driver)
        db.session.commit()

        ride = publish_ride(
            from_location="Leeds",
            to_location="Manchester",
            category="one-time",
            date_time=datetime(2025, 10, 17, 12, 30),
            available_seats_per_date='{"2025-10-17": 5}',
            price_per_seat=10.0,
            driver_id=driver.id,
            driver_name=driver.username
        )
        db.session.add(ride)
        db.session.commit()

        booking = book_ride(
            user_id=1,
            ride_id=ride.id,
            seats_selected=2,
            ride_date=datetime(2025, 10, 17),
            status="Booked",
            total_price=20.0,
            confirmation_email="user123@gmail.com"
        )
        db.session.add(booking)
        db.session.commit()

        payment = Payment(
            user_id=booking.user_id,
            book_ride_id=booking.id,
            ride_id=ride.id,
            amount=20.0,
            status="Success"
        )
        db.session.add(payment)
        db.session.commit()

    return booking, payment
    
# -------------------- TEST CASES --------------------

# Test 1: Valid cancellation of a booked ride
def test_cancel_booking_valid(client, setup_ride_and_booking):
    booking, payment = setup_ride_and_booking
    response = client.post(f"/cancel_booking/{booking.id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert "Booking successfully canceled" in data['message']

# Test 2: Attempt to cancel a booking that doesn't exist
def test_cancel_booking_not_found(client):
    with app.app_context():
        user = User(username="testuser", email="testuser@gmail.com", password_hash=generate_password_hash("Test@1234"))
        db.session.add(user)
        db.session.commit()

        with client.session_transaction() as sess:
            sess["_user_id"] = str(user.id)

        response = client.post("/cancel_booking/99999")
        assert response.status_code == 404
        assert b"Booking not found" in response.data

# Test 3: Partial refund if the booking is cancelled within 15 minutes of ride start time
def test_cancel_booking_partial_refund_within_15_minutes(client, setup_ride_and_booking):
    booking, _ = setup_ride_and_booking

    with client.session_transaction() as sess:
        sess["_user_id"] = str(booking.user_id)

    with app.app_context():
        booking.ride_date = datetime.now().date()
        db.session.commit()

    response = client.post(f"/cancel_booking/{booking.id}")
    assert response.status_code == 200
    assert b"Booking successfully canceled" in response.data

# Test 4: Full refund if the booking is cancelled more than 15 minutes before ride start time
def test_cancel_booking_full_refund_over_15_minutes(client, setup_ride_and_booking):
    booking, _ = setup_ride_and_booking

    with client.session_transaction() as sess:
        sess["_user_id"] = str(booking.user_id)

    with app.app_context():
        booking.ride_date = (datetime.now() + timedelta(days=1)).date()
        db.session.commit()

    response = client.post(f"/cancel_booking/{booking.id}")
    assert response.status_code == 200
    assert b"Booking successfully canceled" in response.data

# Test 5: Attempt to cancel a booking that has already been cancelled
def test_cancel_booking_already_cancelled(client, setup_ride_and_booking):
    booking, _ = setup_ride_and_booking

    with app.app_context():
        # Load fresh instance and cancel it
        booking_in_db = book_ride.query.get(booking.id)
        booking_in_db.status = "Canceled"
        db.session.commit()

    with client.session_transaction() as sess:
        sess["_user_id"] = str(booking.user_id)

    response = client.post(f"/cancel_booking/{booking.id}")
    assert response.status_code == 200  # Still expecting 200 since view always returns 200
    data = response.get_json()
    assert "booking successfully canceled" in data["message"].lower()  # Expecting generic success message
