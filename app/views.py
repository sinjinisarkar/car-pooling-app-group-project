from flask import render_template, redirect, url_for, flash, request
from app import app, db
from app.models import User, publish_ride
from flask_login import current_user, login_required

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/view_journeys')
def view_journeys():
    journeys = view_ride.query.all()  # Fetch all available journeys
    return render_template('view_journeys.html', journeys=journeys)

@app.route('/publish_ride', methods=['GET', 'POST'])
def publish_ride():
    if request.method == 'POST':
        # Get form data from the request
        from_location = request.form['from_location']
        to_location = request.form['to_location']
        date_time = request.form['date_time']
        available_seats = request.form['available_seats']
        price_per_seat = request.form['price_per_seat']
        category = request.form['category']

        # Create a new ride entry
        new_ride = publish_ride(
            driver_id=current_user.id,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats=available_seats,
            price_per_seat=price_per_seat,
            category=category,
            is_available=True
        )
        
        # Add the new ride to the database
        db.session.add(new_ride)
        db.session.commit()

        flash("Your ride has been published!", "success")
        return redirect(url_for('home'))  # Redirect to homepage after publishing

    return render_template('publish_ride.html')
