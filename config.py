import os
from cryptography.fernet import Fernet

# Generate a key once and store it securely (e.g., in an environment variable)
ENCRYPTION_KEY = Fernet.generate_key().decode()  # Replace this with a securely stored key

basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = True

WTF_CSRF_ENABLED = True
SECRET_KEY = 'a-very-secret-secret'

# Email Configuration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USE_SSL = False
MAIL_USERNAME = 'no.reply.catchmyride@gmail.com'
MAIL_PASSWORD = 'yzvr gzdc tywg kysg' # App Password
MAIL_DEFAULT_SENDER = 'no.reply.catchmyride@gmail.com'
