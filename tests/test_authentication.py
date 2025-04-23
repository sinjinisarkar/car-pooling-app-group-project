import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app, db
from app.models import User

# ---------------------- FIXTURES ----------------------

# Common test data
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

# -------------------- TEST CASES --------------------

# -------------------------------
# REGISTER TESTS
# -------------------------------

# Tests for user registration
def test_register(client):
    """Test successful user registration."""
    response = client.post("/register", json=DATA)
    assert response.status_code == 201
    assert b"success" in response.data.lower() 

# Tests for user creation in database
def test_user_creation_in_database(client):
    """Test successful user creation in the database."""
    client.post("/register", json=DATA)
    with app.app_context():
        user = User.query.filter_by(email="user123@gmail.com").first()
        assert user is not None

# Tests for missing fields
def test_registration_missing_fields(client):
    """Test registration with missing fields."""
    data = {
        "user": "",  # Invalid key, should be "username"
        "email": "user123@gmail.com",
        "password": "password123#",
        "confirm_password": "password123#"
    }
    response = client.post("/register", json=data)
    assert response.status_code == 400
    assert b"user" in response.data.lower()

# Tests for existing username
def test_register_existing_username(client):
    """Test registration failure with an already existing username."""
    # Register user 1
    user1 = {
        "username": "uniqueuser",
        "email": "userA@gmail.com",
        "password": "Password123#",
        "confirm_password": "Password123#"
    }
    client.post("/register", json=user1)

    # Try registering with same username
    user2 = {
        "username": "uniqueuser",  # same username
        "email": "userB@gmail.com",  # different email
        "password": "Password123#",
        "confirm_password": "Password123#"
    }
    response = client.post("/register", json=user2)
    assert response.status_code == 400
    assert b"username already" in response.data.lower()

# Tests for invalid email format
def test_register_invalid_email(client):
    """Test registration with an invalid email format."""
    data = {
        "username": "user123",
        "email": "user123",  # Invalid format
        "password": "Password123#",
        "confirm_password": "Password123#"
    }
    response = client.post("/register", json=data)
    assert response.status_code == 400
    assert b"invalid" in response.data.lower()

# Tests for existing email
def test_register_existing_email(client):
    """Test registration failure with an already existing email."""
    client.post("/register", json=DATA)
    data_new = {
        "username": "user456",
        "email": "user123@gmail.com",
        "password": "Password123#",
        "confirm_password": "Password123#"
    }
    response = client.post("/register", json=data_new)
    assert response.status_code == 400
    assert b"email already" in response.data.lower()

@pytest.mark.parametrize("password, reason", [
    ("P", b"8 characters"),
    ("Password", b"special character")
])

# Tests for weak password while registering
def test_weak_passwords(client, password, reason):
    """Test registration failure on weak passwords."""
    data = {
        "username": "user123",
        "email": "user123@gmail.com",
        "password": password,
        "confirm_password": password
    }
    response = client.post("/register", json=data)
    assert response.status_code == 400
    assert reason in response.data.lower()

# Tests for email case insensitivity
def test_register_case_insensitive_email(client):
    """Test registration with capital letters in email."""
    new_data = {
        "username": "user123", 
        "email": "USER123@gmail.com",
        "password": "password123#",
        "confirm_password": "password123#"
    }
    response = client.post("/register", json=new_data)
    assert response.status_code == 201
    assert b"success" in response.data.lower()

# Tests for if password and confirm password are same
def test_password_mismatch(client):
    """Test registration failure when password and confirm password do not match."""
    data = {
        "username": "user123",
        "email": "user123@gmail.com",
        "password": "password123#",
        "confirm_password": "password1234#"
    }
    response = client.post("/register", json=data)
    assert response.status_code == 400
    assert b"passwords do not match" in response.data.lower()

# -------------------------------
# LOGIN TESTS
# -------------------------------

# Tests for user log in 
def test_user_login(client):
    """Test successful user login."""
    client.post("/register", json=DATA)
    login_data = {
        "email": "user123@gmail.com", 
        "password": "password123#"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 200
    assert b"login successful" in response.data.lower()

# Tests for incorrect password
def test_login_wrong_password(client):
    """Test login with invalid password."""
    client.post("/register", json=DATA)
    login_data = {
        "email": "user123@gmail.com", 
        "password": "incorrect"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 401
    assert b"invalid email or password" in response.data.lower()

# Tests for case insensitivity for email
def test_login_case_insensitive_email(client):
    """Test login with capital letters in email."""
    client.post("/register", json=DATA)
    login_data = {
        "email": "USER123@gmail.com", 
        "password": "password123#"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 200
    assert b"login successful" in response.data.lower()

# Tests for not registered email
def test_not_registered_email(client):
    """Test login with unregistered email."""
    client.post("/register", json=DATA)
    login_data = {
        "email": "user_test@gmail.com", 
        "password": "password123#"
    }
    response = client.post("/login", json=login_data)
    assert response.status_code == 401
    assert b"invalid email" in response.data.lower()

# Tests for user log out
def test_user_log_out(client):
    """Test successful user logout."""
    client.post("/register", json=DATA)
    login_data = {
        "email": "user123@gmail.com", 
        "password": "password123#"
    }
    client.post("/login", json=login_data)
    response = client.post("/logout") 
    assert response.status_code == 200  
    assert b"logged out successfully" in response.data.lower()

# -------------------------------
# FORGOT PASSWORD TESTS
# -------------------------------

# Tests for password reset
def test_password_reset(client):
    """Test password reset request with valid email."""
    client.post("/register", json=DATA)
    response = client.post("/forgot-password", json={"email": "user123@gmail.com"})
    assert response.status_code == 200
    assert b"password reset" in response.data.lower()

# Tests for password reset for non-registered users
def test_password_reset_invalid(client):
    """Test password reset request with unregistered email."""
    response = client.post("/forgot-password", json={"email": "user123@gmail.com"})
    assert response.status_code == 404
    assert b"no account" in response.data.lower()