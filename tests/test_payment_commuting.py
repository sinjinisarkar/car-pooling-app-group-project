import sys
import os
from datetime import datetime
from unittest.mock import patch
from flask import url_for
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride, SavedCard, book_ride

# ---------------------- FIXTURES ----------------------

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
def setup_commuting_ride(client):
    """Register a user and publish a commuting ride with available seats for multiple dates."""
    # Register a new user
    client.post("/register", json={
        "username": "commuter",
        "email": "commuter@gmail.com",
        "password": "Commute@123",
        "confirm_password": "Commute@123"
    })
    # Log in the user
    client.post("/login", json={"email": "commuter@gmail.com", "password": "Commute@123"})

    # Fetch the user from the database
    user = User.query.filter_by(email="commuter@gmail.com").first()

    seat_tracking = {
        "2025-12-01": 4,
        "2025-12-02": 3,
        "2025-12-03": 5
    }

    # Create a new ride instance
    commuting_ride = publish_ride(
        driver_id=user.id,  # Assign the driver's user ID
        driver_name=user.username,
        from_location="Bristol",
        to_location="Bath",
        category="commuting",
        available_seats_per_date=json.dumps(seat_tracking),
        price_per_seat=10.0,
        date_time=datetime.strptime("2025-12-01 08:00", "%Y-%m-%d %H:%M"),
        is_available=True
    )

    db.session.add(commuting_ride)
    db.session.commit()

    return commuting_ride

# -------------------- TEST CASES --------------------

# Test 1: Verifies for successful payment for commuting ride
def test_commuting_payment_success(client, setup_commuting_ride):
    """Test successful payment flow with valid datas."""
    ride = setup_commuting_ride
    payload = {
        "ride_id": ride.id,
        "seats": 2,
        "total_price": 20,
        "selected_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
        "email": "commuter@gmail.com",
        "card_number": "2222333344445555",
        "expiry": "10/28",
        "cardholder_name": "Daily Rider",
        "cvv": "456",
        "save_card": False
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200
    assert response.json["success"] is True

# Test 2: Verifies for ride published with multiple dates
def test_commuting_multiple_dates(client, setup_commuting_ride):
    """Test successful payment flow with multiple data."""
    ride = setup_commuting_ride
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 30,  # 3 days * 1 seat * 10
        "selected_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
        "email": "multi@commute.com",
        "card_number": "1234432112344321",
        "expiry": "11/26",
        "cardholder_name": "Multi Commuter",
        "cvv": "999",
        "save_card": True
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200
    assert response.json["success"] is True
    assert "Payment successful" in response.json["message"]

# Test 3: Verifies for commuting ride booking with more than available seats
def test_commuting_invalid_seat_date(client, setup_commuting_ride):
    """Test booking a commuting ride with more than the avaiable seats"""
    ride = setup_commuting_ride
    payload = {
        "ride_id": ride.id,
        "seats": 5,  # Only 3 seats available on 2025-12-02
        "total_price": 50,
        "selected_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
        "email": "fail@commute.com",
        "card_number": "8765432187654321",
        "expiry": "09/30",
        "cardholder_name": "Fail Tester",
        "cvv": "321",
        "save_card": False
    }
    response = client.post("/process_payment", json=payload)

    assert response.status_code == 200
    assert response.json["success"] is True
    assert "Payment successful" in response.json["message"]

    # Optionally verify that seats have been reduced to zero (depending on your logic)
    updated_ride = publish_ride.query.get(ride.id)
    updated_seats = json.loads(updated_ride.available_seats_per_date)
    assert updated_seats["2025-12-02"] == 0

# Test 4: Verifies for booking confirmation email sent after successful booking of the ride
def test_commuting_booking_and_email(client, setup_commuting_ride):
    """Test that booking reflects on dashboard and confirmation email is sent."""
    ride = setup_commuting_ride
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 10,
        "selected_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
        "email": "emailcheck@commute.com",
        "card_number": "0000111122223333",
        "expiry": "01/29",
        "cardholder_name": "Email Check",
        "cvv": "111",
        "save_card": False
    }

    with patch("app.views.send_booking_confirmation_email") as mock_send_email:
        response = client.post("/process_payment", json=payload)
        assert response.status_code == 200
        assert response.json["success"] is True
        mock_send_email.assert_called_once()
        booking = book_ride.query.filter_by(confirmation_email="emailcheck@commute.com").first()
        assert booking is not None
        assert booking.status == "Booked"

# Test 5: Verifies for proper storing of booked commuting ride on dashboard
def test_commuting_ride_displayed_on_dashboard(client, setup_commuting_ride):
    """Ensure that a successfully booked commuting ride appears on the user's dashboard."""
    ride = setup_commuting_ride

    # Book the ride
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 10,
        "selected_dates": ["2025-12-01", "2025-12-02", "2025-12-03"],
        "email": "commuter@gmail.com",
        "card_number": "1234567812345678",
        "expiry": "12/28",
        "cardholder_name": "Dashboard Check",
        "cvv": "111",
        "save_card": False
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200

    dashboard_response = client.get("/dashboard")  

    assert dashboard_response.status_code == 200
    assert b"Bristol" in dashboard_response.data  
    assert b"Bath" in dashboard_response.data  


