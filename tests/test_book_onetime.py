import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride

# -------- FIXTURES --------

@pytest.fixture
def client():
    """Setup and teardown for Flask test client with in-memory DB."""
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        db.session.remove()
        db.drop_all()

@pytest.fixture
def setup_onetime_ride(client):
    """Registers user, logs in, and publishes a one-time ride."""
    client.post("/register", json={
        "username": "testuser",
        "email": "testuser@gmail.com",
        "password": "Test@1234",
        "confirm_password": "Test@1234"
    })
    client.post("/login", json={"email": "testuser@gmail.com", "password": "Test@1234"})

    ride_data = {
        "from_location": "Leeds",
        "to_location": "York",
        "category": "one-time",
        "date_time": "2025-12-01 10:00",
        "available_seats": "2",
        "price_per_seat": "10"
    }
    client.post("/publish_ride", data=ride_data)

    with app.app_context():
        ride = publish_ride.query.first()
        return ride.id, "2025-12-01"

# -------- TEST CASES --------

# Tests for a valid one time ride 
def test_book_onetime_valid(client, setup_onetime_ride):
    """Booking a valid one-time ride loads the page."""
    ride_id, date = setup_onetime_ride
    response = client.get(f"/book_onetime/{ride_id}?selected_date={date}")
    assert response.status_code == 200
    assert b"seats" in response.data

# Tests for missing date field 
def test_book_onetime_missing_date(client, setup_onetime_ride):
    """No date is selected while booking."""
    ride_id, _ = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "seats": "1",
        "email": "test@test.com"
    }, follow_redirects=True)
    assert b"date" in response.data.lower()

# Tests for seat number is not an integer
def test_book_onetime_invalid_seat_number(client, setup_onetime_ride):
    """Seat number is not an integer."""
    ride_id, date = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "selected_date": date,
        "seats": "abc",
        "email": "booker@example.com"
    })
    assert response.status_code == 400
    assert response.get_json()["error"].lower() == "invalid seat number"

# Tests for booking more seats than available
def test_book_onetime_exceeds_available(client, setup_onetime_ride):
    """Booking more seats than available should fail."""
    ride_id, date = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "selected_date": date,
        "seats": "10",  # more than available
        "email": "overbook@test.com"
    })
    assert response.status_code == 400
    assert "not enough" in response.get_json()["error"].lower()

# Tests for neative seat numbers 
def test_book_onetime_negative_seats(client, setup_onetime_ride):
    """Negative seat value is invalid."""
    ride_id, date = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "selected_date": date,
        "seats": "-1",
        "email": "neg@test.com"
    }, follow_redirects=True)
    assert response.status_code in (302, 400, 404) 

# Tests for 0 seats avaiable - cannot book
def test_book_onetime_zero_seats(client, setup_onetime_ride):
    """Zero seat is invalid."""
    ride_id, date = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "selected_date": date,
        "seats": "0",
        "email": "zero@test.com"
    })
    assert response.status_code == 400
    assert b"Invalid seat number" in response.data

# Tests for missing email for booking confirmation
def test_book_onetime_missing_email(client, setup_onetime_ride):
    """Missing email should trigger error."""
    ride_id, date = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "selected_date": date,
        "seats": "1"
    }, follow_redirects=True)
    assert b"email" in response.data.lower()

# Tests for booking of ride by an unauthenticated user (logged out user)
def test_book_onetime_unauthenticated(client, setup_onetime_ride):
    """Unauthenticated user should not access booking page."""
    ride_id, date = setup_onetime_ride
    client.post("/logout")
    response = client.get(f"/book_onetime/{ride_id}?selected_date={date}")
    assert response.status_code == 302

# Tests for booking a one-time ride with a past date (should be rejected if validated)
def test_book_onetime_past_date(client, setup_onetime_ride):
    """Booking a one-time ride with a past date should not be allowed (if validated)."""
    ride_id, _ = setup_onetime_ride
    response = client.post(f"/book_onetime/{ride_id}", data={
        "selected_date": "2020-01-01",
        "seats": "1",
        "email": "pastdate@test.com"
    }, follow_redirects=True)
    assert b"invalid date" in response.data.lower() or response.status_code in (400, 422)

# Test for redirecting to the payment page once one-time booking is confirmed
def test_book_onetime_redirects_to_payment(client, setup_onetime_ride):
    ride_id, date = setup_onetime_ride
    response = client.post(
        f"/book_onetime/{ride_id}",
        data={
            "seats": 2,
            "email": "test@example.com",
            "selected_date": date
        },
        follow_redirects=False
    )

    assert response.status_code == 302
    assert f"/payment/{ride_id}/2/20.0" in response.headers["Location"]
    assert f"selected_dates={date}" in response.headers["Location"]
    assert "email=test@example.com" in response.headers["Location"]
