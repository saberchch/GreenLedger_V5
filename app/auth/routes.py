"""Authentication routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.user import User
from app.models.organization import Organization
from app.models.role import Role
from app.utils.redirects import redirect_to_dashboard

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page route."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('pages/login.html')

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash('Invalid email or password', 'error')
            return render_template('pages/login.html')

        if user.status != 'active':
            flash('Your account is suspended. Please contact support.', 'error')
            return render_template('pages/login.html')

        login_user(user, remember=True)
        flash(f'Welcome back, {user.first_name or user.email}!', 'success')

        return redirect_to_dashboard(user)

    return render_template('pages/login.html')


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page route."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        organization_name = request.form.get('organization_name', '').strip()

        if not email or not password:
            flash('Email and password are required', 'error')
            return render_template('pages/register.html')

        if password != password_confirm:
            flash('Passwords do not match', 'error')
            return render_template('pages/register.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('pages/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('pages/register.html')

        organization = None
        if organization_name:
            organization = Organization.query.filter_by(name=organization_name).first()
            if not organization:
                organization = Organization(
                    name=organization_name,
                    legal_name=organization_name,
                    is_active=True
                )
                db.session.add(organization)
                db.session.flush()

        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            status='active',
            organization_id=organization.id if organization else None
        )

        db.session.add(user)
        db.session.flush()

        # Default role for MVP
        viewer_role = Role.query.filter_by(name='worker').first()
        if viewer_role:
            from app.models.user_role import user_roles
            db.session.execute(
                user_roles.insert().values(
                    user_id=user.id,
                    role_id=viewer_role.id,
                    organization_id=organization.id if organization else None
                )
            )

        db.session.commit()

        login_user(user, remember=True)
        flash('Registration successful! Welcome to GreenLedger.', 'success')

        return redirect_to_dashboard(user)

    return render_template('pages/register.html')


@bp.route('/register-company', methods=['GET', 'POST'])
def register_company():
    """Company Registration page route."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        industry = request.form.get('industry', '').strip()

        if not email or not password or not company_name:
            flash('All fields are required', 'error')
            return render_template('pages/register_company.html')

        if password != password_confirm:
            flash('Passwords do not match', 'error')
            return render_template('pages/register_company.html')

        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return render_template('pages/register_company.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('pages/register_company.html')

        # Create Organization (Pending)
        from app.models.organization import OrganizationStatus
        
        organization = Organization.query.filter_by(name=company_name).first()
        if organization:
             flash('Organization name already taken', 'error')
             return render_template('pages/register_company.html')

        organization = Organization(
            name=company_name,
            legal_name=company_name,
            industry=industry,
            is_active=True, # Active but status is pending
            status=OrganizationStatus.PENDING
        )
        db.session.add(organization)
        db.session.flush()

        # Create Admin User
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            status='active',
            organization_id=organization.id
        )

        db.session.add(user)
        db.session.flush()

        # Assign Admin Role
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            from app.models.user_role import user_roles
            db.session.execute(
                user_roles.insert().values(
                    user_id=user.id,
                    role_id=admin_role.id,
                    organization_id=organization.id
                )
            )

        db.session.commit()

        flash('Application submitted! Please wait for approval.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('pages/register_company.html')


@bp.route('/logout')
@login_required
def logout():
    """Logout route."""
    logout_user()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('main.landing'))
