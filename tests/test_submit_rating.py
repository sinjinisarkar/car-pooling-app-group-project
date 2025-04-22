
import sys
import os
from datetime import datetime, timedelta
from flask import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride, book_ride, RideRating
from werkzeug.security import generate_password_hash

# -------------------- FIXTURES --------------------

@pytest.fixture
def client():
    """Creates a test client and application context for each test."""
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

def login_as(client, user_id):
    """Simulates a logged-in user session."""
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)

# -------------------- SETUP --------------------

def setup_ride(is_commuting=False):
    timestamp = datetime.now().strftime("%f")
    user = User(
        username=f"passenger_{timestamp}",
        email=f"p{timestamp}@example.com",
        password_hash=generate_password_hash("test")
    )
    driver = User(
        username=f"driver_{timestamp}",
        email=f"d{timestamp}@example.com",
        password_hash=generate_password_hash("test")
    )
    db.session.add_all([user, driver])
    db.session.commit()

    ride = publish_ride(
        driver_id=driver.id,
        driver_name=driver.username,
        from_location="A",
        to_location="B",
        category="commuting" if is_commuting else "one-time",
        date_time=datetime.now() + timedelta(days=1),
        available_seats_per_date='{"2025-12-01": 3}',
        price_per_seat=5.0,
        recurrence_dates="2025-12-01" if is_commuting else None,
        commute_times="08:00" if is_commuting else None
    )
    db.session.add(ride)
    db.session.commit()

    ride_date = datetime(2025, 12, 1).date()
    booking = book_ride(
        user_id=user.id,
        ride_id=ride.id,
        ride_date=ride_date,
        status="Booked",
        total_price=10.0,
        seats_selected=1,
        confirmation_email=user.email
    )
    db.session.add(booking)
    db.session.commit()

    return user, ride, booking

# -------------------- TEST CASES --------------------

# Test 1: User can successfully rate a one-time ride.
def test_valid_onetime_rating(client):
    """Test rating submission for a valid one-time ride."""
    user, ride, booking = setup_ride(is_commuting=False)
    login_as(client, user.id)
    data = {"ride_id": ride.id, "rating": 4}
    res = client.post("/api/submit_rating", json=data)
    assert res.status_code == 200
    assert b"Rating submitted successfully" in res.data

# Test 2: User can rate a commuting ride using ride_date
def test_valid_commuting_rating(client):
    """Test rating submission for a valid commuting ride."""
    user, ride, booking = setup_ride(is_commuting=True)
    login_as(client, user.id)
    data = {"ride_id": ride.id, "rating": 5, "ride_date": "2025-12-01"}
    res = client.post("/api/submit_rating", json=data)
    assert res.status_code == 200
    assert b"Rating submitted successfully" in res.data

# Test 3: User cannot rate the same ride more than once
def test_already_rated(client):
    """Test when the user has already rated the ride."""
    user, ride, booking = setup_ride()
    login_as(client, user.id)
    with app.app_context():
        db.session.add(RideRating(ride_id=ride.id, passenger_id=user.id, rating=4))
        db.session.commit()

    res = client.post("/api/submit_rating", json={"ride_id": ride.id, "rating": 5})
    assert res.status_code == 200
    assert b"already rated" in res.data

# Test 4: Submitting a rating without the required data (e.g., missing 'rating') fails
def test_rating_missing_data(client):
    """Test missing required data in rating submission."""
    user, ride, booking = setup_ride()
    login_as(client, user.id)
    res = client.post("/api/submit_rating", json={"ride_id": ride.id})  # Missing rating
    assert res.status_code == 400

# def test_rating_invalid_ride_id(client):
#     """Tests rating submission for a non-existent ride."""
#     user, _, _ = setup_ride()
#     login_as(client, user.id)
#     res = client.post("/api/submit_rating", json={"ride_id": 999999, "rating": 4})
#     assert res.status_code == 404 or res.status_code == 400

def test_rating_without_login(client):
    """Tests rating submission without being logged in."""
    _, ride, _ = setup_ride()
    res = client.post("/api/submit_rating", json={"ride_id": ride.id, "rating": 4})
    assert res.status_code in [302, 401]  # Redirect to login or unauthorized

def test_commuting_rating_missing_ride_date(client):
    """Tests that commuting ride rating fails if ride_date is missing."""
    user, ride, booking = setup_ride(is_commuting=True)
    login_as(client, user.id)
    res = client.post("/api/submit_rating", json={"ride_id": ride.id, "rating": 5})
    assert res.status_code == 400
    assert b"ride_date" in res.data or b"Missing" in res.data
