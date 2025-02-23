from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

app = Flask(__name__)
app.config.from_object('config')

# Initialize extensions (without tying to app immediately)
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Bind app to extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)

login_manager.login_view = "login"  # Redirects to login page if user isn't logged in

# Import models and views inside app context
with app.app_context():
    from app import models, views
    db.create_all()  # Ensure tables exist

