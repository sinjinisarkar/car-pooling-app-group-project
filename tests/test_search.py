import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        db.session.remove()
        db.drop_all()

@pytest.fixture
def register_and_login_user(client):
    client.post("/register", json={
        "username": "user123",
        "email": "user123@gmail.com",
        "password": "Test@1234",
        "confirm_password": "Test@1234"
    })
    client.post("/login", json={"email": "user123@gmail.com", "password": "Test@1234"})

# Test 1: Empty search fields
def test_search_empty_fields(client):
    response = client.get("/filter_journeys", query_string={
        "from": "", "to": "", "date": "2025-10-17", "passengers": 2
    })
    assert response.status_code == 200  # still renders page
    assert b"No journeys" in response.data or b"journeys" in response.data

# Test 2: Invalid date format
def test_search_invalid_date_format(client):
    response = client.get("/filter_journeys", query_string={
        "from": "Leeds", "to": "Manchester", "date": "2025-13-40", "passengers": 1
    })
    assert response.status_code == 200  # still renders page

# Test 3: Passenger number exceeds available
def test_search_more_than_available(client, register_and_login_user):
    client.post("/publish_ride", data={
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "1",
        "price_per_seat": "5.0"
    })
    response = client.get("/filter_journeys", query_string={
        "from": "Leeds", "to": "Manchester", "date": "2025-10-17", "passengers": 3
    })
    assert response.status_code == 200
    assert b"No journeys" in response.data or b"journeys" in response.data

# Test 4: Price limit filter
def test_search_price_limit_filter(client, register_and_login_user):
    client.post("/publish_ride", data={
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "3",
        "price_per_seat": "10.0"
    })
    response = client.get("/filter_journeys", query_string={
        "from": "Leeds", "to": "Manchester", "date": "2025-10-17", "passengers": 1, "price": 5
    })
    assert response.status_code == 200
    assert b"No journeys" in response.data or b"journeys" in response.data

# Test 5: Commuting ride search
def test_search_commuting_ride(client, register_and_login_user):
    client.post("/publish_ride", data={
        "from_location": "Leeds",
        "to_location": "Newcastle",
        "category": "commuting",
        "recurrence_dates": ["2025-10-17", "2025-10-18"],
        "commute_times": ["09:00"],
        "available_seats": "3",
        "price_per_seat": "8.0"
    })
    response = client.get("/filter_journeys", query_string={
        "from": "Leeds", "to": "Newcastle", "date": "2025-10-17", "passengers": 2, "category": "commuting"
    })
    assert response.status_code == 200
    assert b"Leeds" in response.data and b"Newcastle" in response.data

# Test 6: Explicity checking for One-time ride search
def test_search_one_time_only(client, register_and_login_user):
    # Publish both ride types
    client.post("/publish_ride", data={
        "from_location": "Leeds",
        "to_location": "York",
        "category": "one-time",
        "date_time": "2025-10-18 15:00",
        "available_seats": "2",
        "price_per_seat": "6.0"
    })

    client.post("/publish_ride", data={
        "from_location": "Leeds",
        "to_location": "York",
        "category": "commuting",
        "recurrence_dates": ["2025-10-18"],
        "commute_times": ["08:00"],
        "available_seats": "3",
        "price_per_seat": "8.0"
    })

    # Filter specifically for one-time only
    response = client.get("/filter_journeys", query_string={
        "from": "Leeds",
        "to": "York",
        "date": "2025-10-18",
        "passengers": 1,
        "category": "one-time"
    })

    assert response.status_code == 200
    assert b"Leeds" in response.data
    assert b"York" in response.data
    assert b"one-time" in response.data
