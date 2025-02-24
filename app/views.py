import os
from flask import render_template, redirect, url_for, flash, request
from werkzeug.utils import secure_filename
from app import app, db
from app.models import User, publish_ride, view_ride, book_ride
from flask_login import current_user, login_required

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/view_journeys')
def view_journeys():
    journeys = view_ride.query.all()  # Fetch all available journeys
    return render_template('view_journeys.html', journeys=journeys)

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

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
        car_type = request.form['car_type']
        driver_name = request.form['driver_name']

        # Handling file upload
        car_image = request.files['car_image']
        image_filename = None  # Default in case no image is uploaded

        if car_image and allowed_file(car_image.filename):
            filename = secure_filename(car_image.filename)
            image_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            car_image.save(image_filename)  # Save image to uploads folder
        else:
            flash("Invalid image format! Please upload PNG, JPG, JPEG, or GIF.", "danger")
            return redirect(url_for('publish_ride'))

        # Create a new ride entry
        new_ride = publish_ride(
            driver_id=current_user.id,
            from_location=from_location,
            to_location=to_location,
            date_time=date_time,
            available_seats=available_seats,
            price_per_seat=price_per_seat,
            category=category,
            car_type=car_type,
            driver_name=driver_name,
            car_image=image_filename,  # Save the file path
            is_available=True
        )

        # Add the new ride to the database
        db.session.add(new_ride)
        db.session.commit()

        flash("Your ride has been published successfully!", "success")
        return redirect(url_for('home'))  # Redirect to homepage after publishing

    return render_template('publish_ride.html')
