import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User, publish_ride, book_ride, Payment
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

def create_user_and_bookings():
    timestamp = datetime.now().strftime("%f")
    user = User(
        username=f"user_{timestamp}",
        email=f"user{timestamp}@example.com",
        password_hash=generate_password_hash("test")
    )
    db.session.add(user)
    db.session.commit()
    return user

def create_booked_ride(user):
    ride = publish_ride(
        driver_id=user.id,
        driver_name=user.username,
        from_location="Start",
        to_location="End",
        category="one-time",
        date_time=datetime.now() + timedelta(days=1),
        available_seats_per_date='{"2025-12-10": 2}',
        price_per_seat=10.0
    )
    db.session.add(ride)
    db.session.commit()

    booking = book_ride(
        user_id=user.id,
        ride_id=ride.id,
        ride_date=datetime(2025, 12, 10).date(),
        status="Booked",
        total_price=10.0,
        seats_selected=1,
        confirmation_email=user.email
    )
    db.session.add(booking)
    db.session.commit()
    return ride

# ---------------------- TEST CASES ----------------------

# Test 1: Verifies that an unauthenticated user is redirected to the login page when trying to access the dashboard
def test_user_dashboard_redirects_if_not_logged_in(client):
    res = client.get("/dashboard")
    assert res.status_code == 302  
    assert "/login" in res.headers.get("Location", "")  

# Test 2: Verifies that the dashboard loads correctly when the user is logged in
def test_user_dashboard_shows_dashboard_page(client):
    user = create_user_and_bookings()  
    login_as(client, user.id)  
    res = client.get("/dashboard")
    assert res.status_code == 200  
    assert (
        b"Published Rides" in res.data or
        b"Total Earnings" in res.data or
        b"Your Bookings" in res.data or
        b"Upcoming Journeys" in res.data
    )

# Test 3: Verifies that the dashboard still renders even if the user has no rides
def test_user_dashboard_shows_no_rides(client):
    user = create_user_and_bookings()  
    login_as(client, user.id) 
    res = client.get("/dashboard")
    assert res.status_code == 200  
    assert b"Published Rides" in res.data or b"Total Earnings" in res.data

# Test 4: Verifies that a one-time booked ride is displayed
def test_user_dashboard_shows_booked_ride(client):
    user = create_user_and_bookings()  
    create_booked_ride(user)  
    login_as(client, user.id)  
    res = client.get("/dashboard")
    assert res.status_code == 200 
    assert b"From" in res.data or b"Start" in res.data or b"Booked" in res.data

# Test 5: Verifies that a commuting booked ride is displayed on the dashboard
def test_user_dashboard_shows_commuting_ride(client):
    user = create_user_and_bookings()  
    # Create a commuting ride
    ride = publish_ride(
        driver_id=user.id,
        driver_name=user.username,
        from_location="C1",
        to_location="C2",
        category="commuting",
        date_time=None,
        recurrence_dates="2025-12-12",
        commute_times="09:00",
        available_seats_per_date='{"2025-12-12": 2}',
        price_per_seat=8.0
    )
    db.session.add(ride)
    db.session.commit()

    booking = book_ride(
        user_id=user.id,
        ride_id=ride.id,
        ride_date=datetime(2025, 12, 12).date(),
        status="Booked",
        total_price=8.0,
        seats_selected=1,
        confirmation_email=user.email
    )
    db.session.add(booking)
    db.session.commit()

    login_as(client, user.id)  
    res = client.get("/dashboard")
    assert res.status_code == 200  
    assert b"C1" in res.data or b"C2" in res.data or b"commuting" in res.data

# Test 6: Verifies that a driver can see their published rides on the dashboard
def test_driver_sees_published_ride(client):
    user = create_user_and_bookings()  
    ride = publish_ride(
        driver_id=user.id,
        driver_name=user.username,
        from_location="DriverFrom",
        to_location="DriverTo",
        category="one-time",
        date_time=datetime.now() + timedelta(days=2),
        available_seats_per_date='{"2025-12-15": 3}',
        price_per_seat=12.0
    )
    db.session.add(ride)
    db.session.commit()

    login_as(client, user.id)  
    res = client.get("/dashboard")
    assert res.status_code == 200  
    assert b"DriverFrom" in res.data or b"DriverTo" in res.data or b"Published Rides" in res.data

# Test 7: Verifies that a driver can see their total earnings on the dashboard presented in a chart/graph
def test_driver_income_summary_shown(client):
    user = create_user_and_bookings() 

    ride = publish_ride(
        driver_id=user.id,
        driver_name=user.username,
        from_location="IncomeFrom",
        to_location="IncomeTo",
        category="one-time",
        date_time=datetime.now(),
        available_seats_per_date='{"2025-12-01": 2}',
        price_per_seat=10.0
    )
    db.session.add(ride)
    db.session.commit()

    booking = book_ride(
        user_id=user.id, 
        ride_id=ride.id,
        ride_date=datetime(2025, 12, 1).date(),
        status="Booked",
        total_price=20.0,
        seats_selected=2,
        confirmation_email=user.email
    )
    db.session.add(booking)
    db.session.commit()

    payment = Payment(
        user_id=user.id,
        ride_id=ride.id,
        book_ride_id=booking.id, 
        amount=20.0,
        status="Success",
        timestamp=datetime.now(),
        platform_fee=0.005
    )
    db.session.add(payment)
    db.session.commit()

    login_as(client, user.id) 
    res = client.get("/dashboard")
    assert res.status_code == 200 
    assert b"Total Earnings" in res.data or b"Weekly Income" in res.data