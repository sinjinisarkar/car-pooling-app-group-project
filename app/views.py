import os, json, sys, re, requests
from flask import render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from app import app, db, mail
from app.models import User, publish_ride, book_ride, saved_ride, Payment, SavedCard, ChatMessage, EditProposal, PlatformSetting, RideRating
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from sqlalchemy.sql import func
from sqlalchemy import and_, func, not_
from flask_mail import Message
from geopy.distance import geodesic
from collections import defaultdict
import pytz
from app.utils import manager_required, get_platform_fee


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

    # Checks for username duplication
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400
    
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

    # Send role-based redirect path under the key expected by auth.js
    redirect_path = url_for('manager_dashboard') if user.is_manager else url_for('home')

    return jsonify({
        "message": "Login successful",
        "redirect_url": redirect_path
        }), 200


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
        from_location = request.form.get('from_location')
        to_location = request.form.get('to_location')
        category = request.form.get('category')
        driver_name = current_user.username
        price_input = request.form.get('price_per_seat')
        if not price_input:
            flash("Price per seat is required.", "danger")
            return redirect(url_for('publish_ride_view'))
        
        try:
            price_per_seat = float(price_input)
        except ValueError:
            flash("Invalid price format.", "danger")
            return redirect(url_for('publish_ride_view'))

         # Validation messages for testing
        if not from_location or not to_location or not category or not request.form.get('price_per_seat'):
            return jsonify({"error": "All fields are required."}), 400

        if price_per_seat < 1:
            return jsonify({"error": "Price per seat must be at least 1."}), 400

        available_seats = int(request.form.get('available_seats', 0))
        if available_seats < 1:
            return jsonify({"error": "Available seats must be at least 1."}), 400
        
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

    # get current UK time (timezone-aware)
    london = pytz.timezone("Europe/London")
    aware_now = datetime.now(london)
    now = aware_now.replace(tzinfo=None)

    db.session.commit()  
    db.session.expire_all()  
    
    journeys = []

    for ride in publish_ride.query.all():

        if ride.category == "one-time" and ride.date_time < now:
            continue  # Skip past one-time rides

        # Filter out past dates from commuting rides (for display only)
        try:
            seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
        except (json.JSONDecodeError, TypeError):
            seat_data = {}

        if ride.category == "commuting":
            filtered_seats = {}
            commute_times = []
            try:
                commute_times = [datetime.strptime(t.strip(), "%H:%M").time() for t in ride.commute_times.split(",") if t.strip()]
            except Exception as e:
                print(f"error: Failed to parse commute_times: {ride.commute_times} — {e}")

            earliest_time = min(commute_times) if commute_times else time(0, 0)

            for date, seats in seat_data.items():
                try:
                    dt = datetime.combine(datetime.strptime(date, "%Y-%m-%d").date(), earliest_time)
                    if dt >= now:
                        filtered_seats[date] = seats
                except Exception as e:
                    print(f"error: Could not parse datetime for {date}: {e}")
            seat_data = filtered_seats

        ride.seat_tracking = seat_data
        journeys.append(ride)

        # Remove journeys where no future dates have seats left
        journeys = [
            journey for journey in journeys
            if journey.seat_tracking and any(seats > 0 for seats in journey.seat_tracking.values())
        ]
    
    booked_journey_ids = set()
    
    if current_user.is_authenticated:
        booked_journey_ids = {booking.ride_id for booking in book_ride.query.filter_by(user_id=current_user.id).all()}
    
    for journey in journeys:
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

        # Validation messages for testing 
        if not num_seats:
            return jsonify({"error": "Number of seats is required"}), 400
        try:
            num_seats = int(num_seats)

        except ValueError:
            return jsonify({"error": "Invalid seat number"}), 400

        if num_seats < 1:
            return jsonify({"error": "Invalid seat number"}), 400
        
        if not confirmation_email:
            return jsonify({"error": "Email is required"}), 400
        

        if selected_date not in seat_tracking or seat_tracking[selected_date] < num_seats:
            return jsonify({"error": f"Not enough seats available on {selected_date}"}), 400
        
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

    # get current UK time (timezone-aware)
    london = pytz.timezone("Europe/London")
    aware_now = datetime.now(london)
    now = aware_now.replace(tzinfo=None)

    ride = publish_ride.query.get_or_404(ride_id)
    
    # Load seat data from DB
    db.session.refresh(ride)
    raw_seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}

    # Filter seat_tracking to only include future dates
    seat_tracking = {
        date: seats for date, seats in raw_seat_tracking.items()
        if datetime.strptime(date, "%Y-%m-%d") >= now
    }

    # Also filter available_dates (for calendar display)
    available_dates = [
        date.strip() for date in (ride.recurrence_dates.split(",") if ride.recurrence_dates else [])
        if datetime.strptime(date.strip(), "%Y-%m-%d") >= now
    ]

    seat_data = seat_tracking
    
    if request.method == 'POST':
        num_seats = request.form.get('seats')
        selected_dates = request.form.getlist("selected_dates")
        confirmation_email = request.form.get('email')

        # Validation messages for testing
        if not num_seats or not selected_dates:
            return jsonify({"error": "Required fields are missing"}), 400
        try:
            num_seats = int(num_seats)
        except ValueError:
            return jsonify({"error": "Invalid seat number"}), 400
        if num_seats < 1:
            return jsonify({"error": "Invalid seat number"}), 400

        if not confirmation_email:
            return jsonify({"error": "Email is required"}), 400
        
        if not confirmation_email or not re.match(r"[^@]+@[^@]+\.[^@]+", confirmation_email):
            return jsonify({"error": "Invalid email format"}), 400
        
        # Check seat availability for each date
        for date in selected_dates:
            if seat_tracking.get(date.strip(), 0) < num_seats:
                return jsonify({"error": f"Not enough seats available on {date}"}), 400
                
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
    # get current UK time (timezone-aware)
    london = pytz.timezone("Europe/London")
    aware_now = datetime.now(london)
    now = aware_now.replace(tzinfo=None)

    ride = publish_ride.query.get_or_404(ride_id)
    # ensure recurrence_dates exists and is not empty
    if not ride.recurrence_dates or ride.recurrence_dates.strip() == "":
        return jsonify({"available_dates": []})
    
    commute_time = ride.commute_times.strip() if ride.commute_times else None
    
    # every date after today, and today only if time is after current time
    available_dates = []
    for date_str in ride.recurrence_dates.split(","):
        date_str = date_str.strip()
        try:
            combined_dt = datetime.strptime(f"{date_str} {commute_time}", "%Y-%m-%d %H:%M")
            if combined_dt > now:
                available_dates.append(date_str)
        except ValueError:
            continue
    return jsonify({"available_dates": available_dates})


# Route to get available seats
@app.route('/api/get_available_seats/<int:ride_id>', methods=['GET', 'POST'])
def get_available_seats(ride_id):

    # get current UK time (timezone-aware)
    london = pytz.timezone("Europe/London")
    aware_now = datetime.now(london)
    now = aware_now.replace(tzinfo=None)

    ride = publish_ride.query.get_or_404(ride_id)

    if request.method == 'POST':
        data = request.json  
        selected_dates = data.get("selected_dates", [])
        if isinstance(selected_dates, str):
            selected_dates = [date.strip() for date in selected_dates.split(",") if date.strip()]
    else:
        selected_dates = request.args.get("selected_dates", "").split(",")
    
    try:
        seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
    except json.JSONDecodeError:
        seat_tracking = {}

    # Filter out past dates and only include selected ones
    filtered_seats = {}

    for date in selected_dates:
        if date in seat_tracking:
            try:
                # Combine the date with the earliest commute time (default to 00:00)
                commute_time = ride.commute_times.strip().split(",")[0] if ride.commute_times else "00:00"
                commute_dt = datetime.strptime(f"{date} {commute_time}", "%Y-%m-%d %H:%M")
                if commute_dt >= now:
                    filtered_seats[date] = seat_tracking[date]
            except Exception as e:
                print(f"Failed to parse commute time for {date}: {e}")
    print(filtered_seats)

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


# Route for process payemnt
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
        selected_dates = data.get("selected_dates")
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

            # Validation messages for testing
            if not card_number or not expiry or not cardholder_name:
                return jsonify({"success": False, "message": "Card details missing."}), 400

            if len(card_number) != 16 or not card_number.isdigit():
                return "Invalid card number", 400
            
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
            
            # get current UK time (timezone-aware)
            london = pytz.timezone("Europe/London")
            aware_now = datetime.now(london)
            now = aware_now.replace(tzinfo=None)
            
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
            
            fee_rate = get_platform_fee()
            new_payment = Payment(
                user_id=current_user.id,
                ride_id=ride.id,
                book_ride_id=new_booking.id,
                amount=per_day_price,  
                status="Success",
                timestamp=now,
                platform_fee=fee_rate
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

@app.context_processor
def inject_user():
    return dict(user=current_user)


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


# Route to reset password
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


# Route for the user dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    # Get upcoming and inactive journeys
    booked_rides = book_ride.query.filter_by(user_id=current_user.id).all()
    upcoming_journeys = []
    inactive_journeys = []

    for booking in booked_rides:
        ride = publish_ride.query.get(booking.ride_id)
        if ride:
            is_inactive = booking.status in ["Canceled", "done"]
            price_per_seat = ride.price_per_seat

            # Check for accepted proposal
            latest_accepted_proposal = EditProposal.query.filter_by(
                booking_id=booking.id, status="accepted"
            ).order_by(EditProposal.timestamp.desc()).first()

            # Store changes if any for modal
            edit_details = {
                "pickup": latest_accepted_proposal.proposed_pickup if latest_accepted_proposal else None,
                "time": latest_accepted_proposal.proposed_time if latest_accepted_proposal else None,
                "cost": latest_accepted_proposal.proposed_cost if latest_accepted_proposal else None
            }

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
                "seats_booked": booking.seats_selected,
                "category": ride.category
            }
            
            journey_data["edit_details"] = edit_details

            if is_inactive:
                inactive_journeys.append(journey_data)
            else:
                upcoming_journeys.append(journey_data)
    
    # Sort upcoming journeys by date and time
    upcoming_journeys.sort(key=lambda j: (j["date"], j["time"]))

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
                    {
                        "name": User.query.get(passenger.user_id).username,
                        "email": passenger.confirmation_email,
                        "booking_id": passenger.id,
                        "edit_details": {
                            "pickup": (EditProposal.query
                                .filter_by(booking_id=passenger.id, status="accepted")
                                .order_by(EditProposal.timestamp.desc())
                                .first().proposed_pickup if EditProposal.query.filter_by(booking_id=passenger.id, status="accepted").first() else None),
                            "time": (EditProposal.query
                                .filter_by(booking_id=passenger.id, status="accepted")
                                .order_by(EditProposal.timestamp.desc())
                                .first().proposed_time if EditProposal.query.filter_by(booking_id=passenger.id, status="accepted").first() else None),
                            "cost": (EditProposal.query
                                .filter_by(booking_id=passenger.id, status="accepted")
                                .order_by(EditProposal.timestamp.desc())
                                .first().proposed_cost if EditProposal.query.filter_by(booking_id=passenger.id, status="accepted").first() else None)
                        }
                    }
                    for passenger in book_ride.query.filter_by(ride_id=ride.id).filter(book_ride.status != "Canceled").all()
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

            ride_dates = db.session.query(book_ride.ride_date).filter(
                book_ride.ride_id == ride.id,
                book_ride.status != "Canceled"
            ).distinct().all()
            for date_obj in ride_dates:
                date_str = date_obj[0].strftime('%Y-%m-%d')
                passengers = book_ride.query.filter(
                    book_ride.ride_id == ride.id,
                    book_ride.ride_date == date_obj[0],
                    book_ride.status != "Canceled"
                ).all()
                ride_data["dates"][date_str] = [
                    {
                        "name": User.query.get(passenger.user_id).username,
                        "email": passenger.confirmation_email,
                        "booking_id": passenger.id,
                        "edit_details": {
                            "pickup": (EditProposal.query
                                .filter_by(booking_id=passenger.id, status="accepted")
                                .order_by(EditProposal.timestamp.desc())
                                .first().proposed_pickup if EditProposal.query.filter_by(booking_id=passenger.id, status="accepted").first() else None),
                            "time": (EditProposal.query
                                .filter_by(booking_id=passenger.id, status="accepted")
                                .order_by(EditProposal.timestamp.desc())
                                .first().proposed_time if EditProposal.query.filter_by(booking_id=passenger.id, status="accepted").first() else None),
                            "cost": (EditProposal.query
                                .filter_by(booking_id=passenger.id, status="accepted")
                                .order_by(EditProposal.timestamp.desc())
                                .first().proposed_cost if EditProposal.query.filter_by(booking_id=passenger.id, status="accepted").first() else None)
                        }
                    }
                    for passenger in passengers
                ]
            published_rides["commuting"].append(ride_data)

    # earnings logic
    driver_rides = publish_ride.query.filter_by(driver_id=current_user.id).all()
    driver_ride_ids = [ride.id for ride in driver_rides]

    payments = Payment.query.filter(
        Payment.ride_id.in_(driver_ride_ids),
        Payment.status.in_(["Success", "Partially Refunded"])
    ).all()

    earnings_by_week = defaultdict(float)
    total_earnings = 0.0
    
    for payment in payments:
        fee = payment.platform_fee or 0.005  # fallback if None
        if payment.status == "Success":
            driver_earning = payment.amount * (1 - fee)
        elif payment.status == "Partially Refunded":
            # 75% charged (25% refunded), so driver still gets 75%
            driver_earning = payment.amount * 0.75 * (1 - fee)
        else:
            continue  # skip fully refunded or failed
        week_str = payment.timestamp.strftime("%Y-W%U")
        earnings_by_week[week_str] += driver_earning
        total_earnings += driver_earning

    # Create a list of tuples (week_str, earnings_amount, (start_date, end_date))
    earnings_list = []
    for week_str, amount in sorted(earnings_by_week.items()):
        year, week_num = week_str.split("-W")
        start_date, end_date = get_week_dates(year, week_num)
        date_range_str = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"
        earnings_list.append((week_str, amount, date_range_str))

    return render_template("dashboard.html",
                            user=current_user,
                            upcoming_journeys=upcoming_journeys,
                            inactive_journeys=inactive_journeys,
                            published_rides=published_rides,
                            earnings_data=earnings_list,
                            total_earnings=total_earnings)


# helper function for /dashboard to get week start and end dates
def get_week_dates(year, week_num):
    start = datetime.strptime(f'{year}-W{int(week_num):02d}-1', "%Y-W%W-%w").date()
    end = start + timedelta(days=6)
    return start, end


# Route for deleting a saved card 
@app.route("/delete_saved_card/<int:card_id>", methods=["DELETE"])
@login_required
def delete_saved_card(card_id):
    saved_card = SavedCard.query.get(card_id)

    if not saved_card or saved_card.user_id != current_user.id:
        return jsonify({"success": False, "message": "Card not found or unauthorized"}), 403

    db.session.delete(saved_card)
    db.session.commit()

    return jsonify({"success": True, "message": "Card deleted successfully"})


# Route for cancelling a booking 
@app.route("/cancel_booking/<int:booking_id>", methods=["POST"])
@login_required
def cancel_booking(booking_id):
    booking = book_ride.query.get(booking_id)

    # get current UK time (timezone-aware)
    london = pytz.timezone("Europe/London")
    aware_now = datetime.now(london)
    now = aware_now.replace(tzinfo=None)

    if not booking:
        return jsonify({"success": False, "message": "Booking not found"}), 404

    ride = publish_ride.query.get(booking.ride_id)

    # Find associated payment
    payment = Payment.query.filter_by(book_ride_id=booking.id).first()

    ride_time = booking.ride_date
    print(f"ride time is {ride_time} and now is {now}")
    time_difference = (ride_time - now).total_seconds() / 60  # Convert to minutes

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
    booking.cancellation_timestamp = now

    # Restore seats for the canceled date
    seat_tracking = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
    selected_date_str = booking.ride_date.strftime("%Y-%m-%d")

    if selected_date_str in seat_tracking:
        seat_tracking[selected_date_str] += booking.seats_selected  # Restore the canceled seats

    ride.available_seats_per_date = json.dumps(seat_tracking)
    db.session.commit()

    return jsonify({"success": True, "message": f"Booking successfully canceled. Refund: £{refund_amount}"}), 200


# Route for searching a journey
@app.route('/filter_journeys', methods=['GET'])
def filter_journeys():
    from_location = request.args.get("from", "").strip()
    to_location = request.args.get("to", "").strip()
    date = request.args.get("date", "").strip()
    category = request.args.get("category", "").strip()
    max_price = request.args.get("price", "").strip()
    passengers = int(request.args.get("passengers", 1))

    query_filters = []

    if from_location:
        query_filters.append(publish_ride.from_location.ilike(f"%{from_location}%"))
    if to_location:
        query_filters.append(publish_ride.to_location.ilike(f"%{to_location}%"))
    if max_price:
        query_filters.append(publish_ride.price_per_seat <= float(max_price))

    journeys = []

    # One-Time Rides Query
    if not category or category == "one-time":
        one_time_rides = publish_ride.query.filter(
            *query_filters,
            publish_ride.category == "one-time",
            publish_ride.is_available == True,
            func.date(publish_ride.date_time) == date if date else True
        ).all()

        for ride in one_time_rides:
            seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
            available_seats = seat_data.get(date, 0) if date else max(seat_data.values(), default=0)
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
                    "user_has_booked": False,
                    "recurrence_dates": None,
                    "commute_times": None
                })

    # Commuting Rides Query
    if not category or category == "commuting":
        commuting_rides = publish_ride.query.filter(
            *query_filters,
            publish_ride.category == "commuting",
            publish_ride.is_available == True,
            publish_ride.recurrence_dates.ilike(f"%{date}%") if date else True
        ).all()

        for ride in commuting_rides:
            seat_data = json.loads(ride.available_seats_per_date) if ride.available_seats_per_date else {}
            available_seats = seat_data.get(date, 0) if date else max(seat_data.values(), default=0)
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


# Store live locations in memory
live_locations = {}

@app.route('/view_pickup/<int:ride_id>', methods=['GET'])
@login_required
def view_pickup(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    driver = User.query.get(ride.driver_id)

    booking = book_ride.query.filter_by(ride_id=ride_id, user_id=current_user.id).first()
    is_passenger = booking is not None
    is_driver = (ride.driver_id == current_user.id)

    passenger = None
    if is_passenger:
        passenger = User.query.get(booking.user_id)

    if is_passenger and not is_driver:
        ride_date = booking.ride_date.strftime("%Y-%m-%d") if booking.ride_date else "N/A"
        return render_template("pickup_passenger.html", ride_id=ride_id, ride=ride,
                               driver_name=driver.username if driver else "Unknown",
                               passenger_name=passenger.username if passenger else None,
                               ride_status=booking.status, ride_date=ride_date)

    elif is_driver and not is_passenger:
        passenger_bookings = book_ride.query.filter(book_ride.ride_id == ride_id, not_(book_ride.status == 'Canceled')).all()
        passenger_names = [User.query.get(pb.user_id).username for pb in passenger_bookings]

        # Default to "Booked"
        ride_status = "Booked"

        # Safely prioritize the most accurate status
        for pb in passenger_bookings:
            if pb.status == "done":
                ride_status = "done"
                break
            elif pb.status == "ongoing" and ride_status != "done":
                ride_status = "ongoing"
                # but only if no "done" detected

        print("Final ride_status being passed:", ride_status)

        # To extract date for one-time
        ride_date = ride.date_time.strftime("%Y-%m-%d") if ride.date_time else "N/A"

        return render_template("pickup_driver.html", ride_id=ride_id, ride=ride,
                            ride_status=ride_status,
                            driver_name=driver.username if driver else "Unknown",
                            passenger_names=passenger_names,  ride_date=ride_date)

    elif is_passenger and is_driver:
        # Edge case: Treat it like a driver only since a driver wouldn’t need to track themselves
        passenger_bookings = book_ride.query.filter(book_ride.ride_id == ride_id, not_(book_ride.status == 'Canceled')).all()
        passenger_names = [User.query.get(pb.user_id).username for pb in passenger_bookings]
        
        ride_status = "Booked"
        for pb in passenger_bookings:
            if pb.status == "done":
                ride_status = "done"
                break
            elif pb.status == "ongoing":
                ride_status = "ongoing"

        ride_date = booking.ride_date.strftime("%Y-%m-%d") if booking.ride_date else "N/A"

        return render_template("pickup_driver.html", ride_id=ride_id, ride=ride,
                            ride_status=ride_status,
                            driver_name=driver.username if driver else "Unknown",
                            passenger_names=passenger_names,
                            ride_date=ride_date)

    else:
        return "<h3><strong>Unauthorized access to this ride</strong></h3>", 403


# API to get pickup location for a ride
@app.route('/api/get_pickup_location/<int:ride_id>', methods=['GET'])
@login_required
def get_pickup_location(ride_id):
    ride = publish_ride.query.get_or_404(ride_id)
    return jsonify({"from_location": ride.from_location}), 200


# Passenger Updates Their Location
@app.route('/api/track_passenger_location', methods=['POST'])
@login_required
def track_passenger_location():
    data = request.json
    ride_id = data.get("ride_id")
    lat = data.get("latitude")
    lon = data.get("longitude")
    ride_date = data.get("ride_date")  # For commuting rides
    user_id = current_user.id          # Get current user ID

    if not ride_id or not lat or not lon:
        return jsonify({"error": "Invalid data"}), 400

    if ride_date:
        key = f"passenger_{ride_id}_{ride_date}_{user_id}"
    else:
        key = f"passenger_{ride_id}_{user_id}"

    live_locations[key] = (lat, lon)

    return jsonify({"message": "Passenger location updated"}), 200


# Driver Updates Their Location
@app.route('/api/track_driver_location', methods=['POST'])
@login_required
def track_driver_location():
    data = request.json
    ride_id = data.get("ride_id")
    lat = data.get("latitude")
    lon = data.get("longitude")
    ride_date = data.get("ride_date")  

    if not ride_id or not lat or not lon:
        return jsonify({"error": "Invalid data"}), 400

    key = f"driver_{ride_id}_{ride_date}" if ride_date else f"driver_{ride_id}"
    live_locations[key] = (lat, lon)

    return jsonify({"message": "Driver location updated"}), 200


@app.route('/api/get_live_locations/<int:ride_id>', methods=['GET'])
@login_required
def get_live_locations(ride_id):
    driver_loc = live_locations.get(f"driver_{ride_id}")

    # Collect all passenger locations for one-time ride
    passenger_locs = {}
    for key, value in live_locations.items():
        if key.startswith(f"passenger_{ride_id}_") or key == f"passenger_{ride_id}":
            # Extract user_id or username from key
            parts = key.split("_")
            if len(parts) == 3:
                user_id = parts[2]
                user = User.query.get(int(user_id))
                if user:
                    passenger_locs[user.username] = value
            elif len(parts) == 2:
                passenger_locs[current_user.username] = value

    # Check if they are within 100 meters (only if there's one passenger)
    nearby = False
    if len(passenger_locs) == 1 and driver_loc:
        only_passenger_coords = list(passenger_locs.values())[0]
        distance = geodesic(only_passenger_coords, driver_loc).meters
        nearby = distance <= 100

    return jsonify({
        "passenger": passenger_locs,
        "driver": driver_loc,
        "nearby": nearby
    })
    

# API to track if passenger reached pickup point
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


# Helper Function to Get Coordinates (Uses OpenStreetMap Nominatim)
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


# Route for Journey Status
@app.route("/api/start_journey", methods=["POST"])
@login_required
def start_journey():
    data = request.get_json()
    ride_id = data.get("ride_id")
    ride_date_str = data.get("ride_date")

    if not ride_id:
        return jsonify({"error": "Missing ride ID"}), 400

    ride = publish_ride.query.get_or_404(ride_id)

    if ride.driver_id != current_user.id:
        return jsonify({"error": "Only the driver can start the journey"}), 403

    # One-time ride: no date needed
    if ride.category == "one-time":
        bookings = book_ride.query.filter_by(
            ride_id=ride_id
        ).all()
    else:
        # Commuting ride: ride_date is required
        if not ride_date_str:
            return jsonify({"error": "Missing ride date for commuting ride"}), 400

        try:
            ride_date = datetime.strptime(ride_date_str, "%Y-%m-%d").date()
        except:
            return jsonify({"error": "Invalid date format"}), 400

        bookings = book_ride.query.filter(
            book_ride.ride_id == ride_id,
            db.func.date(book_ride.ride_date) == ride_date
        ).all()

    for booking in bookings:
        booking.status = "ongoing"

    db.session.commit()
    return jsonify({"message": "Journey started!"}), 200


@app.route('/api/update_passenger_pickup_location', methods=['POST'])
@login_required
def update_passenger_pickup_location():
    data = request.json
    ride_id = data.get('ride_id')
    lat = data.get('latitude')
    lon = data.get('longitude')

    # Validate inputs
    if ride_id is None or lat is None or lon is None:
        return jsonify({"error": "Missing ride_id or coordinates."}), 400

    # Update the live location dictionary directly
    ride_date = data.get("ride_date")
    key = f"passenger_{ride_id}_{ride_date}" if ride_date else f"passenger_{ride_id}"
    live_locations[key] = (lat, lon)
    return jsonify({"message": "Pickup location updated."}), 200


# Route for the commuting journeys
@app.route('/view_pickup_commute/<int:ride_id>/<date>', methods=['GET'])
@login_required
def view_pickup_commute(ride_id, date):
    ride = publish_ride.query.get_or_404(ride_id)
    driver = User.query.get(ride.driver_id)

    # Convert date string to datetime.date
    try:
        ride_date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return "<h3><strong>Invalid date format</strong></h3>", 400

    # Check if user is a passenger for this date
    booking = book_ride.query.filter(
        book_ride.ride_id == ride_id,
        book_ride.user_id == current_user.id,
        db.func.date(book_ride.ride_date) == ride_date_obj
    ).first()

    is_passenger = booking is not None
    is_driver = ride.driver_id == current_user.id

    # Detect ride status
    if is_driver:
        # For drivers: determine status based on bookings
        bookings = book_ride.query.filter(
            book_ride.ride_id == ride_id,
            db.func.date(book_ride.ride_date) == ride_date_obj
        ).all()

        ride_status = "Booked"  # default status
        for b in bookings:
            if b.status == "ongoing":
                ride_status = "ongoing"
                break
            elif b.status == "done":
                ride_status = "done"
    elif is_passenger:
        ride_status = booking.status if booking else "Booked" # directly from passenger's booking
    else:
        return "<h3><strong>Unauthorized access to this ride</strong></h3>", 403

    # For displaying multiple passenger names (for driver view)
    passenger_names = []
    if is_driver:
        bookings = book_ride.query.filter(
            book_ride.ride_id == ride_id,
            db.func.date(book_ride.ride_date) == ride_date_obj,
            not_(book_ride.status == "Canceled")
        ).all()
        passenger_names = [User.query.get(b.user_id).username for b in bookings]

    template = "pickup_driver.html" if is_driver else "pickup_passenger.html"
    return render_template(
        template,
        ride_id=ride_id,
        ride_date=date,
        ride=ride,
        driver_name=driver.username,
        passenger_names=passenger_names,
        ride_status=ride_status  
    )


@app.route('/api/get_commute_live_locations/<int:ride_id>/<string:ride_date>', methods=['GET'])
@login_required
def get_commute_live_locations(ride_id, ride_date):
    from geopy.distance import geodesic

    passenger_loc = {}

    for key, loc in live_locations.items():
        if key.startswith(f"passenger_{ride_id}_{ride_date}_"):
            user_id = key.split("_")[-1]
            user = User.query.get(int(user_id))
            username = user.username if user else f"Passenger_{user_id}"
            passenger_loc[username] = loc

    driver_key = f"driver_{ride_id}_{ride_date}"
    driver_loc = live_locations.get(driver_key)

    if not passenger_loc and not driver_loc:
        return jsonify({"error": "No location data available"}), 404

    # Check if any passenger is nearby
    nearby = False
    if driver_loc:
        for passenger_id, loc in passenger_loc.items():
            if loc:
                distance = geodesic(loc, driver_loc).meters
                if distance <= 100:
                    nearby = True
                    break

    return jsonify({
        "passenger": passenger_loc,  # now a dict of username -> location
        "driver": driver_loc,
        "nearby": nearby
    })


# ID 17: chat option between driver and passenger
# route to check if the user is not logged in for chat polling
@app.route('/api/is_logged_in')
def is_logged_in():
    return jsonify({"logged_in": current_user.is_authenticated})


# Route to view the chat
@app.route('/chat/<int:booking_id>')
@login_required
def chat_view(booking_id):
    booking = book_ride.query.get_or_404(booking_id)
    if current_user.id not in [booking.user_id, booking.ride.driver_id]:
        return "Unauthorized", 403
    return render_template("chat.html", booking=booking)


# Route to send message 
@app.route('/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    booking_id = data.get("booking_id")
    message = data.get("message")

    if not message:
        return jsonify({"error": "Empty message"}), 400

    booking = book_ride.query.get_or_404(booking_id)
    if current_user.id not in [booking.user_id, booking.ride.driver_id]:
        return jsonify({"error": "Unauthorized"}), 403

    new_msg = ChatMessage(
        booking_id=booking_id,
        sender_username=current_user.username,
        message=message
    )
    db.session.add(new_msg)
    db.session.commit()

    return jsonify(new_msg.to_dict()), 200


# Route to get messages 
@app.route('/get_messages/<int:booking_id>')
@login_required
def get_messages(booking_id):
    booking = book_ride.query.get_or_404(booking_id)
    if current_user.id not in [booking.user_id, booking.ride.driver_id]:
        return jsonify({"error": "Unauthorized"}), 403

    messages = ChatMessage.query.filter_by(booking_id=booking_id).order_by(ChatMessage.timestamp).all()
    proposals = EditProposal.query.filter_by(booking_id=booking_id).order_by(EditProposal.timestamp).all()

    combined = []

    for msg in messages:
        combined.append({
            "type": "message",
            "id": msg.id,
            "sender": msg.sender_username,
            "message": msg.message,
            "timestamp": msg.timestamp.strftime('%Y-%m-%d %H:%M')
        })

    for prop in proposals:
        combined.append({
            "type": "proposal",
            "id": prop.id,
            "sender": prop.sender,
            "pickup": prop.proposed_pickup,
            "time": prop.proposed_time,
            "cost": prop.proposed_cost,
            "status": prop.status,
            "timestamp": prop.timestamp.strftime('%Y-%m-%d %H:%M')
        })

    # Sort by timestamp (assuming both ChatMessage and Proposal have timestamp)
    combined.sort(key=lambda x: x["timestamp"])

    return jsonify(combined)


# Route to check for new messages
@app.route('/check_new_messages')
@login_required
def check_new_messages():
    user_bookings = book_ride.query.filter(
        (book_ride.user_id == current_user.id) |
        (book_ride.ride.has(driver_id=current_user.id))
    ).with_entities(book_ride.id).all()

    booking_ids = [b.id for b in user_bookings]

    recent_messages = ChatMessage.query.filter(
        ChatMessage.booking_id.in_(booking_ids),
        ChatMessage.sender_username != current_user.username,
        ChatMessage.seen_by_receiver == False
    ).order_by(ChatMessage.timestamp.desc()).limit(5).all()

    if not recent_messages:
        return jsonify({"new": False})

    messages_data = [
        {
            "sender": msg.sender_username,
            "booking_id": msg.booking_id,
            "message_id": msg.id
        } for msg in recent_messages
    ]

    return jsonify({"new": True, "messages": messages_data})


# Route to check if the messae is seen
@app.route('/mark_message_seen/<int:message_id>', methods=['POST'])
@login_required
def mark_message_seen(message_id):
    msg = ChatMessage.query.get_or_404(message_id)
    if current_user.username != msg.sender_username:  # Only receiver can mark it seen
        msg.seen_by_receiver = True
        db.session.commit()
    return jsonify(success=True)


# Route to handle edit proposals
@app.route('/propose_edit', methods=['POST'])
@login_required
def propose_edit():
    data = request.get_json()
    booking_id = data.get("booking_id")
    pickup = data.get("pickup")
    time = data.get("time")
    cost = data.get("cost")

    booking = book_ride.query.get_or_404(booking_id)

    if current_user.id not in [booking.user_id, booking.ride.driver_id]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    proposal = EditProposal(
        booking_id=booking_id,
        sender=current_user.username,
        proposed_pickup=pickup or None,
        proposed_time=time or None,
        proposed_cost=float(cost) if cost else None,
    )

    db.session.add(proposal)
    db.session.commit()

    return jsonify({"success": True})


# Route to respond to the proposals 
@app.route('/respond_proposal', methods=['POST'])
@login_required
def respond_proposal():
    data = request.get_json()
    proposal_id = data.get("proposal_id")
    action = data.get("action")  # accept or reject

    proposal = EditProposal.query.get_or_404(proposal_id)
    booking = book_ride.query.get_or_404(proposal.booking_id)

    # Only the other party can respond
    if current_user.username == proposal.sender:
        return jsonify({"success": False, "error": "Cannot respond to your own proposal"}), 403

    if action == "accept":
        proposal.status = "accepted"
        if proposal.proposed_pickup:
            booking.pickup_point = proposal.proposed_pickup
        if proposal.proposed_time:
            booking.time = proposal.proposed_time
        if proposal.proposed_cost is not None:
            booking.cost = proposal.proposed_cost
    elif action == "reject":
        proposal.status = "rejected"
    else:
        return jsonify({"success": False, "error": "Invalid action"}), 400

    db.session.commit()
    return jsonify({"success": True})


# Routes for management view
@app.cli.command("make-manager")
def make_manager():
    email = input("Enter user email to promote: ")
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_manager = True
            db.session.commit()
            print(f"{user.email} is now a manager ")
        else:
            print("User not found")


# Route for the manager dashboard
@app.route('/manager/dashboard')
@login_required
@manager_required
def manager_dashboard():
    total_bookings = book_ride.query.count()
    total_rides_published = publish_ride.query.count()

    # Total platform earnings
    total_revenue = db.session.query(
        func.sum(Payment.amount * 0.005)
    ).filter_by(status="Success", refunded=False).scalar() or 0

    # Weekly earnings logic
    payments = Payment.query.filter_by(status="Success", refunded=False).all()
    weekly_earnings = defaultdict(float)

    for payment in payments:
        fee = payment.amount * 0.005
        week_str = payment.timestamp.strftime("%Y-W%U")
        weekly_earnings[week_str] += fee

    # Format for table
    weekly_earnings_list = []
    for week_str, amount in sorted(weekly_earnings.items()):
        year, week_num = week_str.split("-W")
        start_date, end_date = get_week_dates(year, week_num)
        date_range = f"{start_date.strftime('%d %b %Y')} - {end_date.strftime('%d %b %Y')}"
        weekly_earnings_list.append((week_str, round(amount, 2), date_range))

    # Extract for chart.js
    labels = [entry[0] for entry in weekly_earnings_list]
    values = [entry[1] for entry in weekly_earnings_list]
    date_ranges = [entry[2] for entry in weekly_earnings_list]

    return render_template(
        "management/manager_dashboard.html",
        total_bookings=total_bookings,
        total_rides_published=total_rides_published,
        total_revenue=round(total_revenue, 2),
        weekly_earnings=weekly_earnings_list,
        earnings_chart_labels=labels,
        earnings_chart_values=values,
        earnings_chart_dates=date_ranges
    )


# Route to configure fee 
@app.route("/manager/configure_fee", methods=["GET", "POST"])
@login_required
@manager_required
def configure_fee():
    setting = PlatformSetting.query.filter_by(key="platform_fee").first()

    if request.method == "POST":
        new_value = request.form.get("fee")
        try:
            new_fee = float(new_value)
            if not 0 <= new_fee <= 1:
                return jsonify({"success": False, "message": "Fee must be between 0 and 1."}), 400
            else:
                if setting:
                    setting.value = str(new_fee)
                else:
                    setting = PlatformSetting(key="platform_fee", value=str(new_fee))
                    db.session.add(setting)
                db.session.commit()
                return jsonify({"success": True, "message": "Platform fee updated successfully."})
        except ValueError:
            return jsonify({"success": False, "message": "Invalid input. Please enter a number."}), 400

    # If GET request
    current_fee = float(setting.value) if setting else 0.005
    return render_template("management/configure_fee.html", current_fee=current_fee)


# Booking Rating Routes
@app.route("/api/finish_journey", methods=["POST"])
@login_required
def finish_journey():
    data = request.get_json()
    ride_id = data.get("ride_id")
    ride_date_str = data.get("ride_date")  # Optional for one-time

    if not ride_id:
        return jsonify({"error": "Missing ride ID"}), 400

    ride = publish_ride.query.get_or_404(ride_id)

    if ride.driver_id != current_user.id:
        return jsonify({"error": "Only the driver can finish the journey"}), 403

    if ride.category == "commuting":
        if not ride_date_str:
            return jsonify({"error": "Missing ride date for commuting ride"}), 400
        try:
            ride_date = datetime.strptime(ride_date_str, "%Y-%m-%d").date()
        except:
            return jsonify({"error": "Invalid date format"}), 400

        # Update only bookings for this date
        bookings = book_ride.query.filter(
            book_ride.ride_id == ride_id,
            db.func.date(book_ride.ride_date) == ride_date
        ).all()
    else:
        bookings = book_ride.query.filter_by(ride_id=ride_id).all()

    for booking in bookings:
        booking.status = "done"

    db.session.commit()
    return jsonify({"message": "Journey marked as finished."}), 200


# Route to submit rating
@app.route('/api/submit_rating', methods=['POST'])
@login_required
def submit_rating():
    try:
        data = request.json
        print("Incoming rating submission:", data)

        ride_id = data.get("ride_id")
        rating = data.get("rating")
        ride_date_str = data.get("ride_date")  # for commuting

        if ride_id is None or rating is None:
            return jsonify({"error": "Missing ride_id or rating"}), 400

        ride = publish_ride.query.get_or_404(ride_id)
        user_id = current_user.id

        # If commuting, parse ride_date and use func.date to filter correctly
        if ride.category == "commuting":
            if not ride_date_str:
                return jsonify({"error": "Missing ride_date for commuting ride"}), 400
            ride_date = datetime.strptime(ride_date_str, "%Y-%m-%d").date()
            booking_query = book_ride.query.filter(
                and_(
                    book_ride.user_id == user_id,
                    book_ride.ride_id == ride_id,
                    func.date(book_ride.ride_date) == ride_date
                )
            )
        else:
            booking_query = book_ride.query.filter_by(user_id=user_id, ride_id=ride_id)

        booking = booking_query.first()
        print("Booking:", booking)

        # Check if already rated
        if ride.category == "commuting":
            existing = RideRating.query.filter_by(
                ride_id=ride_id,
                passenger_id=user_id,
                ride_date=ride_date
            ).first()
        else:
            existing = RideRating.query.filter_by(
                ride_id=ride_id,
                passenger_id=user_id
            ).first()

        if existing:
            print("You already rated this ride.")
            return jsonify({
                "message": "You already rated this ride.",
                "redirect_url": url_for("dashboard")
            })


        # Add new rating
        rating_entry = RideRating(
            ride_id=ride_id,
            passenger_id=user_id,
            rating=rating
        )
        if ride.category == "commuting":
            rating_entry.ride_date = ride_date

        db.session.add(rating_entry)

        if booking:
            print("Booking found. Marking as done.")
            booking.status = "done"
        else:
            print("No booking found to mark as done.")

        db.session.commit()
        return jsonify({"message": "Rating submitted successfully!", "redirect_url": url_for("dashboard")})

    except Exception as e:
        return jsonify({"error": "Server error occurred."}), 500


# Route to check the ride status (booked, ongoing and done)
@app.route('/api/ride_status', methods=['POST'])
@login_required
def check_ride_status():
    data = request.get_json()
    ride_id = data.get('ride_id')
    ride_date_str = data.get('ride_date')
    
    if not ride_id:
        return jsonify({'error': 'Missing ride_id'}), 400

    ride = publish_ride.query.get_or_404(ride_id)

    if ride.category == "commuting":
        if not ride_date_str:
            return jsonify({'error': 'Missing ride_date for commuting'}), 400
        ride_date = datetime.strptime(ride_date_str, '%Y-%m-%d').date()
        booking = book_ride.query.filter_by(user_id=current_user.id, ride_id=ride_id).filter(db.func.date(book_ride.ride_date) == ride_date).first()
    else:
        booking = book_ride.query.filter_by(user_id=current_user.id, ride_id=ride_id).first()

    if not booking:
        return jsonify({'status': 'none'}), 200

    return jsonify({'status': booking.status}), 200
