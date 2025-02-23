from flask import Flask, render_template
from app import app, db
from app.models import User, publish_ride, view_ride, book_ride

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/view_journeys')
def view_journeys():
    journeys = view_ride.query.all()  # Fetch all available journeys
    return render_template('view_journeys.html', journeys=journeys)
