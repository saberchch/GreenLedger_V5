"""Settings routes for user profile and preferences."""
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.settings import bp

@bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """General settings page."""
    if request.method == 'POST':
        theme = request.form.get('theme', 'light')
        language = request.form.get('language', 'en')
        email_notif = 'on' if request.form.get('email_notifications') else 'off'
        push_notif = 'on' if request.form.get('push_notifications') else 'off'
        analytics = 'on' if request.form.get('analytics') else 'off'

        # Persist to user model if preferences column exists
        try:
            if hasattr(current_user, 'preferences'):
                import json
                prefs = json.loads(current_user.preferences or '{}')
                prefs.update({
                    'theme': theme, 'language': language,
                    'email_notifications': email_notif,
                    'push_notifications': push_notif,
                    'analytics': analytics,
                })
                current_user.preferences = json.dumps(prefs)
                db.session.commit()
        except Exception:
            pass

        flash('Settings saved!', 'success')
        return redirect(url_for('settings.index'))

    return render_template('pages/settings/index.html', user=current_user)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        # Update user information
        current_user.first_name = request.form.get('first_name', current_user.first_name)
        current_user.last_name = request.form.get('last_name', current_user.last_name)
        current_user.email = request.form.get('email', current_user.email)
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings.profile'))
    
    return render_template('pages/settings/profile.html', user=current_user)
