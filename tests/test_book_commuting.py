import sys
import os

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
def setup_commuting_ride(client):
    """Registers user, logs in, and publishes a commuting ride."""

    # Register and Login
    client.post("/register", json={
        "username": "commuter",
        "email": "commuter@gmail.com",
        "password": "Test@1234",
        "confirm_password": "Test@1234"
    })
    client.post("/login", json={"email": "commuter@gmail.com", "password": "Test@1234"})

    # Publish commuting ride
    data = {
        "from_location": "Leeds",
        "to_location": "York",
        "category": "commuting",
        "recurrence_dates": ["2025-12-01", "2025-12-02"],
        "commute_times": ["08:00", "09:00"],
        "available_seats": "3",
        "price_per_seat": "8"
    }

    client.post("/publish_ride", data=data)

    # Return ride ID for test use
    with app.app_context():
        ride = publish_ride.query.first()
        return ride.id

# -------- TEST CASES --------

# Tests for a valid commuting ride
def test_book_commuting_loads(client, setup_commuting_ride):
    """Booking page loads for commuting ride."""
    ride_id = setup_commuting_ride
    response = client.get(f"/book_commuting/{ride_id}")
    assert response.status_code == 200
    assert b"commuting" in response.data.lower()

# Tests for missing date field
def test_book_commuting_missing_dates(client, setup_commuting_ride):
    """No dates selected for commuting ride."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "seats": "2",
        "email": "test@commute.com"
    }, follow_redirects=True)
    assert b"required fields" in response.data.lower()

# Tests for booking a commuting ride with invalid date format
def test_book_commuting_invalid_date_format(client, setup_commuting_ride):
    """Invalid date format should be rejected."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["12-31-2025"],  # Wrong format
        "seats": "1",
        "email": "format@test.com"
    }, follow_redirects=True)
    assert b"invalid date" in response.data.lower() or response.status_code == 400

# Tests for seat number is not an integer
def test_book_commuting_invalid_seat_number(client, setup_commuting_ride):
    """Non-integer seat input should fail."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["2025-12-01"],
        "seats": "abc",
        "email": "commuter@example.com"
    }, follow_redirects=True)
    assert b"invalid seat number" in response.data.lower()

# Tests for 0 and negative seat numbers
def test_book_commuting_zero_or_negative_seats(client, setup_commuting_ride):
    """Zero or negative seats are invalid."""
    ride_id = setup_commuting_ride
    for seats in ["0", "-2"]:
        response = client.post(f"/book_commuting/{ride_id}", data={
            "selected_dates": ["2025-12-01"],
            "seats": seats,
            "email": "bad@test.com"
        }, follow_redirects=True)
        assert b"invalid" in response.data.lower()

# Tests for missing email field for booking confirmation
def test_book_commuting_missing_email(client, setup_commuting_ride):
    """Missing email input."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["2025-12-01"],
        "seats": "2"
    }, follow_redirects=True)
    assert b"email" in response.data.lower()

# Tests for correct email format for booking confirmation
def test_book_commuting_invalid_email_format(client, setup_commuting_ride):
    """Email format should be validated."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["2025-12-01"],
        "seats": "1",
        "email": "invalid-email@@.com"
    }, follow_redirects=True)
    assert b"invalid email" in response.data.lower() or response.status_code in (400, 422)

# Tests for overbooking of ride
def test_book_commuting_exceeds_available(client, setup_commuting_ride):
    """Overbooking should trigger error."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["2025-12-01"],
        "seats": "10",
        "email": "over@commute.com"
    }, follow_redirects=True)
    assert b"not enough seats" in response.data.lower()

# Tests for booking a ride by an authenticated user (logged out user)
def test_book_commuting_unauthenticated(client, setup_commuting_ride):
    """Should not allow booking if logged out."""
    ride_id = setup_commuting_ride
    client.post("/logout")
    response = client.get(f"/book_commuting/{ride_id}")
    assert response.status_code == 302  # Redirects to login page
    assert "/login" in response.headers["Location"]  # Confirm redirection

# Tests for booking commuting rides with past dates (should be rejected if validated)
def test_book_commuting_past_date(client, setup_commuting_ride):
    """Booking a commuting ride with a past date should not be allowed (if validated)."""
    ride_id = setup_commuting_ride
    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["2020-01-01"],
        "seats": "1",
        "email": "past@test.com"
    }, follow_redirects=True)
    assert b"invalid date" in response.data.lower() or response.status_code in (400, 422)

# Test for successful redirection to payment page for valid commuting ride booking
def test_book_commuting_redirects_to_payment(client, setup_commuting_ride):
    """Valid booking should redirect to payment page."""
    ride_id = setup_commuting_ride

    response = client.post(f"/book_commuting/{ride_id}", data={
        "selected_dates": ["2025-12-01"],
        "seats": "2",
        "total_price": "16.0",
        "email": "test@example.com"
    }, follow_redirects=False)

    assert response.status_code == 302  # Check that it redirects
    redirected_url = response.headers["Location"]
    
    # Check redirection to the correct payment page
    assert f"/payment_page/{ride_id}/2/16.0" in redirected_url
    assert "selected_dates=2025-12-01" in redirected_url
    assert "email=test@example.com" in redirected_url

# # Tests for booking - still yet to decide
# def test_book_commuting_duplicate_booking(client, setup_commuting_ride):
#     """User shouldn't be able to book the same ride on same date twice."""
#     ride_id = setup_commuting_ride
#     booking_data = {
#         "selected_dates": ["2025-12-01"],
#         "seats": "1",
#         "email": "repeat@booking.com"
#     }
#     client.post(f"/book_commuting/{ride_id}", data=booking_data)
#     response = client.post(f"/book_commuting/{ride_id}", data=booking_data, follow_redirects=True)
#     assert b"already booked" in response.data.lower() or response.status_code in (400, 409)

