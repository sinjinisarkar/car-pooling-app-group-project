
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User
from flask import session

# Sample data for user registration and login
DATA = {
    "username": "user123",
    "email": "user123@gmail.com",
    "password": "password123#",
    "confirm_password": "password123#"
}

@pytest.fixture
def client():
    """Fixture to create a test client for Flask app."""
    with app.test_client() as client:
        with app.app_context():
            db.create_all()  # Create the tables in the database
        yield client
        db.session.remove()
        db.drop_all()  # Clean up the database after tests

# ========================
# TEST CASES FOR SEARCHING RIDES
# ========================

# Test 1: Valid Search (Matching journey)
def test_search_journeys_valid(client):
    """Tests search functionality with valid data and matching results."""
    # Register and login user
    client.post("/register", json=DATA)
    login_data = {"email": "user123@gmail.com", "password": "password123#"}
    client.post("/login", json=login_data)

    # Publish one-time and commuting rides
    one_time_ride = {
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "2",
        "price_per_seat": "5.0"
    }
    commuting_ride = {
        "from_location": "Leeds",
        "to_location": "Newcastle",
        "category": "commuting",
        "recurrence_dates": ["2025-10-11", "2025-10-12"],
        "commute_times": ["12:00", "10:00"],
        "available_seats": "3",
        "price_per_seat": "10"
    }
    client.post("/publish_ride", data=one_time_ride)
    client.post("/publish_ride", data=commuting_ride)

    # Search query
    search_data = {
        'from': 'Leeds',
        'to': 'Manchester',
        'date': '2025-10-17',
        'passengers': 2
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 200
    data = response.get_json()
    journey = data['journeys'][0]
    assert journey['from_location'] == 'Leeds'
    assert journey['to_location'] == 'Manchester'
    assert journey['date_time'] == '2025-10-17 12:30'
    assert journey['price_per_seat'] == 5.0
    assert journey['seat_tracking'] is not None
    assert journey['category'] == 'one-time'

# Test 2: Empty Search Fields
def test_search_journeys_empty(client):
    """Tests the search functionality with empty fields."""
    search_data = {
        'from': '',
        'to': '',
        'date': '2025-10-17',
        'passengers': 2
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 400
    assert b"fill in all search fields" in response.data.lower()

# Test 3: Invalid Search (No Matches Found)
def test_search_journeys_invalid(client):
    """Tests search functionality with no matching results."""
    search_data = {
        'from': 'Leeds',
        'to': 'Manchester',
        'date': '2025-10-17',
        'passengers': 2
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 200
    data = response.get_json()
    assert data['journeys'] == []  # No journeys should be returned

# Test 4: Default Passengers Field (When passengers is not specified)
def test_search_journeys_passengers(client):
    """Tests search with default passengers value of 1."""
    client.post("/register", json=DATA)
    login_data = {"email": "user123@gmail.com", "password": "password123#"}
    client.post("/login", json=login_data)

    one_time_ride = {
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "1",
        "price_per_seat": "5.0"
    }
    client.post("/publish_ride", data=one_time_ride)

    search_data = {
        'from': 'Leeds',
        'to': 'Manchester',
        'date': '2025-10-17',
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 200
    data = response.get_json()
    journey = data['journeys'][0]
    assert journey['seats_available'] >= 1  # Should default to 1 if passengers is not specified

# Test 5: More Passengers Than Available Seats
def test_search_journeys_more_passengers(client):
    """Tests search when requested passengers exceed available seats."""
    client.post("/register", json=DATA)
    login_data = {"email": "user123@gmail.com", "password": "password123#"}
    client.post("/login", json=login_data)

    one_time_ride = {
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "1",
        "price_per_seat": "5.0"
    }
    client.post("/publish_ride", data=one_time_ride)

    search_data = {
        'from': 'Leeds',
        'to': 'Manchester',
        'date': '2025-10-17',
        'passengers': '3'
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 200
    data = response.get_json()
    assert data['journeys'] == []  # No journeys should be returned as seats are insufficient

# Test 6: Invalid Date Format
def test_search_journeys_invalid_date(client):
    """Tests search with an invalid date format."""
    search_data = {
        'from': 'Leeds',
        'to': 'Manchester',
        'date': 'invalid-date',
        'passengers': 2
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 400
    assert b"Invalid date format" in response.data.lower()

# Test 7: Search by Price Limit
def test_search_journeys_price_limit(client):
    """Tests the search functionality with a price limit filter."""
    client.post("/register", json=DATA)
    login_data = {"email": "user123@gmail.com", "password": "password123#"}
    client.post("/login", json=login_data)

    one_time_ride = {
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "3",
        "price_per_seat": "10.0"
    }
    client.post("/publish_ride", data=one_time_ride)

    search_data = {
        'from': 'Leeds',
        'to': 'Manchester',
        'date': '2025-10-17',
        'price': '5.0',
        'passengers': 2
    }
    response = client.get('/filter_journeys', query_string=search_data)

    assert response.status_code == 200
    data = response.get_json()
    assert len(data['journeys']) == 0  # No rides should be returned as the price exceeds the limit

# ========================
# END OF TEST CASES
# ========================
