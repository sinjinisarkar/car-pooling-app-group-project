import os, json, sys
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from app.models import User, publish_ride, view_ride, book_ride, SavedRide
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy.sql import func


# Route for home page
@app.route('/')
def home():
    return render_template('index.html', user=current_user)  
if __name__ == '__main__':
    app.run(debug=True)


# Route for User Registration (Signup)
@app.route("/register", methods=["POST"])
def register():
    data = request.json  
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


# Route for User Login 
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


# Route for User Logout
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully!"}), 200 


# Route to Load User for Flask-Login
from app import login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Route for publish ride by the driver
@app.route('/publish_ride', methods=['GET', 'POST'])
@login_required
def publish_ride_view():
    if request.method == 'POST':
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        category = request.form['category']
        driver_name = current_user.username
        price_per_seat = float(request.form['price_per_seat'])
        # Initialize variables
        date_time = None
        recurrence_dates = None
        commute_times = None
        available_seats_per_date = None
        available_seats = None  
        if category == "one-time":
            date_time_str = request.form.get('date_time')
            available_seats = int(request.form.get('available_seats', 0))  
            if not date_time_str:
                flash("Please select a valid Date & Time for one-time rides.", "danger")
                return redirect(url_for('publish_ride_view'))
            try:
                date_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                flash("Invalid Date & Time format!", "danger")
                return redirect(url_for('publish_ride_view'))
            available_seats_per_date = json.dumps({date_time.strftime("%Y-%m-%d"): available_seats})

        else:  # **Commuting Ride (Multiple Recurring Days & Times)**
            recurrence_dates_list = request.form.getlist('recurrence_dates')
            commute_times_list = request.form.getlist('commute_times')
            available_seats = int(request.form.get('available_seats', 0))  
            if not recurrence_dates_list or not commute_times_list:
                flash("Please select at least one commute day and time.", "danger")
                return redirect(url_for('publish_ride_view'))
            recurrence_dates = ",".join(recurrence_dates_list)
            commute_times = ",".join(commute_times_list)
            # Split the recurrence_dates string properly
            recurrence_dates_list = [date.strip() for date in recurrence_dates.split(",")]
            # Ensure each date is stored as a separate key
            seats_dict = {date: available_seats for date in recurrence_dates_list}
            available_seats_per_date = json.dumps(seats_dict)  
        # Save the Ride
        new_ride = publish_ride(
            driver_id=current_user.id,
            driver_name=driver_name,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats_per_date=available_seats_per_date,  # Only for commuting rides
            price_per_seat=price_per_seat,
            category=category,
            recurrence_dates=recurrence_dates,
            commute_times=commute_times,
            is_available=True
        )
        db.session.add(new_ride)
        new_view_ride = view_ride(
            driver_id=current_user.id,
            driver_name=driver_name,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats_per_date=available_seats_per_date,  # Only for commuting rides
            price_per_seat=price_per_seat,
            category=category,
            recurrence_dates=recurrence_dates,
            commute_times=commute_times
        )
        db.session.add(new_view_ride)
        db.session.commit()
        flash("Your ride has been published successfully!", "success")
        return redirect(url_for('view_journeys'))
    return render_template('publish_ride.html', user=current_user)


# Route for viewing ride by the passenger/user
@app.route('/view_journeys')
def view_journeys():
    db.session.commit()  
    db.session.expire_all()  
    # Get all rides that still have available seats on any date
    journeys = view_ride.query.all()
    booked_journey_ids = set()
    if current_user.is_authenticated:
        booked_journey_ids = {booking.ride_id for booking in book_ride.query.filter_by(user_id=current_user.id).all()}
    for journey in journeys:
        try:
            journey.seat_tracking = json.loads(journey.available_seats_per_date) if journey.available_seats_per_date else {}
        except (json.JSONDecodeError, TypeError):
            journey.seat_tracking = {}  # Prevent errors if data is invalid
        journey.user_has_booked = journey.id in booked_journey_ids
    return render_template('view_journeys.html', journeys=journeys, user=current_user)


# Route for booking a joureny by teh user/passenger
@app.route('/book_journey/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def book_journey(ride_id):
    ride = view_ride.query.filter_by(id=ride_id).first()
    if not ride:
        ride = publish_ride.query.get_or_404(ride_id)
    
    # Load available seats data
    seat_tracking = {}
    if ride.available_seats_per_date:
        try:
            seat_tracking = json.loads(ride.available_seats_per_date)
        except json.JSONDecodeError:
            seat_tracking = {}
    
    available_dates = []
    if ride.category == "commuting" and ride.recurrence_dates:
        available_dates = [date.strip() for date in ride.recurrence_dates.split(",")]
    
    selected_date = request.args.get("selected_date") or (available_dates[0] if available_dates else "")
    current_available_seats = seat_tracking.get(selected_date, 0) if selected_date else 0
    
    if request.method == 'POST':
        num_seats = request.form.get('seats')
        confirmation_email = request.form.get('email')
        if not num_seats:
            flash("Please enter the number of seats.", "danger")
            return redirect(url_for('book_journey', ride_id=ride_id))
        
        try:
            num_seats = int(num_seats)
        except ValueError:
            flash("Invalid seat number!", "danger")
            return redirect(url_for('book_journey', ride_id=ride_id))
        
        total_price = num_seats * ride.price_per_seat
        
        if ride.category == "one-time":
            ride_date = ride.date_time.strftime("%Y-%m-%d")
            if num_seats > seat_tracking.get(ride_date, 0):
                flash(f"Not enough seats available! Only {seat_tracking.get(ride_date, 0)} left.", "danger")
                return redirect(url_for('book_journey', ride_id=ride_id))
            
            seat_tracking[ride_date] = max(0, seat_tracking.get(ride_date, 0) - num_seats)
        
        else:
            selected_dates = request.form.getlist('selected_dates')
            if not selected_dates:
                flash("Please select at least one date.", "danger")
                return redirect(url_for('book_journey', ride_id=ride_id))
            
            for date in selected_dates:
                if seat_tracking.get(date, 0) < num_seats:
                    flash(f"Not enough seats available on {date}.", "danger")
                    return redirect(url_for('book_journey', ride_id=ride_id))
                
                seat_tracking[date] = max(0, seat_tracking.get(date, 0) - num_seats)
        
        ride.available_seats_per_date = json.dumps(seat_tracking)
        db.session.commit()
        
        new_booking = book_ride(
            user_id=current_user.id,
            ride_id=ride.id,
            status="Booked",
            total_price=total_price,
            seats_selected=num_seats,
            confirmation_email=confirmation_email,
            ride_date=selected_date if ride.category == "commuting" else ride_date,
        )
        db.session.add(new_booking)
        db.session.commit()
        
        flash("Ride booked successfully!", "success")
        return redirect(url_for('payment_page', ride_id=ride.id, seats=num_seats, total_price=total_price))
    
    return render_template(
        'book_journeys.html', 
        ride=ride, 
        available_dates=available_dates, 
        seat_tracking=seat_tracking,
        current_available_seats=current_available_seats, 
        seat_data=seat_tracking,  # Ensure seat_data is passed to the template
        user=current_user
    )




# # Route to get available dates
# @app.route('/api/get_available_dates/<int:ride_id>', methods=['GET'])
# def get_available_dates(ride_id):
#     ride = publish_ride.query.get_or_404(ride_id)
#     # Ensure recurrence_dates exists and is not empty
#     if not ride.recurrence_dates or ride.recurrence_dates.strip() == "":
#         return jsonify({"available_dates": []})
#     # Properly split and clean recurrence dates
#     available_dates = [date.strip() for date in ride.recurrence_dates.split(",")]
#     return jsonify({"available_dates": available_dates})


# # Route to get available seats
# @app.route('/api/get_available_seats/<int:ride_id>', methods=['GET', 'POST'])
# def get_available_seats(ride_id):
#     if request.method == 'POST':
#         data = request.json  
#         selected_dates = data.get("selected_dates", [])
#     else:
#         selected_dates = request.args.get("selected_dates", "").split(",")

#     ride = publish_ride.query.get_or_404(ride_id)
#     # Ensure available_seats_per_date exists
#     if not ride.available_seats_per_date or ride.available_seats_per_date.strip() == "":
#         return jsonify({"available_seats": {}})
#     seat_tracking = {}
#     try:
#         seat_tracking = json.loads(ride.available_seats_per_date)
#     except json.JSONDecodeError:
#         seat_tracking = {}  
#     # Define filtered_seats properly
#     filtered_seats = {}
#     if isinstance(selected_dates, list):
#         for date in selected_dates:
#             date = date.strip()
#             filtered_seats[date] = seat_tracking.get(date, 0)
#     else:
#         selected_dates = selected_dates.strip()
#         filtered_seats[selected_dates] = seat_tracking.get(selected_dates, 0)
#     return jsonify({"available_seats": filtered_seats})


# Route for payment page
@app.route('/payment/<int:ride_id>/<int:seats>/<float:total_price>', methods=['GET'])
@login_required
def payment_page(ride_id, seats, total_price):
    ride = publish_ride.query.get_or_404(ride_id)
    return render_template(
        "payment.html",
        ride=ride,
        seats=seats,
        total_price=total_price
    )


@app.route("/process_payment", methods=["POST"])
@login_required  
def process_payment():
    try:
        data = request.json  
        if not data:
            return jsonify({"success": False, "message": "Invalid request: No data received"}), 400
        # Extract and validate required fields
        ride_id = data.get("ride_id")
        seats = data.get("seats")
        total_price = data.get("total_price")
        card_number = data.get("card_number")
        expiry = data.get("expiry")
        cvv = data.get("cvv")
        confirmation_email = current_user.email  # Store the email of the logged-in user
        if None in [ride_id, seats, total_price, card_number, expiry, cvv]:
            print(" Missing required fields")
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        try:
            seats = int(seats)
            total_price = float(total_price)
        except ValueError:
            print(" Invalid data format for seats or total_price")
            return jsonify({"success": False, "message": "Invalid data format"}), 400
        # Validate card details
        card_number = card_number.strip()
        expiry = expiry.strip()
        cvv = cvv.strip()
        if not card_number.isdigit() or not expiry.replace("/", "").isdigit() or not cvv.isdigit():
            print(" Invalid payment details format")
            return jsonify({"success": False, "message": "Invalid payment details"}), 400
        if len(card_number) != 16 or len(expiry) != 5 or len(cvv) != 3:
            print(" Card details incorrect")
            return jsonify({"success": False, "message": "Invalid payment details"}), 400
        print("Payment data validated successfully!")
        # Ensure the user is authenticated before proceeding
        if not current_user.is_authenticated:
            print("User not authenticated")
            return jsonify({"success": False, "message": "User not logged in"}), 401
        # Fetch the ride from the database
        ride = publish_ride.query.get(ride_id)
        if not ride:
            print(f" Ride with ID {ride_id} not found")
            return jsonify({"success": False, "message": "Ride not found"}), 404
        
        # Load the available seats for the ride
        seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}

        # Deduct the booked seats
        ride_date = ride.date_time.strftime("%Y-%m-%d") if ride.date_time else None
        if ride_date:
            if ride_date in seat_tracking:
                seat_tracking[ride_date] -= seats  # Deduct seats
                seat_tracking[ride_date] = max(0, seat_tracking[ride_date])  # Prevent negative values
            else:
                print(f"Warning: Ride date {ride_date} not found in seat tracking")

            # Update available seats in the database
            ride.available_seats_per_date = json.dumps(seat_tracking)
            db.session.commit
        
        # Create a new booking entry
        new_booking = book_ride(
            user_id=current_user.id,
            ride_id=ride.id,
            status="Booked",
            total_price=total_price,
            seats_selected=seats,
            confirmation_email=confirmation_email,
            ride_date=ride.date_time  # Store the ride date
        )
        # Save the booking in the database
        db.session.add(new_booking)
        db.session.commit()
        print(f"Booking saved successfully! Booking ID: {new_booking.id}")
        # Redirect user to dashboard after successful booking
        redirect_url = url_for("dashboard")
        response = {
            "success": True,
            "message": "Payment successful & booking confirmed!",
            "redirect_url": redirect_url
        }
        return jsonify(response)
    except Exception as e:
        db.session.rollback()  # Rollback in case of failure
        print(f"Error processing payment: {str(e)}")
        return jsonify({"success": False, "message": "Internal server error"}), 500


# Route for user dashboard
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    booked_rides = book_ride.query.filter_by(user_id=current_user.id).all()
    # Categorize Rides
    one_time_rides = []
    commuting_rides = {}
    for ride in booked_rides:
        # Skip broken bookings
        if ride.ride is None:
            print(f" Ride object missing for booking ID {ride.id}")
            continue
        ride_data = {
            "booking_id": ride.id,
            "from": ride.ride.from_location,
            "to": ride.ride.to_location,
            "seats_selected": ride.seats_selected,
            "total_price": ride.total_price,
            "confirmation_email": ride.confirmation_email,
            "ride_id": ride.ride.id
        }
        # One-Time Rides (Single Date)
        if ride.ride.category == "one-time":
            ride_data["date_time"] = ride.ride.date_time.strftime('%Y-%m-%d %H:%M') if ride.ride.date_time else "N/A"
            one_time_rides.append(ride_data)
        # Commuting Rides (Multiple Dates & Times)
        else:
            ride_date = ride.ride_date.strftime('%Y-%m-%d') if ride.ride_date else "N/A"
            ride_time = ride.ride_time if hasattr(ride, "ride_time") and ride.ride_time else "N/A"
            if ride.ride.id not in commuting_rides:
                commuting_rides[ride.ride.id] = {
                    "from": ride.ride.from_location,
                    "to": ride.ride.to_location,
                    "confirmation_email": ride.confirmation_email,
                    "seats_selected": ride.seats_selected,
                    "total_price": ride.total_price,
                    "ride_id": ride.ride.id,
                    "dates_times": []  # Store multiple commuting instances
                }
            commuting_rides[ride.ride.id]["dates_times"].append({"date": ride_date, "time": ride_time})
    return render_template(
        'dashboard.html',
        one_time_rides=one_time_rides,
        commuting_rides=commuting_rides
    )


@app.context_processor
def inject_user():
    return dict(user=current_user)


# Cancelling a booking by user/passenger once booked on their user dashboard page
@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = book_ride.query.get_or_404(booking_id)
    # Ensure the current user is the one who booked the ride
    if booking.user_id != current_user.id:
        flash("You cannot cancel someone else's booking.", "danger")
        return redirect(url_for('dashboard'))
    # Fetch ride details
    ride = view_ride.query.get(booking.ride_id)
    if not ride:
        flash("Ride not found.", "danger")
        return redirect(url_for('dashboard'))
    # Load seat availability from JSON
    seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
    # Ensure the booked date exists in seat tracking
    booked_date = booking.ride_date
    if booked_date in seat_tracking:
        seat_tracking[booked_date] += booking.seats_selected  # Restore seats for that date
    # Save updated seat availability back to the database
    ride.available_seats_per_date = json.dumps(seat_tracking)
    # Sync with `publish_ride`
    publish_ride_entry = publish_ride.query.filter_by(id=ride.id).first()
    if publish_ride_entry:
        publish_ride_entry.available_seats_per_date = json.dumps(seat_tracking)
    # Delete the booking
    db.session.delete(booking)
    # Restore ride if any date has available seats again
    if any(seats > 0 for seats in seat_tracking.values()):
        db.session.add(ride)
    # Remove ride if all dates are now empty
    else:
        db.session.delete(ride)  
    db.session.commit()
    flash("Booking canceled successfully!", "success")
    return redirect(url_for('dashboard'))
