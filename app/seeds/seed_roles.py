"""Seed script for MVP roles."""
from app.extensions import db
from app.models.role import Role


def seed_roles():
    """Create MVP roles if they don't exist. Idempotent."""
    roles_data = [
        {
            "name": "admin",
            "description": "Full system & organization access"
        },
        {
            "name": "auditor",
            "description": "Audit, validation, approval, blockchain notarization"
        },
        {
            "name": "worker",
            "description": "Data input, calculations, logistics"
        },
        {
            "name": "viewer",
            "description": "Read-only access"
        }
    ]

    for role_data in roles_data:
        existing_role = Role.query.filter_by(name=role_data["name"]).first()
        if not existing_role:
            role = Role(
                name=role_data["name"],
                description=role_data["description"]
            )
            db.session.add(role)
            print(f"Created role: {role_data['name']}")
        else:
            print(f"Role already exists: {role_data['name']}")

    db.session.commit()
    print("Role seeding completed.")


if __name__ == "__main__":
    from app.factory import create_app
    app = create_app()
    with app.app_context():
        seed_roles()
