from app.factory import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.organization import Organization
from werkzeug.security import generate_password_hash

app = create_app('development')

with app.app_context():
    # Check if admin exists
    admin_email = "platform_admin@acme.com"
    user = User.query.filter_by(email=admin_email).first()
    
    if not user:
        # Get an organization to attach to (optional for platform admin but good for foreign key constraints if strict)
        org = Organization.query.first()
        if not org:
            print("No organization found. Creating one.")
            org = Organization(name="System", legal_name="System", country="US", industry="Tech", is_active=True)
            db.session.add(org)
            db.session.flush()

        user = User(
            email=admin_email,
            password_hash=generate_password_hash("admin123"),
            first_name="Platform",
            last_name="Admin",
            status="active",
            organization_id=org.id,
            role=UserRole.PLATFORM_ADMIN
        )
        db.session.add(user)
        db.session.commit()
        print(f"Created platform admin: {admin_email}")
    else:
        print(f"User {admin_email} already exists.")
        if user.role != UserRole.PLATFORM_ADMIN:
            user.role = UserRole.PLATFORM_ADMIN
            db.session.commit()
            print(f"Updated role to PLATFORM_ADMIN.")
