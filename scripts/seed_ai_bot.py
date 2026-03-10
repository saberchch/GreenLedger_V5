from app.factory import create_app
from app.extensions import db
from app.models.user import User, UserRole
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    ai_email = 'ai@greenledger.com'
    existing = User.query.filter_by(email=ai_email).first()
    
    if not existing:
        ai_user = User(
            email=ai_email,
            first_name='GreenLedger',
            last_name='AI',
            role=UserRole.VIEWER, # We'll use VIEWER as base safely, or a generic role
            organization_id=None
        )
        ai_user.password_hash = generate_password_hash('this-is-an-internal-bot-account-DO-NOT-USE')
        db.session.add(ai_user)
        db.session.commit()
        print(f"✅ Successfully seeded AI Bot User: {ai_email} (ID: {ai_user.id})")
    else:
        print(f"ℹ️ AI Bot {ai_email} already exists (ID: {existing.id}).")
