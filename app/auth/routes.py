"""Authentication routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash, generate_password_hash
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.extensions import db, csrf
from app.models.user import User, UserRole
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
        
        # Validate & capture selected role
        selected_role = request.form.get('role', 'worker').strip().lower()
        allowed_roles = {'worker', 'auditor', 'viewer'}
        if selected_role not in allowed_roles:
            selected_role = 'worker'

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

        # Link worker to a selected existing organization
        from app.models.organization import Organization, OrganizationStatus
        organization = None
        if selected_role == 'worker':
            org_id = request.form.get('organization_id', '').strip()
            if not org_id:
                flash('Workers must select a registered organization to join.', 'error')
                return render_template('pages/register.html')
            organization = Organization.query.filter_by(
                id=org_id, status=OrganizationStatus.ACTIVE
            ).first()
            if not organization:
                flash('Organization not found or not active. Please search and select a valid organization.', 'error')
                return render_template('pages/register.html')

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

        from app.models.user import UserRole

        role_map = {
            'worker': UserRole.WORKER,
            'auditor': UserRole.AUDITOR,
            'viewer': UserRole.VIEWER,
        }
        user.role = role_map.get(selected_role, UserRole.WORKER)

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
    return redirect(url_for('main.index'))


# ---------------------------------------------------------------------------
# Google Identity Services (GSI) - ID Token flow
# ---------------------------------------------------------------------------

@bp.route('/google/callback', methods=['POST'])
@csrf.exempt
def google_callback():
    """
    Handle the callback from Google GSI.
    Google sends a POST request with a 'credential' field containing a JWT ID token.
    """
    token = request.form.get('credential')
    if not token:
        flash('No credential received from Google.', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Verify the ID token
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            current_app.config['GOOGLE_CLIENT_ID']
        )

        # ID token is valid. Get the user's Google ID, email, and name.
        email = idinfo.get('email', '').strip().lower()
        if not email:
            flash('Could not retrieve email from Google token.', 'error')
            return redirect(url_for('auth.login'))

        # Look up existing user
        user = User.query.filter_by(email=email).first()

        if not user:
            # Auto-create a new account for first-time Google users
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

            user = User(
                email=email,
                # Placeholder hash — Google users cannot log in with a password
                password_hash=generate_password_hash(f'__gsi_oauth_{email}__'),
                first_name=first_name,
                last_name=last_name,
                status='active',
                role=UserRole.VIEWER,
            )
            db.session.add(user)
            db.session.commit()
            flash(f'Welcome to GreenLedger, {first_name or email}! Your account has been created.', 'success')
        else:
            if user.status != 'active':
                flash('Your account is suspended. Please contact support.', 'error')
                return redirect(url_for('auth.login'))
            flash(f'Welcome back, {user.first_name or user.email}!', 'success')

        login_user(user, remember=True)
        return redirect_to_dashboard(user)

    except ValueError:
        # Invalid token
        flash('Invalid Google ID token.', 'error')
        return redirect(url_for('auth.login'))
    except Exception as e:
        flash(f'Authentication error: {str(e)}', 'error')
        return redirect(url_for('auth.login'))
