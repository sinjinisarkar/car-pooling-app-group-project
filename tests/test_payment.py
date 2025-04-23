import sys
import os
from datetime import datetime
from unittest.mock import patch
from flask import url_for

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
def setup_ride_and_user(client):
    client.post("/register", json={
        "username": "payuser",
        "email": "payuser@gmail.com",
        "password": "Test@1234",
        "confirm_password": "Test@1234"
    })
    client.post("/login", json={"email": "payuser@gmail.com", "password": "Test@1234"})

    ride_data = {
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-12-05 12:00",
        "available_seats": "4",
        "price_per_seat": "15"
    }
    client.post("/publish_ride", data=ride_data)
    ride = publish_ride.query.first()
    return ride

# -------------------- TEST CASES --------------------

# Test 1: Verifies the payment process works for a valid one-time ride booking
def test_one_time_payment_success(client, setup_ride_and_user):
    """Test successful payment flow with valid data."""
    ride = setup_ride_and_user
    payload = {
        "ride_id": ride.id,
        "seats": 2,
        "total_price": 30,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "payuser@gmail.com",
        "card_number": "1234567812345678",
        "expiry": "12/30",
        "cardholder_name": "John Doe",
        "cvv": "123",
        "save_card": False
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200
    assert response.json["success"] is True
    assert "Payment successful" in response.json["message"]

# Test 2: Verifies that a valid cardholder name is accepted
def test_cardholder_name_validation(client, setup_ride_and_user):
    """Check that a valid cardholder name is accepted."""
    ride = setup_ride_and_user
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "payuser@gmail.com",
        "card_number": "1234567812345678",
        "expiry": "12/30",
        "cardholder_name": "A",  # minimal valid
        "cvv": "123"
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200

# Test 3: Verifies that a valid cardholder number is accepted
def test_missing_card_number(client, setup_ride_and_user):
    """Missing card number should fail."""
    ride = setup_ride_and_user
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "payuser@gmail.com",
        "expiry": "12/30",
        "cardholder_name": "John Doe"
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 400
    assert "Card details missing" in response.json["message"]

# Test 4: Verifies for valid card number length
def test_card_number_length(client, setup_ride_and_user):
    """Test invalid card number length."""
    ride = setup_ride_and_user
    for bad_card in ["12345678", "12345678901234567890"]:
        payload = {
            "ride_id": ride.id,
            "seats": 1,
            "total_price": 15,
            "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
            "email": "payuser@gmail.com",
            "card_number": bad_card,
            "expiry": "12/30",
            "cardholder_name": "John",
            "cvv": "123"
        }
        response = client.post("/process_payment", json=payload)
        assert response.status_code == 400 or not response.json["success"]

# Test 5: Verfies for expiry date and its foramt
def test_valid_expiry_date(client, setup_ride_and_user):
    """Ensure expiry date is accepted if formatted correctly."""
    ride = setup_ride_and_user
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "payuser@gmail.com",
        "card_number": "1234567812345678",
        "expiry": "11/30",
        "cardholder_name": "Jane",
        "cvv": "321"
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200

# Tests 6: Verfires for valid CVV 
def test_valid_cvv_length(client, setup_ride_and_user):
    """Test valid CVV length (3 digits)."""
    ride = setup_ride_and_user
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "payuser@gmail.com",
        "card_number": "1234567812345678",
        "expiry": "12/25",
        "cardholder_name": "Doe",
        "cvv": "123"
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200

# Tests 7: Verifies for if card is saving when requested
def test_save_card_option(client, setup_ride_and_user):
    """Check that card is saved when requested."""
    ride = setup_ride_and_user
    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "savecard@test.com",
        "card_number": "9999888877776666",
        "expiry": "10/30",
        "cardholder_name": "Save Me",
        "cvv": "222",
        "save_card": True
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200
    assert SavedCard.query.filter_by(cardholder_name="Save Me").first() is not None

# Tests 8: Verifies for use of saved card (can the user use a already saved card)
def test_use_saved_card(client, setup_ride_and_user):
    """Test booking with an already saved card."""
    ride = setup_ride_and_user
    with app.app_context():
        card = SavedCard(
            user_id=1,
            expiry_date="10/30",
            cardholder_name="Saved",
        )
        card.set_card_number("1111222233334444")
        db.session.add(card)
        db.session.commit()
        saved_card_id = card.id

    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "saved@card.com",
        "use_saved_card": True,
        "saved_card_id": saved_card_id
    }
    response = client.post("/process_payment", json=payload)
    assert response.status_code == 200
    assert "Payment successful" in response.json["message"]

# Tests 9: Verifies for proper storing of booked one time ride on dashboard and sending a booking confirmation
def test_booking_dashboard_and_email(client, setup_ride_and_user):
    """Test that booking reflects on user dashboard and confirmation email is sent."""
    ride = setup_ride_and_user

    payload = {
        "ride_id": ride.id,
        "seats": 1,
        "total_price": 15,
        "selected_dates": [ride.date_time.strftime("%Y-%m-%d")],
        "email": "dashuser@gmail.com",
        "card_number": "4444555566667777",
        "expiry": "12/28",
        "cardholder_name": "Dash Tester",
        "cvv": "321",
        "save_card": False
    }

    # Patch the email function to avoid sending real email
    with patch("app.views.send_booking_confirmation_email") as mock_send_email:
        response = client.post("/process_payment", json=payload)
        assert response.status_code == 200
        assert response.json["success"] is True
        assert "booking confirmed" in response.json["message"].lower()

        # Check that confirmation email function was called
        mock_send_email.assert_called_once()

        # Check that booking exists in DB
        booking = book_ride.query.filter_by(confirmation_email="dashuser@gmail.com").first()
        assert booking is not None
        assert booking.ride_id == ride.id
        assert booking.status == "Booked"
        assert booking.seats_selected == 1

        # Simulate accessing the dashboard (authenticated)
        dashboard_response = client.get("/dashboard")  
        assert dashboard_response.status_code == 200
        assert b"Leeds" in dashboard_response.data  
        assert b"Manchester" in dashboard_response.data  
