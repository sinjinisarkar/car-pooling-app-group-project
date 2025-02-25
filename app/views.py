import os
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from app.models import User, publish_ride, view_ride, book_ride
from werkzeug.utils import secure_filename
from datetime import datetime

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

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 400

    # Check if passwords match
    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    # Hash password and create new user
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

@app.route('/publish_ride', methods=['GET', 'POST'])
@login_required
def publish_ride_view():
    if request.method == 'POST':
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        date_time_str = request.form['date_time']
        available_seats = request.form['available_seats']
        price_per_seat = request.form['price_per_seat']
        category = request.form['category']

        try:
            date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M")
        except ValueError:
            return jsonify({"message": "Invalid date format"}), 400

        # Save to publish_ride
        new_ride = publish_ride(
            driver_id=current_user.id,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats=int(available_seats),
            price_per_seat=float(price_per_seat),
            category=category,
            is_available=True
        )
        db.session.add(new_ride)

        # Save to view_ride (ensure it's also stored here)
        new_view_ride = view_ride(
            driver_id=current_user.id,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats=int(available_seats),
            price_per_seat=float(price_per_seat),
            category=category
        )
        db.session.add(new_view_ride)

        db.session.commit()

        flash("Your ride has been published successfully!", "success")
        return redirect(url_for('view_journeys'))

    return render_template('publish_ride.html', user=current_user)

# viewing the ride by the user/passenger
@app.route('/view_journeys')
def view_journeys():
    journeys = view_ride.query.all()  # Fetch all available journeys
    return render_template('view_journeys.html', journeys=journeys, user=current_user)