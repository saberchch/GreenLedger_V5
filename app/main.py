"""Main routes for the application."""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask import send_file

bp = Blueprint('main', __name__)


@bp.route('/orgs/search')
def orgs_search():
    """Public JSON endpoint: search active organizations by name for worker registration."""
    from app.models.organization import Organization, OrganizationStatus
    q = request.args.get('q', '').strip()
    if not q or len(q) < 2:
        return jsonify([])
    results = Organization.query.filter(
        Organization.name.ilike(f'%{q}%'),
        Organization.status == OrganizationStatus.ACTIVE
    ).limit(10).all()
    return jsonify([{'id': o.id, 'name': o.name, 'industry': o.industry or ''} for o in results])




@bp.route('/')
def index():
    """Landing page route."""
    return render_template('pages/landing.html')


@bp.route('/request-access', methods=['GET', 'POST'])
def request_access():
    """Request access page route."""
    if request.method == 'POST':
        # TODO: Implement actual access request logic
        # For now, just flash a message and redirect
        flash('Access request submitted successfully! You will receive an email within 24 hours.', 'success')
        return redirect(url_for('main.index'))
    
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


@bp.route('/explorer')
def explorer():
    """Explorer page route."""
    return render_template('pages/explorer.html')



@bp.route("/whitepapers/security")
def security_whitepaper():
    return send_file(
        "docs/whitepapers/security/GreenLedger_Whitepaper_V1.pdf",
        mimetype="application/pdf",
        as_attachment=False  # opens in browser
    )
