"""Seed script for mock users with credentials."""
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.user import User, UserRole
from app.models.organization import Organization


def seed_users():
    """Create mock users with known credentials. Idempotent."""
    
    # Create organizations if they don't exist
    orgs_data = [
        {
            "name": "Acme Global Industries",
            "legal_name": "Acme Global Industries Ltd.",
            "country": "United States",
            "industry": "Manufacturing"
        },
        {
            "name": "EuroSteel Corp",
            "legal_name": "EuroSteel Corporation",
            "country": "Germany",
            "industry": "Steel Production"
        },
        {
            "name": "GreenTech Solutions",
            "legal_name": "GreenTech Solutions Inc.",
            "country": "Canada",
            "industry": "Technology"
        }
    ]
    
    organizations = {}
    for org_data in orgs_data:
        org = Organization.query.filter_by(name=org_data["name"]).first()
        if not org:
            org = Organization(**org_data, is_active=True)
            db.session.add(org)
            print(f"Created organization: {org_data['name']}")
        else:
            print(f"Organization already exists: {org_data['name']}")
        organizations[org_data["name"]] = org
    
    db.session.flush()
    
    # Create mock users with single role enum
    users_data = [
        {
            "email": "admin@acme.com",
            "password": "admin123",
            "first_name": "Admin",
            "last_name": "User",
            "organization": "Acme Global Industries",
            "role": UserRole.ORG_ADMIN
        },
        {
            "email": "auditor@acme.com",
            "password": "auditor123",
            "first_name": "Auditor",
            "last_name": "Smith",
            "organization": "Acme Global Industries",
            "role": UserRole.AUDITOR
        },
        {
            "email": "worker@acme.com",
            "password": "worker123",
            "first_name": "Worker",
            "last_name": "Johnson",
            "organization": "Acme Global Industries",
            "role": UserRole.WORKER
        },
        {
            "email": "viewer@acme.com",
            "password": "viewer123",
            "first_name": "Viewer",
            "last_name": "Brown",
            "organization": "Acme Global Industries",
            "role": UserRole.VIEWER
        },
        {
            "email": "admin@eurosteel.com",
            "password": "admin123",
            "first_name": "Hans",
            "last_name": "Mueller",
            "organization": "EuroSteel Corp",
            "role": UserRole.ORG_ADMIN
        },
        {
            "email": "worker@eurosteel.com",
            "password": "worker123",
            "first_name": "Klaus",
            "last_name": "Schmidt",
            "organization": "EuroSteel Corp",
            "role": UserRole.WORKER
        },
        {
            "email": "admin@greentech.com",
            "password": "admin123",
            "first_name": "Sarah",
            "last_name": "Jenkins",
            "organization": "GreenTech Solutions",
            "role": UserRole.ORG_ADMIN
        }
    ]
    
    for user_data in users_data:
        existing_user = User.query.filter_by(email=user_data["email"]).first()
        if existing_user:
            # Update role if it's wrong
            if existing_user.role != user_data["role"]:
                existing_user.role = user_data["role"]
                print(f"Updated role for user: {user_data['email']} -> {user_data['role'].value}")
            else:
                print(f"User already exists: {user_data['email']}")
            continue
        
        org = organizations.get(user_data["organization"])
        if not org:
            print(f"Organization not found: {user_data['organization']}")
            continue
        
        user = User(
            email=user_data["email"],
            password_hash=generate_password_hash(user_data["password"]),
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            status="active",
            organization_id=org.id,
            role=user_data["role"]
        )
        
        db.session.add(user)
        print(f"Created user: {user_data['email']} ({user_data['role'].value})")
    
    db.session.commit()
    
    print("\n✅ User seeding complete!")
    print("\n📋 Login Credentials:")
    print("=" * 50)
    for user_data in users_data:
        print(f"Email: {user_data['email']}")
        print(f"Password: {user_data['password']}")
        print(f"Role: {user_data['role'].value}")
        print(f"Organization: {user_data['organization']}")
        print("-" * 50)
