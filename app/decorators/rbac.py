"""Role-Based Access Control decorators."""
from functools import wraps
from flask import abort, current_app
from flask_login import current_user


def role_required(role_name: str, organization_id: int = None):
    """
    Decorator to require a specific role.
    
    Args:
        role_name: Name of the required role (admin, auditor, worker, viewer)
        organization_id: Optional organization ID to check role within specific org
    
    Returns:
        403 Forbidden if user doesn't have the required role
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            
            if not current_user.has_role(role_name, organization_id):
                current_app.logger.warning(
                    f"User {current_user.email} attempted to access {f.__name__} "
                    f"without required role: {role_name}"
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(organization_id: int = None):
    """Convenience decorator for admin role."""
    return role_required("admin", organization_id)


def auditor_required(organization_id: int = None):
    """Convenience decorator for auditor role."""
    return role_required("auditor", organization_id)
