"""Main routes for the application."""

from flask import Blueprint, render_template, request, flash, redirect, url_for

bp = Blueprint('main', __name__)


@bp.route('/')
def landing():
    """Landing page route."""
    return render_template('pages/landing.html')


@bp.route('/request-access', methods=['GET', 'POST'])
def request_access():
    """Request access page route."""
    if request.method == 'POST':
        # TODO: Implement actual access request logic
        # For now, just flash a message and redirect
        flash('Access request submitted successfully! You will receive an email within 24 hours.', 'success')
        return redirect(url_for('main.landing'))
    
    return render_template('pages/request_access.html')


@bp.route('/modules')
def modules():
    """Modules page route."""
    return render_template('pages/modules.html')


@bp.route('/security')
def security():
    """Security page route."""
    return render_template('pages/security.html')


@bp.route('/how-it-works')
def how_it_works():
    """How it works page route."""
    return render_template('pages/how_it_works.html')
