from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import app, db
from app.models import User

@app.route('/')
def home():
    return render_template('index.html', user=current_user)  # Send user details to frontend

if __name__ == '__main__':
    app.run(debug=True)

#  User Registration (Signup)
@app.route("/register", methods=["POST"])
def register():
    data = request.json  # Get JSON data from frontend
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")

    # ❌ Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 400

    # ❌ Check if passwords match
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # ✅ Hash password and create new user
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    new_user = User(username=username, email=email, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

# User Login 
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid email or password"}), 401

    login_user(user)
    return jsonify({"message": "Login successful"}), 200

# User Logout
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully!"}), 200


# Load User for Flask-Login
from app import login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))