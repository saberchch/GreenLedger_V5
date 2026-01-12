"""Authentication routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route."""
    if request.method == 'POST':
        # TODO: Implement actual authentication logic
        # For now, just redirect to dashboard (will be implemented later)
        flash('Login functionality will be implemented soon', 'info')
        return redirect(url_for('main.landing'))
    
    return render_template('pages/login.html')
