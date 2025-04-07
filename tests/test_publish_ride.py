import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride

# Sample user data
DATA = {
    "username": "user123",
    "email": "user123@gmail.com",
    "password": "password123#",
    "confirm_password": "password123#"
}

@pytest.fixture
def client():
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        db.session.remove()
        db.drop_all()

@pytest.fixture
def register_and_login(client):
    """Register and login test driver."""
    client.post("/register", json={
        "username": "testdriver",
        "email": "driver@gmail.com",
        "password": "Password@123",
        "confirm_password": "Password@123"
    })
    client.post("/login", json={"email": "driver@gmail.com", "password": "Password@123"})

# -------------------------------
# ONE-TIME RIDE PIBLISHING TESTS
# -------------------------------

# Tests for missing fields in one-time ride
def test_onetime_missing_fields(client, register_and_login):
    base_data = {
        "from_location": "Leeds", "to_location": "York", "category": "one-time",
        "date_time": "2025-12-01 10:00", "available_seats": "2", "price_per_seat": "5.5"
    }
    for field in list(base_data.keys()):
        data = base_data.copy()
        del data[field]
        response = client.post("/publish_ride", data=data)
        assert response.status_code in (302, 400)

# Tests for invalid datatime format 
def test_onetime_invalid_datetime_format(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "one-time",
        "date_time": "bad-date-format", "available_seats": "2", "price_per_seat": "5.0"
    }
    response = client.post("/publish_ride", data=data)
    assert response.status_code in (302, 400)

# Tests for invalod seats and price amount
def test_onetime_invalid_seats_or_price(client, register_and_login):
    test_cases = [("0", "5.0"), ("-2", "5.0"), ("2", "0"), ("2", "-4.0")]
    for seats, price in test_cases:
        data = {
            "from_location": "Leeds", "to_location": "York", "category": "one-time",
            "date_time": "2025-12-01 10:00", "available_seats": seats, "price_per_seat": price
        }
        response = client.post("/publish_ride", data=data)
        assert response.status_code in (302, 400)

# Tests for if the one-time is successfuly published
def test_onetime_successful_publish(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "one-time",
        "date_time": "2025-12-01 10:00", "available_seats": "3", "price_per_seat": "7.0"
    }
    response = client.post("/publish_ride", data=data, follow_redirects=True)
    assert response.status_code == 200
    ride = publish_ride.query.first()
    assert ride is not None
    assert ride.driver_name == "testdriver"

# --------------------------------
# COMMUTING RIDE PUBLISHING TESTS
# --------------------------------

# Tets for missing fields in commuting rides
def test_commuting_missing_fields(client, register_and_login):
    base_data = {
        "from_location": "Leeds", "to_location": "York", "category": "commuting",
        "recurrence_dates": ["2025-12-01"], "commute_times": ["08:00"],
        "available_seats": "3", "price_per_seat": "5.0"
    }
    for field in list(base_data.keys()):
        data = base_data.copy()
        if field in ["recurrence_dates", "commute_times"]:
            data[field] = []
        else:
            del data[field]
        response = client.post("/publish_ride", data=data)
        assert response.status_code in (302, 400)

# Tests for invalid seat and price format
def test_commuting_invalid_seats_or_price(client, register_and_login):
    test_cases = [("0", "5.0"), ("-1", "5.0"), ("3", "0"), ("3", "-1.0")]
    for seats, price in test_cases:
        data = {
            "from_location": "Leeds", "to_location": "York", "category": "commuting",
            "recurrence_dates": ["2025-12-01"], "commute_times": ["08:00"],
            "available_seats": seats, "price_per_seat": price
        }
        response = client.post("/publish_ride", data=data)
        assert response.status_code in (302, 400)

# Tests for commuting ride with inconsistent date/time format 
def test_commuting_bad_date_format(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "commuting",
        "recurrence_dates": ["bad-date"], "commute_times": ["08:00"],
        "available_seats": "3", "price_per_seat": "5.0"
    }
    response = client.post("/publish_ride", data=data)
    assert response.status_code in (302, 400)

# Tests for successfuly publishing a commuting ride
def test_commuting_successful_publish(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "commuting",
        "recurrence_dates": ["2025-12-01"], "commute_times": ["08:00"],
        "available_seats": "4", "price_per_seat": "6.5"
    }
    response = client.post("/publish_ride", data=data, follow_redirects=True)
    assert response.status_code == 200
    ride = publish_ride.query.first()
    assert ride is not None
    assert ride.driver_name == "testdriver"

# -----------------------
# ADDITIONAL EDGE CASES
# -----------------------

# Tests for inavlid category choosen
def test_invalid_category(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "invalid",
        "date_time": "2025-12-01 10:00", "available_seats": "2", "price_per_seat": "5.0"
    }
    response = client.post("/publish_ride", data=data)
    assert response.status_code in (302, 400)

# Tests for unauthenticated user trying to publish a ride 
def test_publish_unauthenticated_user(client):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "one-time",
        "date_time": "2025-12-01 10:00", "available_seats": "2", "price_per_seat": "5.0"
    }
    response = client.post("/publish_ride", data=data, follow_redirects=True)
    assert response.status_code in (401, 403, 302, 405)

# Tests for excessively high seats or price (boundary testing)
def test_onetime_excessively_large_values(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "one-time",
        "date_time": "2025-12-01 10:00", "available_seats": "999", "price_per_seat": "999"
    }
    response = client.post("/publish_ride", data=data)
    assert response.status_code in (200, 302)

# Tests for missing price only
def test_missing_price_only(client, register_and_login):
    data = {
        "from_location": "Leeds", "to_location": "York", "category": "one-time",
        "date_time": "2025-12-01 10:00", "available_seats": "2"
    }
    response = client.post("/publish_ride", data=data)
    assert response.status_code in (302, 400)

# # Tests for available seats exceeding 8 (One-Time and Commuting) - tested in the front-end js files
# def test_seats_exceed_8(client, register_and_login):
#     test_cases = [
#         ("one-time", "2025-12-01 10:00"),
#         ("commuting", "2025-12-01 10:00")
#     ]
    
#     for category, date_time in test_cases:
#         data = {
#             "from_location": "Leeds", "to_location": "York", "category": category,
#             "date_time": date_time, "available_seats": "9", "price_per_seat": "5.0"
#         }
        
#         response = client.post("/publish_ride", data=data)
#         assert response.status_code == 200  # Assuming you get a success response
#         # Check if the appropriate message is displayed for exceeding seats
#         assert b"exceeds the maximum" in response.data.lower()

# # Tests for duplicate ride with the same date and time (One-Time and Commuting) - tested in the front-end js files
# def test_duplicate_ride_same_datetime(client, register_and_login):
#     test_cases = [
#         ("one-time", "2025-12-01 10:00"),
#         ("commuting", "2025-12-01 10:00")
#     ]
    
#     for category, date_time in test_cases:
#         data = {
#             "from_location": "Leeds", "to_location": "York", "category": category,
#             "date_time": date_time, "available_seats": "3", "price_per_seat": "5.0"
#         }
        
#         # First ride publish
#         response = client.post("/publish_ride", data=data)
#         assert response.status_code == 200
#         assert b"successfully published" in response.data.lower()
        
#         # Second ride with the same date and time
#         response = client.post("/publish_ride", data=data)
#         assert response.status_code in (302, 400)  # Adjust based on your expected response
#         assert b"ride already exists" in response.data.lower()  # Adjust the error message as needed