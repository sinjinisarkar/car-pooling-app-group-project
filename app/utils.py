from flask import redirect, url_for, flash
from flask_login import current_user
from functools import wraps
from app.models import PlatformSetting


def manager_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not current_user.is_manager:
            flash("Access restricted to managers only.", "warning")
            return redirect(url_for('home'))  # Or wherever is appropriate
        return f(*args, **kwargs)
    return decorated_function


def get_platform_fee(default=0.005):
    setting = PlatformSetting.query.filter_by(key="platform_fee").first()
    return float(setting.value) if setting else default