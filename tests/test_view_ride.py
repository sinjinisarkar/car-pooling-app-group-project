import sys
import os
import pytest
import json
from datetime import datetime
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from app.models import User, publish_ride, book_ride
from flask import session

# ---------------------- FIXTURES ----------------------

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
    client.post("/register", json=DATA)
    login_data = {"email": DATA["email"], "password": DATA["password"]}
    client.post("/login", json=login_data)

# -------------------- TEST CASES --------------------

# Test 1: Verifies for if page Loads (Unauthenticated)
def test_view_journeys_loading(client):
    response = client.get("/view_journeys")
    assert response.status_code == 200
    assert b"Journeys" in response.data

# Test 2: Verifies for if no rides are published
def test_view_journeys_empty(client):
    response = client.get("/view_journeys")
    assert response.status_code == 200
    assert b"No journeys available" in response.data

# Test 3: Verifies for if rides are displayed after publishing
def test_view_journeys_available_rides(client, register_and_login):
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

    response = client.get("/view_journeys")
    data = response.data.decode("utf-8")
    assert response.status_code == 200
    assert "Leeds" in data and "Manchester" in data and "Newcastle" in data

# Test 4: Verifies for if published rides still show after logout
def test_view_journeys_log_out_1(client, register_and_login):
    one_time_ride = {
        "from_location": "Leeds",
        "to_location": "Manchester",
        "category": "one-time",
        "date_time": "2025-10-17 12:30",
        "available_seats": "2",
        "price_per_seat": "5.0"
    }
    client.post("/publish_ride", data=one_time_ride)
    client.post("/logout")

    response = client.get("/view_journeys")
    assert response.status_code == 200
    assert b"Leeds" in response.data and b"Manchester" in response.data

# Test 5: Verifies for if "no journeys" message appears for unauthenticated users with no rides
def test_view_journeys_log_out_2(client, register_and_login):
    client.post("/logout")
    response = client.get("/view_journeys")
    assert response.status_code == 200
    assert b"No journeys available" in response.data

# Test 6: Verifies for seat_tracking with corrupted JSON
def test_view_journeys_seat_tracking_parsed(client, register_and_login):
    with app.app_context():
        ride = publish_ride(
            driver_id=1,
            driver_name="user123",
            from_location="Leeds",
            to_location="York",
            date_time=datetime.strptime("2025-10-17 12:30", "%Y-%m-%d %H:%M"),
            available_seats_per_date='invalid_json',
            price_per_seat=5.0,
            category="one-time",
            is_available=True
        )
        db.session.add(ride)
        db.session.commit()

    response = client.get("/view_journeys")
    assert response.status_code == 200  # Should not crash even with bad JSON

# Test 7: Verifies for user_has_booked flag (rides booked by logged-in user)
def test_view_journeys_user_has_booked_flag(client, register_and_login):
    with app.app_context():
        ride = publish_ride(
            driver_id=1,
            driver_name="user123",
            from_location="Leeds",
            to_location="York",
            date_time=datetime.strptime("2025-10-17 12:30", "%Y-%m-%d %H:%M"),
            available_seats_per_date=json.dumps({"2025-10-17": 2}),
            price_per_seat=5.0,
            category="one-time",
            is_available=True
        )
        db.session.add(ride)
        db.session.commit()

        booking = book_ride(
            user_id=1,
            ride_id=ride.id,
            status="Booked",
            total_price=10.0,
            seats_selected=1,
            confirmation_email=DATA["email"],
            ride_date=datetime.strptime("2025-10-17", "%Y-%m-%d")
        )
        db.session.add(booking)
        db.session.commit()

    response = client.get("/view_journeys")
    assert response.status_code == 200
    assert b"Leeds" in response.data and b"York" in response.data

# Test 8: Verifies for ride visibility when seats become zero - ride is hidden(one-time)
def test_view_journeys_hide_fully_booked_ride(client, register_and_login):
    one_time_data = {
        "from_location": "Leeds",
        "to_location": "York",
        "category": "one-time",
        "date_time": "2025-12-01 10:00",
        "available_seats": "1",
        "price_per_seat": "8"
    }
    client.post("/publish_ride", data=one_time_data)

    # Fully book the ride manually
    ride = publish_ride.query.filter_by(category="one-time").first()
    ride.available_seats_per_date = json.dumps({"2025-12-01": 0})
    db.session.commit()
    db.session.expire_all()

    response = client.get("/view_journeys")
    html = response.data.decode("utf-8").lower()

    assert "from: leeds" not in html and "to: york" not in html

# Test 9: Verifies for ride visibility when seats become zero - ride is hidden(commuting)
def test_view_journeys_hide_fully_booked_commuting(client, register_and_login):
    commuting_data = {
        "from_location": "Leeds",
        "to_location": "Sheffield",
        "category": "commuting",
        "recurrence_dates": ["2025-12-01", "2025-12-02"],
        "commute_times": ["08:00", "09:00"],
        "available_seats": "2",
        "price_per_seat": "7"
    }
    client.post("/publish_ride", data=commuting_data)

    ride = publish_ride.query.filter_by(category="commuting").first()
    ride.available_seats_per_date = json.dumps({
        "2025-12-01": 0,
        "2025-12-02": 0
    })
    db.session.commit()
    db.session.expire_all()

    response = client.get("/view_journeys")
    html = response.data.decode("utf-8").lower()

    assert "from: leeds" not in html and "to: sheffield" not in html