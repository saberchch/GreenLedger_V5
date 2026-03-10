"""Database models."""
from app.models.base import BaseModel
from app.models.user import User
from app.models.role import Role
from app.models.organization import Organization
from app.models.user_role import user_roles
from app.models.report import Report
from app.models.notification import Notification
from app.models.activity_message import ActivityMessage
# Legacy — keep for any existing references
from app.models.auditor_request import AuditorRequest, RequestStatus
# New smart-contract models
from app.models.auditor_contract import AuditorContract, ContractStatus, AuditorType
from app.models.auditor_point_log import AuditorPointLog
from app.models.secure_message import SecureMessage, MessageChannel
from app.models.system_setting import SystemSetting

__all__ = [
    "BaseModel",
    "User",
    "Role",
    "Organization",
    "user_roles",
    "Report",
    "Notification",
    "ActivityMessage",
    # Legacy
    "AuditorRequest",
    "RequestStatus",
    # New
    "AuditorContract",
    "ContractStatus",
    "AuditorType",
    "AuditorPointLog",
    "SecureMessage",
    "MessageChannel",
    "SystemSetting",
]
