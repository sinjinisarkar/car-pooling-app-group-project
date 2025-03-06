import os
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from app.models import User, publish_ride, view_ride, book_ride, SavedRide
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

# Publishing a ride by the driver
@app.route('/publish_ride', methods=['GET', 'POST'])
@login_required
def publish_ride_view():
    if request.method == 'POST':
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        category = request.form['category']
        driver_name = current_user.username  # Store driver name

        # Handle date/time for one-time rides & recurrence days for commuting rides
        if category == "one-time":
            date_time_str = request.form['date_time']
            try:
                date_time = datetime.strptime(date_time_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                flash("Invalid date format", "danger")
                return redirect(url_for('publish_ride_view'))
            recurrence_days = None  # No recurrence days for one-time rides
        else:  # If it's a commuting ride
            date_time = None  # ✅ Ensure date_time is NULL for commuting rides
            recurrence_days = request.form.getlist('recurrence_days')  # ✅ Store selected checkboxes
            recurrence_days = ",".join(recurrence_days) if recurrence_days else None  # Convert list to string

        available_seats = request.form['available_seats']
        price_per_seat = request.form['price_per_seat']

        # Save to publish_ride
        new_ride = publish_ride(
            driver_id=current_user.id,
            driver_name=driver_name,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,  # Will be None for commuting rides
            available_seats=int(available_seats),
            price_per_seat=float(price_per_seat),
            category=category,
            recurrence_days=recurrence_days,  # Store recurrence days
            is_available=True
        )
        db.session.add(new_ride)

        # Save to view_ride (ensure it's also stored here)
        new_view_ride = view_ride(
            driver_id=current_user.id,
            driver_name=driver_name,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,  # ✅ Ensure date_time is NULL for commuting rides
            available_seats=int(available_seats),
            price_per_seat=float(price_per_seat),
            category=category,
            recurrence_days=recurrence_days  # ✅ Ensure commuting days are saved
        )
        db.session.add(new_view_ride)

        db.session.commit()

        flash("Your ride has been published successfully!", "success")
        return redirect(url_for('view_journeys'))

    return render_template('publish_ride.html', user=current_user)


@app.route('/view_journeys')
def view_journeys():
    # Get all rides that still have available seats
    journeys = view_ride.query.filter(view_ride.available_seats > 0).all()

    # If a user is logged in, hide their booked one-time rides
    if current_user.is_authenticated:
        booked_journey_ids = [booking.ride_id for booking in book_ride.query.filter_by(user_id=current_user.id).all()]
        journeys = [journey for journey in journeys if not (journey.id in booked_journey_ids and journey.category == 'one-time')]

    return render_template('view_journeys.html', journeys=journeys, user=current_user if current_user.is_authenticated else None)

# Book a journey by the user/passenger
@app.route('/book_journey/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def book_journey(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    view_ride_entry = view_ride.query.filter_by(id=ride.id).first()

    if request.method == 'POST':
        num_seats = int(request.form['seats'])
        confirmation_email = request.form['email']

        # Ensure enough seats are available
        if num_seats > ride.available_seats:
            flash("Not enough available seats", "danger")
            return redirect(url_for('view_journeys'))

        # Calculate total price
        total_price = num_seats * ride.price_per_seat

        # If commuting, get the selected days
        booking_days = request.form.getlist('booking_days') if ride.category == "commuting" else []

        # If it's a one-time ride, assign the actual ride date
        if ride.category == "one-time":
            ride_date = ride.date_time
        else:
            ride_date = None  # ✅ For commuting rides, we don't set a ride date

        # Create booking(s)
        if ride.category == "one-time":
            new_booking = book_ride(
                user_id=current_user.id, 
                ride_id=ride.id, 
                status="Booked", 
                total_price=total_price, 
                seats_selected=num_seats, 
                confirmation_email=confirmation_email,
                ride_date=ride_date  # ✅ Only set this for one-time rides
            )
            db.session.add(new_booking)
            ride.available_seats -= num_seats  
            if view_ride_entry:
                view_ride_entry.available_seats -= num_seats  

        else:  # Commuting Ride
            for day in booking_days:
                new_booking = book_ride(
                    user_id=current_user.id,
                    ride_id=ride.id,
                    status="Booked",
                    total_price=total_price,  
                    seats_selected=num_seats,
                    confirmation_email=confirmation_email,
                    ride_date=None  # ✅ No fixed date for commuting rides
                )
                db.session.add(new_booking)

            ride.available_seats -= num_seats  
            if view_ride_entry:
                view_ride_entry.available_seats -= num_seats  

        db.session.commit()

        # Hide ride if all seats are booked
        if ride.available_seats <= 0 and view_ride_entry:
            db.session.delete(view_ride_entry)
            db.session.commit()

        flash("Ride booked successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('book_journeys.html', ride=ride, user=current_user)

# Cancelling a booking by user/passenger once booked on their user dashboard page
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = book_ride.query.get_or_404(booking_id)

    # Ensure the current user is the one who booked the ride
    if booking.user_id != current_user.id:
        flash("You cannot cancel someone else's booking.", "danger")
        return redirect(url_for('dashboard'))

    # Increase the available seats in the ride
    ride = publish_ride.query.get_or_404(booking.ride_id)
    ride.available_seats += booking.seats
    
    # Delete the booking from the book_ride table
    db.session.delete(booking)
    db.session.commit()

    flash("Booking canceled successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Query the booked rides for the current user
    booked_rides = book_ride.query.filter_by(user_id=current_user.id).all()
    
    # Pass both the booked rides and their details to the template
    return render_template('dashboard.html', booked_rides=booked_rides)

@app.context_processor
def inject_user():
    return dict(user=current_user)