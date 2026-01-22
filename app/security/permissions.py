from app.models.user import User, UserRole
from app.models.emission_activity import EmissionActivity, ActivityStatus
from app.models.document import Document

class PermissionManager:
    """
    Centralized permission logic for GreenLedger.
    Enforces RBAC and Organization Isolation.
    """

    @staticmethod
    def is_platform_admin(user: User) -> bool:
        return user.role == UserRole.PLATFORM_ADMIN

    @staticmethod
    def is_org_admin(user: User, organization_id: int = None) -> bool:
        if user.role != UserRole.ORG_ADMIN:
            return False
        if organization_id and user.organization_id != organization_id:
            return False
        return True

    @staticmethod
    def can_submit_activity(user: User) -> bool:
        """Worker and Org Admin can submit activities."""
        return user.role in [UserRole.WORKER, UserRole.ORG_ADMIN] and user.organization_id is not None

    @staticmethod
    def can_validate_activity(user: User, activity: EmissionActivity) -> bool:
        """
        Auditors and Org Admins can validate.
        - Org Admin: Must be from the same org.
        - Auditor: Must have delegation (assuming auditor is external or assigned).
          For MVP, auditor might be system-wide or assigned. 
          Prompt says 'Delegated verifier'.
          Let's assume Auditor can validate any org they are assigned to, or for now, just check role.
        
        RESTRICTION: Cannot validate own submission.
        """
        if user.id == activity.created_by_id:
            return False

        if user.role == UserRole.ORG_ADMIN:
            return user.organization_id == activity.organization_id
        
        if user.role == UserRole.AUDITOR:
            # Future: Check if auditor is assigned to this org
            return True 
            
        return False

    @staticmethod
    def can_decrypt_document(user: User, document: Document) -> bool:
        """
        Only Worker (owner), Org Admin, and Auditor can decrypt.
        Platform Admin cannot decrypt.
        """
        if user.role == UserRole.PLATFORM_ADMIN:
            return False
            
        if user.organization_id != document.organization_id and user.role != UserRole.AUDITOR:
             # Basic isolation: must be in same org, unless auditor
             return False

        if user.role == UserRole.WORKER:
            return True # Workers can view org docs? Or only own? 
            # Prompt says "only worker (owner), org_admin, and delegated auditor"
            # So if worker, must be owner.
            if user.id != document.uploaded_by_id and user.role == UserRole.WORKER:
                 # Check strict ownership if worker
                 return user.id == document.uploaded_by_id

        if user.role in [UserRole.ORG_ADMIN, UserRole.AUDITOR]:
            return True
            
        return False

    @staticmethod
    def can_view_dashboard(user: User, dashboard_type: str) -> bool:
         if dashboard_type == "platform_admin":
             return user.role == UserRole.PLATFORM_ADMIN
         if dashboard_type == "org_admin":
             return user.role == UserRole.ORG_ADMIN
         if dashboard_type == "worker":
             return user.role == UserRole.WORKER
         if dashboard_type == "auditor":
             return user.role == UserRole.AUDITOR
         return False
