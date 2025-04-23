import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride, book_ride
from werkzeug.security import generate_password_hash

# ---------------------- FIXTURES ----------------------

@pytest.fixture
def client():
    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client
        db.session.remove()
        db.drop_all()

def login_as(client, user_id):
    with client.session_transaction() as sess:
        sess["_user_id"] = str(user_id)

def create_manager_user():
    timestamp = datetime.now().strftime("%f")
    manager = User(
        username=f"manager_{timestamp}",
        email=f"manager{timestamp}@example.com",
        password_hash=generate_password_hash("test"),
        is_manager=True  # ⚠️ Ensure this field exists in your User model
    )
    db.session.add(manager)
    db.session.commit()
    return manager

def create_normal_user_and_ride():
    timestamp = datetime.now().strftime("%f")
    user = User(
        username=f"user_{timestamp}",
        email=f"user{timestamp}@example.com",
        password_hash=generate_password_hash("test")
    )
    db.session.add(user)
    db.session.commit()

    ride = publish_ride(
        driver_id=user.id,
        driver_name=user.username,
        from_location="Origin",
        to_location="Destination",
        category="one-time",
        date_time=datetime.now() + timedelta(days=1),
        available_seats_per_date='{"2025-12-10": 2}',
        price_per_seat=15.0
    )
    db.session.add(ride)
    db.session.commit()
    return user, ride

# ---------------------- TEST CASES ----------------------

# Test 1: Ensures non-authenticated users cannot access the manager dashboard
def test_manager_dashboard_requires_login(client):
    res = client.get("/manager/dashboard")
    assert res.status_code in [302, 401]  
    assert "/login" in res.headers.get("Location", "")  

# Test 2: Ensures normal (non-manager) users are redirected or blocked
def test_non_manager_access_forbidden(client):
    user, _ = create_normal_user_and_ride()
    login_as(client, user.id)
    res = client.get("/manager/dashboard", follow_redirects=False)
    assert res.status_code == 302
    redirect_location = res.headers.get("Location", "")
    assert redirect_location in ["/", "/login", "/unauthorized"]

# Test 3: Validates that a manager can access the dashboard successfully
def test_manager_access_successful(client):
    manager = create_manager_user()
    login_as(client, manager.id)
    res = client.get("/manager/dashboard")
    assert res.status_code == 200
    assert (
        b"Manager Dashboard" in res.data or
        b"Total Users" in res.data or
        b"System Analytics" in res.data or
        b"All Published Rides" in res.data
    )

# Test 4: Manager should be able to see ride stats and earnings overview
def test_manager_can_see_rides(client):
    manager = create_manager_user()
    _, ride = create_normal_user_and_ride()
    login_as(client, manager.id)
    res = client.get("/manager/dashboard")
    assert res.status_code == 200
    assert (
        b"Weekly Platform Earnings" in res.data or
        b"Total Revenue" in res.data or
        b"Total Bookings" in res.data or
        b"Platform Overview" in res.data or
        b"Chart" in res.data  
    )

# Test 5: Manager can view the fee configuration
def test_manager_configure_fee_get(client):
    manager = create_manager_user()
    login_as(client, manager.id)
    res = client.get("/manager/configure_fee")
    assert res.status_code == 200
    assert b"Platform Fee" in res.data or b"fee" in res.data

# Test 6: Manager can successfully update the platform fee 
def test_manager_configure_fee_post_valid(client):
    manager = create_manager_user()
    login_as(client, manager.id)
    res = client.post("/manager/configure_fee", data={"fee": "0.01"})
    assert res.status_code == 200
    assert b"success" in res.data

# Test 7: Manager tries to enter an out-of-range fee (e.g. 0 > 1)
def test_manager_configure_fee_post_invalid_range(client):
    manager = create_manager_user()
    login_as(client, manager.id)
    res = client.post("/manager/configure_fee", data={"fee": "2.5"})
    assert res.status_code == 400
    assert b"Fee must be between 0 and 1" in res.data

# Test 8: Manager tries to enter an invalid (non-numeric) fee
def test_manager_configure_fee_post_invalid_format(client):
    manager = create_manager_user()
    login_as(client, manager.id)
    res = client.post("/manager/configure_fee", data={"fee": "abc"})
    assert res.status_code == 400
    assert b"Invalid input" in res.data

# Test 9: Check if the earnings chart/graph is presented on manager dashboard
def test_weekly_income_chart_present(client):
    manager = create_manager_user()
    login_as(client, manager.id)
    res = client.get("/manager/dashboard")
    assert res.status_code == 200
    assert b"chart" in res.data.lower() or b"earnings_chart_values" in res.data or b"<canvas" in res.data