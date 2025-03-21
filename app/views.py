import os, json, sys, re, requests
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db, mail
from app.models import User, publish_ride, book_ride, saved_ride, Payment, SavedCard
from werkzeug.utils import secure_filename
from datetime import datetime
from sqlalchemy.sql import func
from flask_mail import Message
from geopy.distance import geodesic



# Route for home page
@app.route('/')
def home():
    return render_template('index.html', user=current_user)  

if __name__ == '__main__':
    app.run(debug=True)

# Redirection to the appropriate booking page from the search functionality when the user hasn't logged in
# check login status for the search functionality
@app.route('/check_login_status', methods=['GET'])
def check_login_status():
    if not current_user.is_authenticated:
        return jsonify({"is_logged_in": False, "message": "You need to log in before booking a ride."})
    return jsonify({"is_logged_in": True})

@app.before_request
def check_redirect_after_login():
    if 'redirect_after_login' in session and current_user.is_authenticated:
        redirect_path = session.pop('redirect_after_login')
        return redirect(redirect_path)

# check the redirect path
@app.route('/set_redirect_path', methods=['POST'])
def set_redirect_path():
    data = request.get_json()
    path = data.get('path')
    if path:
        session['redirect_after_login'] = path
        return jsonify({"message": "Redirect path set successfully."}), 200
    return jsonify({"message": "No path provided."}), 400

# Route for User Registration (Signup)
@app.route("/register", methods=["POST"])
def register():
    data = request.json  
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    confirm_password = data.get("confirm_password")
    
    # Email converted to lower case
    email = email.lower() if email else None

    # Validate email format
    if not email or not email.endswith("@gmail.com"):
        return jsonify({"error": "Invalid email format. Email must be a valid '@gmail.com' address."}), 400
    
    # Check if user already exists (case insensitive)
    if User.query.filter_by(email=email).first():        
        return jsonify({"message": "Email already registered"}), 400

    # Checks if the 'username' is empty
    if not data.get('username'):
        return jsonify({"error": "Username is required"}), 400
    
    # Check if 'email' is empty 
    if not data.get('email'):
        return jsonify({"error": "Email is required"}), 400

    # Strong password Validation
    if len(password) < 8 or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return jsonify({"error": "Password must be at least 8 characters long and contain at least one special character."}), 400

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

    # Email is converted to lowercase for case insensitivity
    email = email.lower() if email else None
    
    # Validate email
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    # Find the user by email (case insensitive)
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
            print(f"Storing available_seats_per_date: {available_seats_per_date}")

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
    journeys = publish_ride.query.all()
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
@app.route('/book_onetime/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def book_onetime(ride_id):
    if not current_user.is_authenticated:
        return jsonify({"error": "You need to log in before booking a ride."}), 403

    ride = publish_ride.query.filter_by(id=ride_id).first()
    # Load latest seat tracking data
    db.session.refresh(ride)  
    seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
    # Get available commuting dates
    available_dates = []
    
    # Ensure selected_date is always valid
    selected_date = request.args.get("selected_date") or request.form.get("selected_date")
    if not selected_date:
        if ride.category == "one-time":
            selected_date = ride.date_time.strftime("%Y-%m-%d")
        elif available_dates:
            selected_date = available_dates[0]
        else:
            selected_date = ""
    selected_date = selected_date.strip()
    
    # Get available seats
    current_available_seats = seat_tracking.get(selected_date, 0)
    if request.method == 'POST':
        num_seats = request.form.get('seats')
        confirmation_email = request.form.get('email')
        if not num_seats:
            flash("Please enter the number of seats.", "danger")
            return redirect(url_for('book_onetime', ride_id=ride_id))
        try:
            num_seats = int(num_seats)
        except ValueError:
            flash("Invalid seat number!", "danger")
            return redirect(url_for('book_onetime', ride_id=ride_id))
        if selected_date not in seat_tracking or seat_tracking[selected_date] < num_seats:
            flash(f"Not enough seats available on {selected_date}.", "danger")
            return redirect(url_for('book_onetime', ride_id=ride_id))
        total_price = num_seats * ride.price_per_seat
        # Redirect to Payment Page with selected_date included
        return redirect(url_for('payment_page', ride_id=ride.id, seats=num_seats, total_price=total_price, selected_dates=selected_date, email=confirmation_email))
    
    return render_template(
        'book_onetime.html', 
        ride=ride, 
        available_dates=available_dates, 
        seat_tracking=seat_tracking,
        current_available_seats=current_available_seats, 
        seat_data=seat_tracking,
        selected_date=selected_date,
        user=current_user
    )


# Route for booking a commuting journey
@app.route('/book_commuting/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def book_commuting(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    print(f"ride is {ride} right on entering commuting route")
    # Load latest seat tracking data
    db.session.refresh(ride)
    seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
    # Get available commuting dates
    available_dates = ride.recurrence_dates.split(",") if ride.recurrence_dates else []
    seat_data = seat_tracking
    
    if request.method == 'POST':
        num_seats = request.form.get('seats')
        selected_dates = request.form.getlist("selected_dates")
        confirmation_email = request.form.get('email')
        
        if not num_seats or not selected_dates:
            flash("Please enter all required fields.", "danger")
            return redirect(url_for('book_commuting', ride_id=ride_id))
        try:
            num_seats = int(num_seats)
        except ValueError:
            flash("Invalid seat number!", "danger")
            return redirect(url_for('book_commuting', ride_id=ride_id))
        total_price=request.form.get('total_price')
        
        return redirect(url_for('payment_page', ride_id=ride.id, seats=num_seats, total_price=total_price, selected_date=",".join(selected_dates), email=confirmation_email))
    
    return render_template(
        'book_commuting.html', 
        ride=ride, 
        available_dates=available_dates, 
        seat_data=seat_data,
        seat_tracking=seat_tracking,
        user=current_user
    )


# Route to get available dates
@app.route('/api/get_available_dates/<int:ride_id>', methods=['GET'])
def get_available_dates(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    # Ensure recurrence_dates exists and is not empty
    if not ride.recurrence_dates or ride.recurrence_dates.strip() == "":
        return jsonify({"available_dates": []})
    # Properly split and clean recurrence dates
    available_dates = [date.strip() for date in ride.recurrence_dates.split(",")]
    return jsonify({"available_dates": available_dates})


# Route to get available seats
@app.route('/api/get_available_seats/<int:ride_id>', methods=['GET', 'POST'])
def get_available_seats(ride_id):
    if request.method == 'POST':
        data = request.json  
        selected_dates = data.get("selected_dates", [])
    else:
        selected_dates = request.args.get("selected_dates", "").split(",")
    ride = publish_ride.query.get_or_404(ride_id)
    
    # Ensure available_seats_per_date exists
    if not ride.available_seats_per_date or ride.available_seats_per_date.strip() == "":
        return jsonify({"available_seats": {}})
    seat_tracking = {}
    try:
        seat_tracking = json.loads(ride.available_seats_per_date)
    except json.JSONDecodeError:
        seat_tracking = {}  
    
    # Define filtered_seats properly
    filtered_seats = {}
    if isinstance(selected_dates, list):
        for date in selected_dates:
            date = date.strip()
            filtered_seats[date] = seat_tracking.get(date, 0)
    else:
        selected_dates = selected_dates.strip()
        filtered_seats[selected_dates] = seat_tracking.get(selected_dates, 0)
    return jsonify({"available_seats": filtered_seats})


# Route for payment page
@app.route('/payment/<int:ride_id>/<int:seats>/<float:total_price>', methods=['GET'])
@login_required
def payment_page(ride_id, seats, total_price):
    selected_dates = request.args.getlist("selected_dates")
    email = request.args.get("email", None)
    ride = publish_ride.query.get_or_404(ride_id)
    return render_template(
        "payment.html",
        ride=ride,
        seats=seats,
        total_price=total_price,
        selected_date=selected_dates,
        email=email
    )


@app.route("/process_payment", methods=["POST"])
@login_required  
def process_payment():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "Invalid request: No data received"}), 400
        
        ride_id = data.get("ride_id")
        seats = data.get("seats")
        total_price = data.get("total_price")
        selected_dates = data.get("selected_dates")  # Should be a list
        confirmation_email = data.get("email")
        use_saved_card = data.get("use_saved_card", False)
        saved_card_id = int(data.get("saved_card_id", 0)) if data.get("saved_card_id") else None

        # Ensure selected_dates is always a list
        if not selected_dates or not isinstance(selected_dates, list):
            return jsonify({"success": False, "message": "No valid selected dates provided"}), 400
        
        ride = publish_ride.query.get(ride_id)
        if not ride:
            return jsonify({"success": False, "message": "Ride not found"}), 404
        
        # Load seat tracking data
        seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
        seats = int(seats)
        per_day_price = seats * ride.price_per_seat

        # Handle Payment Method (Saved Card vs. Manual Entry)
        if use_saved_card:
            # If using a saved card, validate it
            saved_card = SavedCard.query.get(saved_card_id)
            if not saved_card or saved_card.user_id != current_user.id:
                return jsonify({"success": False, "message": "Invalid saved card selected."}), 400
            # decrypted_card_number = saved_card.get_card_number()
        
        else:
            # If entering card manually, validate details
            card_number = data.get("card_number")
            expiry = data.get("expiry")
            cardholder_name = data.get("cardholder_name")
            save_card = data.get("save_card", False)

            if not card_number or not expiry or not cardholder_name:
                return jsonify({"success": False, "message": "Card details missing."}), 400
            
            # Extract last four digits for reference
            last_four_digits = card_number[-4:]

            # Save the card if requested
            if save_card:
                new_card = SavedCard(
                    user_id=current_user.id,
                    expiry_date=expiry,
                    cardholder_name=cardholder_name,
                )
                new_card.set_card_number(card_number)
                db.session.add(new_card)
                db.session.commit()

        for selected_date in selected_dates:
            if selected_date in seat_tracking:
                seat_tracking[selected_date] -= seats
                seat_tracking[selected_date] = max(0, seat_tracking[selected_date])
            else:
                print(f"Warning: Ride date {selected_date} not found in seat tracking")
                return jsonify({"success": False, "message": f"No available seats on {selected_date}"}), 400
            
            # Save the booking
            new_booking = book_ride(
                user_id=current_user.id,
                ride_id=ride.id,
                status="Booked",
                total_price=total_price,
                seats_selected=seats,
                confirmation_email=confirmation_email,
                ride_date=datetime.strptime(selected_date, "%Y-%m-%d").date(),
            )
            db.session.add(new_booking)
            db.session.commit()
            
            new_payment = Payment(
                user_id=current_user.id,
                ride_id=ride.id,
                book_ride_id=new_booking.id,
                amount=per_day_price,  
                status="Success",
                timestamp=datetime.utcnow()
            )
            db.session.add(new_payment)
            db.session.commit()
        
        # Update available seats in database
        ride.available_seats_per_date = json.dumps(seat_tracking)
        db.session.commit()

        # Send Booking Confirmation Email
        send_booking_confirmation_email(confirmation_email, ride, seats, total_price, selected_dates)

        return jsonify({"success": True, "message": "Payment successful & booking confirmed!", "redirect_url": url_for("dashboard")})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Internal server error", "error": str(e)}), 500


# Route to send booking confirmation email
def send_booking_confirmation_email(email, ride, seats, total_price, selected_dates):
    try:
        subject = "Booking Confirmation - Your Ride Details"
        selected_dates_str = ", ".join(selected_dates)

        body = f"""
        Dear User,

        Thank you for booking your ride. Here are your details:

        📍 From: {ride.from_location}
        📍 To: {ride.to_location}
        🚗 Driver: {ride.driver_name}
        🎟️ Seats Booked: {seats}
        💰 Total Price: £{total_price}
        📅 Ride Date(s): {selected_dates_str}

        If you have any issues, please contact support.

        Regards,
        CatchMyRide
        """

        msg = Message(subject, recipients=[email], body=body)
        mail.send(msg)

        print(f"Booking confirmation email sent to {email}")

    except Exception as e:
        print(f"Error sending email: {e}")


# Route to resend email from the dashboard if the user wants
@app.route("/resend_booking_confirmation/<int:booking_id>", methods=["POST"])
@login_required
def resend_booking_confirmation(booking_id):
    """ Allows users to resend the booking confirmation email """
    booking = book_ride.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    ride = publish_ride.query.get(booking.ride_id)
    if not ride:
        return jsonify({"success": False, "message": "Ride not found"}), 404

    send_booking_confirmation_email(booking.confirmation_email, ride, booking.seats_selected, booking.total_price, [str(booking.ride_date)])

    return jsonify({"success": True, "message": "Booking confirmation email resent!"})

@app.context_processor
def inject_user():
    return dict(user=current_user)


@app.route('/search_journeys', methods=['GET'])
def search_journeys():
    from_location = request.args.get("from")
    to_location = request.args.get("to")
    date = request.args.get("date")
    passengers = int(request.args.get("passengers", 1))

    # Query One-Time Rides 
    one_time_rides = publish_ride.query.filter(
        publish_ride.from_location.ilike(f"%{from_location}%"),
        publish_ride.to_location.ilike(f"%{to_location}%"),
        func.date(publish_ride.date_time) == date,
        publish_ride.category == "one-time",
        publish_ride.is_available == True
    ).all()

    # Query Commuting Rides 
    commuting_rides = publish_ride.query.filter(
        publish_ride.from_location.ilike(f"%{from_location}%"),
        publish_ride.to_location.ilike(f"%{to_location}%"),
        publish_ride.category == "commuting",
        publish_ride.is_available == True,
        func.lower(publish_ride.recurrence_dates).like(f"%{date}%")
    ).all()

    journey_list = []

    # One-Time Rides
    for ride in one_time_rides:
        seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
        available_seats = seat_data.get(date, 0)
        if available_seats >= passengers:
            journey_list.append({
                "id": ride.id,
                "from": ride.from_location,
                "to": ride.to_location,
                "date": ride.date_time.strftime('%Y-%m-%d'),
                "time": ride.date_time.strftime('%H:%M') if ride.date_time else "Not Provided",
                "seats_available": available_seats,
                "price_per_seat": ride.price_per_seat,
                "category": ride.category
            })

    # Commuting Rides
    for ride in commuting_rides:
        seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
        available_seats = seat_data.get(date, 0)
        if available_seats >= passengers:
            journey_list.append({
                "id": ride.id,
                "from": ride.from_location,
                "to": ride.to_location,
                "date": date,
                "time": "Flexible (Multiple Times)",
                "seats_available": available_seats,
                "price_per_seat": ride.price_per_seat,
                "category": ride.category
            })

    return jsonify({"journeys": journey_list})



def get_base_url():
    """ Automatically detects and returns the correct base URL. """
    # If running in GitHub Codespaces
    if "CODESPACE_NAME" in os.environ:
        return f"https://{os.getenv('CODESPACE_NAME')}-5000.githubpreview.dev"

    # If running in production (detect custom domain)
    if "PRODUCTION_DOMAIN" in os.environ:
        return f"https://{os.getenv('PRODUCTION_DOMAIN')}"

    # Otherwise, use whatever Flask detects
    return request.host_url.rstrip('/')


# Route for forgot password 
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('forgot_password.html')

    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form  # Handle form submissions

    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user:
        token = user.generate_reset_password_token(secret_key=app.config['SECRET_KEY'])
        # Check if running in GitHub Codespaces
        codespace_url = os.getenv("CODESPACE_NAME")
        if codespace_url:
            base_url = f"https://{codespace_url}-5000.app.github.dev"
        else:
            base_url = request.url_root.rstrip('/')  # Fallback for local use

        reset_url = f"{base_url}{url_for('reset_password', token=token, user_id=user.id)}"
        print("Generated Reset URL:", reset_url)


        subject = 'Password Reset Request'
        msg = Message(subject, recipients=[email], body=f"""
To reset your password, visit the following link: {reset_url}
If you did not request this, please ignore this email. The link expires in 10 minutes.
        """)
        mail.send(msg)

        return jsonify({"success": True, "message": "Password reset link sent to your email."})
    else:
        return jsonify({"success": False, "message": "No account found with that email address."}), 404


@app.route('/reset-password/<token>/<int:user_id>', methods=['GET', 'POST'])
def reset_password(token, user_id):
    if request.method == 'GET':
        # Validate token before showing reset page
        user = User.validate_reset_password_token(token, secret_key=app.config['SECRET_KEY'], user_id=user_id)

        if not user:
            return jsonify({"success": False, "message": "Invalid or expired reset link!"}), 400

        # Render the reset password HTML page (you already have it)
        return render_template("reset_password.html", token=token, user_id=user_id)

    # If it's a POST request, process password reset
    if request.method == 'POST':
        # Handle both JSON and form data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        new_password = data.get('password')

        print("Received Token:", token)
        print("Received User ID:", user_id)

        user = User.validate_reset_password_token(token, secret_key=app.config['SECRET_KEY'], user_id=user_id)

        if not user:
            return redirect(url_for('index', expired_reset=True))

        if new_password:
            user.set_password(new_password)
            db.session.commit()
            return jsonify({"success": True, "message": "Your password has been updated! You can now log in."})

        return jsonify({"success": False, "message": "Password update failed!"}), 400


@app.route('/dashboard')
@login_required
def dashboard():
    # Get upcoming and inactive journeys
    booked_rides = book_ride.query.filter_by(user_id=current_user.id).all()
    upcoming_journeys = []
    inactive_journeys = []

    current_time = datetime.utcnow()

    for booking in booked_rides:
        ride = publish_ride.query.get(booking.ride_id)
        if ride:
            is_canceled = booking.status == "Canceled"
            price_per_seat = ride.price_per_seat

            journey_data = {
                "booking_id": booking.id,
                "ride_id": ride.id,
                "from": ride.from_location,
                "to": ride.to_location,
                "date": booking.ride_date.strftime('%Y-%m-%d'),
                "time": ride.commute_times if ride.category == "commuting" else (
                    ride.date_time.strftime('%H:%M') if ride.date_time else "Not Provided"
                ),
                "status": booking.status,
                "price": price_per_seat,
                "seats_booked": booking.seats_selected
            }

            if is_canceled:
                inactive_journeys.append(journey_data)
            else:
                upcoming_journeys.append(journey_data)

    # Get published rides (separate one-time and commuting)
    user_published_rides = publish_ride.query.filter_by(driver_id=current_user.id).all()
    published_rides = {"one_time": [], "commuting": []}

    for ride in user_published_rides:
        if ride.category == "one-time":
            published_rides["one_time"].append({
                "ride_id": ride.id,
                "from": ride.from_location,
                "to": ride.to_location,
                "date": ride.date_time.strftime('%Y-%m-%d'),
                "time": ride.date_time.strftime('%H:%M'),
                "price": ride.price_per_seat,
                "passengers": [
                    {"name": User.query.get(passenger.user_id).username, "email": passenger.confirmation_email}
                    for passenger in book_ride.query.filter_by(ride_id=ride.id).all()
                ]
            })
        else:  # Commuting rides
            ride_data = {
                "ride_id": ride.id,
                "from": ride.from_location,
                "to": ride.to_location,
                "time": ride.commute_times,
                "price": ride.price_per_seat,
                "dates": {}
            }

            ride_dates = db.session.query(book_ride.ride_date).filter_by(ride_id=ride.id).distinct().all()
            for date_obj in ride_dates:
                date_str = date_obj[0].strftime('%Y-%m-%d')
                passengers = book_ride.query.filter(
                    book_ride.ride_id == ride.id,
                    book_ride.ride_date == date_obj[0],
                    book_ride.status != "Canceled"
                ).all()
                ride_data["dates"][date_str] = [
                    {"name": User.query.get(passenger.user_id).username, "email": passenger.confirmation_email}
                    for passenger in passengers
                ]

            published_rides["commuting"].append(ride_data)

    return render_template("dashboard.html",
                           user=current_user,
                           upcoming_journeys=upcoming_journeys,
                           inactive_journeys=inactive_journeys,
                           published_rides=published_rides)


@app.route("/delete_saved_card/<int:card_id>", methods=["DELETE"])
@login_required
def delete_saved_card(card_id):
    saved_card = SavedCard.query.get(card_id)

    if not saved_card or saved_card.user_id != current_user.id:
        return jsonify({"success": False, "message": "Card not found or unauthorized"}), 403

    db.session.delete(saved_card)
    db.session.commit()

    return jsonify({"success": True, "message": "Card deleted successfully"})


@app.route("/cancel_booking/<int:booking_id>", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = book_ride.query.get(booking_id)
    if not booking:
        return jsonify({"success": False, "message": "Booking not found"}), 404

    ride = publish_ride.query.get(booking.ride_id)

    # Find associated payment
    payment = Payment.query.filter_by(book_ride_id=booking.id).first()

    # Get current time and ride time
    current_time = datetime.utcnow()
    ride_time = booking.ride_date
    time_difference = (ride_time - current_time).total_seconds() / 60  # Convert to minutes

    # Find associated payment
    payment = Payment.query.filter_by(book_ride_id=booking.id).first()

    if time_difference < 15:
        # User is charged 75% of the fee
        cancellation_fee = round(payment.amount * 0.75, 2)
        refund_amount = round(payment.amount - cancellation_fee, 2)
        charge_message = f"Charged 75% cancellation fee: £{cancellation_fee}. Refunded: £{refund_amount}."
        # Update payment record
        if payment:
            payment.status = "Partially Refunded"
            payment.refunded = True
    else:
        # Full refund
        refund_amount = payment.amount
        charge_message = "Full refund issued."
        # Update payment record
        if payment:
            payment.status = "Refunded"
            payment.refunded = True

    # Mark the booking as canceled
    booking.status = "Canceled"
    booking.cancellation_timestamp = current_time

    # Restore seats for the canceled date
    seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
    selected_date_str = booking.ride_date.strftime("%Y-%m-%d")

    if selected_date_str in seat_tracking:
        seat_tracking[selected_date_str] += booking.seats_selected  # Restore the canceled seats

    ride.available_seats_per_date = json.dumps(seat_tracking)
    db.session.commit()

    return jsonify({"success": True, "message": f"Booking successfully canceled. Refund: £{refund_amount}"}), 200


# Route to filter out journeys
@app.route('/filter_journeys', methods=['GET'])
def filter_journeys():
    from_location = request.args.get("from")
    to_location = request.args.get("to")
    date = request.args.get("date")
    passengers = int(request.args.get("passengers", 1))

    # Query One-Time Rides
    one_time_rides = publish_ride.query.filter(
        publish_ride.from_location.ilike(f"%{from_location}%"),
        publish_ride.to_location.ilike(f"%{to_location}%"),
        func.date(publish_ride.date_time) == date,
        publish_ride.category == "one-time",
        publish_ride.is_available == True
    ).all()

    # Query Commuting Rides
    commuting_rides = publish_ride.query.filter(
        publish_ride.from_location.ilike(f"%{from_location}%"),
        publish_ride.to_location.ilike(f"%{to_location}%"),
        publish_ride.category == "commuting",
        publish_ride.is_available == True,
        func.lower(publish_ride.recurrence_dates).like(f"%{date}%")
    ).all()

    # Prepare final data structure
    journeys = []

    # Process One-Time Rides
    for ride in one_time_rides:
        seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
        available_seats = seat_data.get(date, 0)
        if available_seats >= passengers:
            journeys.append({
                "id": ride.id,
                "from_location": ride.from_location,
                "to_location": ride.to_location,
                "date_time": ride.date_time,
                "seat_tracking": seat_data,
                "price_per_seat": ride.price_per_seat,
                "category": ride.category,
                "driver_name": ride.driver_name,
                "user_has_booked": False,  # This can be enhanced if needed
                "recurrence_dates": None,
                "commute_times": None
            })

    # Process Commuting Rides
    for ride in commuting_rides:
        seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
        available_seats = seat_data.get(date, 0)
        if available_seats >= passengers:
            journeys.append({
                "id": ride.id,
                "from_location": ride.from_location,
                "to_location": ride.to_location,
                "date_time": None,
                "seat_tracking": seat_data,
                "price_per_seat": ride.price_per_seat,
                "category": ride.category,
                "driver_name": ride.driver_name,
                "user_has_booked": False,
                "recurrence_dates": ride.recurrence_dates,
                "commute_times": ride.commute_times
            })

    return render_template('view_journeys.html', journeys=journeys, user=current_user)


# ID 14 here:
# Store live locations in memory (Consider using a database for production)
live_locations = {}

# ✅ Route to display the pickup location map
@app.route('/view_pickup/<int:ride_id>', methods=['GET'])
@login_required
def view_pickup(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    return render_template("view_pickup.html", ride_id=ride_id, user=current_user)

# ✅ API to get pickup location for a ride
@app.route('/api/get_pickup_location/<int:ride_id>', methods=['GET'])
@login_required
def get_pickup_location(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    return jsonify({"from_location": ride.from_location}), 200

# ✅ Passenger Updates Their Location
@app.route('/api/track_passenger_location', methods=['POST'])
@login_required
def track_passenger_location():
    data = request.json
    ride_id = data.get("ride_id")
    lat = data.get("latitude")
    lon = data.get("longitude")

    if not ride_id or not lat or not lon:
        return jsonify({"error": "Invalid data"}), 400

    live_locations[f"passenger_{ride_id}"] = (lat, lon)
    return jsonify({"message": "Passenger location updated"}), 200

# ✅ Driver Updates Their Location
@app.route('/api/track_driver_location', methods=['POST'])
@login_required
def track_driver_location():
    data = request.json
    ride_id = data.get("ride_id")
    lat = data.get("latitude")
    lon = data.get("longitude")

    if not ride_id or not lat or not lon:
        return jsonify({"error": "Invalid data"}), 400

    live_locations[f"driver_{ride_id}"] = (lat, lon)
    return jsonify({"message": "Driver location updated"}), 200

# ✅ Fetch Both Passenger & Driver Live Locations
@app.route('/api/get_live_locations/<int:ride_id>', methods=['GET'])
@login_required
def get_live_locations(ride_id):
    passenger_loc = live_locations.get(f"passenger_{ride_id}")
    driver_loc = live_locations.get(f"driver_{ride_id}")

    if not passenger_loc and not driver_loc:
        return jsonify({"error": "No location data available"}), 404

    # Check if they are within 100 meters
    nearby = False
    if passenger_loc and driver_loc:
        distance = geodesic(passenger_loc, driver_loc).meters
        if distance <= 100:
            nearby = True

    return jsonify({
        "passenger": passenger_loc,
        "driver": driver_loc,
        "nearby": nearby
    })

# ✅ API to track if passenger reached pickup point
@app.route('/api/check_arrival', methods=['POST'])
@login_required
def check_arrival():
    data = request.json
    ride_id = data.get("ride_id")
    user_lat = data.get("latitude")
    user_lon = data.get("longitude")

    ride = publish_ride.query.get_or_404(ride_id)
    pickup_lat, pickup_lon = get_coordinates_from_address(ride.from_location)

    if not pickup_lat or not pickup_lon:
        return jsonify({"error": "Invalid pickup location"}), 400

    # Calculate distance to pickup point
    passenger_location = (user_lat, user_lon)
    pickup_location = (pickup_lat, pickup_lon)
    distance = geodesic(passenger_location, pickup_location).meters

    if distance <= 50:  # Within 50 meters
        return jsonify({"arrived": True, "message": "You have arrived at the pickup location!"})
    else:
        return jsonify({"arrived": False, "message": "Keep moving towards the pickup location."})

# ✅ Helper Function to Get Coordinates (Uses OpenStreetMap Nominatim)
def get_coordinates_from_address(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json"
    response = requests.get(url, headers={"User-Agent": "CatchMyRide/1.0"})

    if response.status_code == 200:
        data = response.json()
        if len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            return lat, lon
    return None, None