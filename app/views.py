import os, json
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db
from app.models import User, publish_ride, view_ride, book_ride, SavedRide
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy.sql import func


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
        category = request.form['category']
        driver_name = current_user.username
        price_per_seat = float(request.form['price_per_seat'])

        # Initialize variables
        date_time = None
        recurrence_dates = None
        commute_times = None
        available_seats_per_date = None
        available_seats = None  # Define this variable properly

        if category == "one-time":
            date_time_str = request.form.get('date_time')
            available_seats = int(request.form.get('available_seats', 0))  # ✅ Ensure it's an integer

            if not date_time_str:
                flash("Please select a valid Date & Time for one-time rides.", "danger")
                return redirect(url_for('publish_ride_view'))

            try:
                date_time = datetime.strptime(date_time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                flash("Invalid Date & Time format!", "danger")
                return redirect(url_for('publish_ride_view'))

            available_seats_per_date = json.dumps({"seats": available_seats})  # ✅ Store as JSON instead of None


        else:  # **Commuting Ride (Multiple Recurring Days & Times)**
            recurrence_dates_list = request.form.getlist('recurrence_dates')
            commute_times_list = request.form.getlist('commute_times')
            available_seats = int(request.form.get('available_seats', 0))  # ✅ Ensure available_seats is an integer

            if not recurrence_dates_list or not commute_times_list:
                flash("Please select at least one commute day and time.", "danger")
                return redirect(url_for('publish_ride_view'))

            recurrence_dates = ",".join(recurrence_dates_list)
            commute_times = ",".join(commute_times_list)

            # ✅ Split the recurrence_dates string properly
            recurrence_dates_list = [date.strip() for date in recurrence_dates.split(",")]

            # ✅ Ensure each date is stored as a separate key
            seats_dict = {date: available_seats for date in recurrence_dates_list}
            available_seats_per_date = json.dumps(seats_dict)  # ✅ Store properly formatted JSON



        # ✅ Save the Ride
        new_ride = publish_ride(
            driver_id=current_user.id,
            driver_name=driver_name,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats_per_date=available_seats_per_date,  # ✅ Only for commuting rides
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
            available_seats_per_date=available_seats_per_date,  # ✅ Only for commuting rides
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



@app.route('/view_journeys')
def view_journeys():
    db.session.commit()  # Ensure session is up to date
    db.session.expire_all()  # Ensure fresh data

    # Get all rides that still have available seats on any date
    journeys = view_ride.query.all()

    booked_journey_ids = set()
    if current_user.is_authenticated:
        booked_journey_ids = {booking.ride_id for booking in book_ride.query.filter_by(user_id=current_user.id).all()}

    for journey in journeys:
        try:
            journey.seat_tracking = json.loads(journey.available_seats_per_date) if journey.available_seats_per_date else {}
        except (json.JSONDecodeError, TypeError):
            journey.seat_tracking = {}  # ✅ Prevent errors if data is invalid

        journey.user_has_booked = journey.id in booked_journey_ids  

    return render_template('view_journeys.html', journeys=journeys, user=current_user)


@app.route('/book_journey/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def book_journey(ride_id):
    view_ride_entry = view_ride.query.filter_by(id=ride_id).first()
    ride = view_ride_entry if view_ride_entry else publish_ride.query.get_or_404(ride_id)

    # ✅ Get available dates from recurrence_dates (for commuting rides)
    available_dates = []
    if ride.category == "commuting" and ride.recurrence_dates:
        available_dates = [date.strip() for date in ride.recurrence_dates.split(",")]

    # ✅ Convert JSON string to dictionary
    seat_tracking = {}
    if ride.available_seats_per_date:
        try:
            seat_tracking = json.loads(ride.available_seats_per_date)  # Ensure valid JSON
        except json.JSONDecodeError:
            seat_tracking = {}

    # ✅ Get selected date from request or set default
    selected_dates = request.args.get("selected_date", available_dates[0] if available_dates else None)


    # ✅ Ensure the selected date is in seat_tracking
    current_available_seats = seat_tracking.get(selected_dates, 0) if selected_dates else 0


    if request.method == 'POST':
        num_seats = int(request.form['seats'])
        confirmation_email = request.form['email']

        # ✅ Handle one-time ride bookings
        if ride.category == "one-time":
            seat_data = json.loads(ride.available_seats_per_date)  # Extract available seats
            available_seats = seat_data.get("seats", 0)  # Extract numeric value

            if num_seats > available_seats:
                return jsonify({"success": False, "message": f"Not enough available seats! Only {available_seats} left."}), 400
                
            ride_date = ride.date_time
            ride_time = ride.date_time.strftime("%H:%M")  # Extract time from timestamp

            # ✅ Calculate total price for one-time rides
            total_price = num_seats * ride.price_per_seat

            new_booking = book_ride(
                user_id=current_user.id,
                ride_id=ride.id,
                status="Booked",
                total_price=total_price,
                seats_selected=num_seats,
                confirmation_email=confirmation_email,
                ride_date=ride_date,
                ride_time=ride_time
            )
            db.session.add(new_booking)

            # ✅ Reduce available seats for one-time rides
            if view_ride_entry:
                view_ride_entry.available_seats_per_date = json.dumps(
                    {ride_date.strftime("%Y-%m-%d"): max(0, seat_tracking.get(ride_date.strftime("%Y-%m-%d"), 0) - num_seats)}
                )

            db.session.commit()

        else:  # ✅ Handle commuting rides
            selected_dates = request.form.get('selected_dates', "").split(",")
            selected_times = request.form.get('selected_time', "").split(",")

            if not selected_dates or not selected_times:
                flash("Please select at least one date and time.", "danger")
                return redirect(url_for('book_journey', ride_id=ride_id))

            # ✅ Ensure seat tracking contains correct seat numbers
            for date in selected_dates:
                date = date.strip()
                if date in seat_tracking:
                    if seat_tracking[date] >= num_seats:
                        seat_tracking[date] -= num_seats  # ✅ Deduct seats for this date
                    else:
                        flash(f"Not enough seats available on {date}", "danger")
                        return redirect(url_for('book_journey', ride_id=ride_id))
                else:
                    flash(f"Invalid date selection: {date}", "danger")
                    return redirect(url_for('book_journey', ride_id=ride_id))

                for time in selected_times:
                    new_booking = book_ride(
                        user_id=current_user.id,
                        ride_id=ride.id,
                        status="Booked",
                        total_price=num_seats * ride.price_per_seat,
                        seats_selected=num_seats,
                        confirmation_email=confirmation_email,
                        ride_date=date,
                        ride_time=time.strip()
                    )
                    db.session.add(new_booking)

            # ✅ Update seat availability after booking
            ride.available_seats_per_date = json.dumps(seat_tracking)

            # ✅ Remove ride from view if ALL dates are fully booked
            if all(seats == 0 for seats in seat_tracking.values()):
                if view_ride_entry:
                    db.session.delete(view_ride_entry)

            db.session.commit()

        flash("Ride booked successfully!", "success")
        return redirect(url_for('payment', ride_id=ride.id, seats=num_seats, total_price=total_price, date=ride_date.strftime("%Y-%m-%d")))

    
    return render_template('book_journeys.html', ride=ride, available_dates=available_dates, seat_tracking=seat_tracking, current_available_seats=current_available_seats, user=current_user)

@app.route('/api/get_available_dates/<int:ride_id>', methods=['GET'])
def get_available_dates(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)

    if not ride.recurrence_dates:
        return jsonify({"available_dates": []})

    available_dates = [date.strip() for date in ride.recurrence_dates.split(",")]

    print(f"🚀 DEBUG: API Sending Available Dates for Ride {ride_id}: {available_dates}")
    return jsonify({"available_dates": available_dates})


@app.route('/api/get_available_seats/<int:ride_id>', methods=['GET', 'POST'])  # ✅ Allow POST
def get_available_seats(ride_id):
    if request.method == 'POST':
        data = request.json  # ✅ Read JSON data from request
        selected_dates = data.get("selected_dates", [])
    else:
        selected_dates = request.args.get("selected_dates", "").split(",")

    ride = publish_ride.query.get_or_404(ride_id)

    if not ride.available_seats_per_date:
        return jsonify({"available_seats": {}})

    seat_tracking = json.loads(ride.available_seats_per_date)

    # ✅ Filter available seats for selected dates
    filtered_seats = {date: seat_tracking.get(date, 0) for date in selected_dates}

    print(f"🚀 DEBUG: Available seats for {ride_id}: {filtered_seats}")

    return jsonify({"available_seats": filtered_seats})



@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    booked_rides = book_ride.query.filter_by(user_id=current_user.id).all()

    rides_data = []
    for ride in booked_rides:
        rides_data.append({
            "booking_id": ride.id,
            "from": ride.ride.from_location,
            "to": ride.ride.to_location,
            "date_time": ride.ride.date_time.strftime('%Y-%m-%d %H:%M') if ride.ride.date_time else "N/A (Commuting)",
            "seats_selected": ride.seats_selected,
            "total_price": ride.total_price,
            "confirmation_email": ride.confirmation_email,
            "category": ride.ride.category,
            "ride_id": ride.ride.id
        })

    return jsonify({
        "success": True,
        "message": "Dashboard data fetched successfully",
        "booked_rides": rides_data
    })

    
    # Pass both the booked rides and their details to the template
    return render_template('dashboard.html', booked_rides=booked_rides)

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

    # ✅ Load seat availability from JSON
    seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}

    # ✅ Ensure the booked date exists in seat tracking
    booked_date = booking.ride_date
    if booked_date in seat_tracking:
        seat_tracking[booked_date] += booking.seats_selected  # ✅ Restore seats for that date

    # ✅ Save updated seat availability back to the database
    ride.available_seats_per_date = json.dumps(seat_tracking)

    # ✅ Sync with `publish_ride`
    publish_ride_entry = publish_ride.query.filter_by(id=ride.id).first()
    if publish_ride_entry:
        publish_ride_entry.available_seats_per_date = json.dumps(seat_tracking)

    # ✅ Delete the booking
    db.session.delete(booking)

    # ✅ Restore ride if any date has available seats again
    if any(seats > 0 for seats in seat_tracking.values()):
        db.session.add(ride)
    else:
        db.session.delete(ride)  # ✅ Remove ride if all dates are now empty

    db.session.commit()

    flash("Booking canceled successfully!", "success")
    return redirect(url_for('dashboard'))


@app.route('/payment/<int:ride_id>/<int:seats>/<float:total_price>', methods=['GET'])
@login_required
def payment_page(ride_id, seats, total_price):
    ride = publish_ride.query.get_or_404(ride_id)

    return jsonify({
        "success": True,
        "message": "Payment page loaded",
        "ride_id": ride_id,
        "seats": seats,
        "total_price": total_price,
        "ride_details": {
            "from": ride.from_location,
            "to": ride.to_location,
            "driver": ride.driver_name,
            "price_per_seat": ride.price_per_seat
        }
    })


@app.route("/process_payment", methods=["POST"])
@login_required
def process_payment():
    data = request.json  # ✅ Expect JSON instead of form data

    ride_id = data.get("ride_id")
    seats = int(data.get("seats", 0))
    total_price = float(data.get("total_price", 0.0))
    card_number = data.get("card_number")
    expiry = data.get("expiry")
    cvv = data.get("cvv")

    # ✅ Validate input
    if not all([ride_id, seats, total_price, card_number, expiry, cvv]):
        return jsonify({"success": False, "message": "Missing payment details"}), 400

    if len(card_number) != 16 or len(expiry) != 5 or len(cvv) != 3:
        return jsonify({"success": False, "message": "Invalid payment details"}), 400

    # ✅ Simulated Payment Success (Redirect to Dashboard)
    return jsonify({
        "success": True,
        "message": "Payment successful",
        "redirect_url": url_for("dashboard", _external=True)
    })
