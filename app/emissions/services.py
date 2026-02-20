"""
Emission Service Layer
Centralises all business logic for creating, submitting, validating,
rejecting and **editing** EmissionActivity records.  Routes should call
these functions rather than manipulating the ORM directly.
"""

from datetime import date, datetime
from typing import Optional

from flask import current_app
from app.extensions import db
from app.models.emission_activity import (
    EmissionActivity, EmissionScope, ActivityStatus
)
from app.models.emission_factor_database import ActivityType
from app.models.audit_log import AuditLog
from app.services.emission_factor_loader import get_loader, EmissionFactorData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _log(actor_id: int, org_id: int, action: str, entity_id: int, details: str):
    """Write an audit log entry (does NOT commit)."""
    entry = AuditLog(
        actor_id=actor_id,
        organization_id=org_id,
        action=action,
        entity_type="EmissionActivity",
        entity_id=entity_id,
        details=details,
    )
    db.session.add(entry)


def _kg_to_tonnes(kg: float) -> float:
    return round(kg / 1000, 6)


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _resolve_factor(form: dict):
    """Return (EmissionFactorData | None, co2e_result | None)."""
    loader = get_loader()
    factor: Optional[EmissionFactorData] = None
    ademe_id = form.get("ademe_factor_id", "").strip()
    if ademe_id:
        factor = loader.get_by_id(ademe_id)

    co2e_result = None
    if factor and factor.factor:
        qty = float(form.get("quantity") or 0)
        tn = float(form.get("tonnage") or 0) or None
        dist = float(form.get("distance") or 0) or None
        atype = form.get("activity_type", ActivityType.SIMPLE.value)
        co2e_result = calculate_co2e(atype, qty, factor.factor, tn, dist)

    return factor, co2e_result


# ---------------------------------------------------------------------------
# CO2e Calculation
# ---------------------------------------------------------------------------

def calculate_co2e(
    activity_type: str,
    quantity: float,
    factor_value: float,
    tonnage: Optional[float] = None,
    distance: Optional[float] = None,
) -> float:
    """
    Calculate CO2e in **kgCO2e**.

    - TRANSPORT : tonnage × distance × factor_value
    - otherwise : quantity × factor_value
    """
    if activity_type == ActivityType.TRANSPORT.value and tonnage and distance:
        return round(tonnage * distance * factor_value, 4)
    return round(quantity * factor_value, 4)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_activity(user, form: dict, *, auto_validate: bool = False) -> EmissionActivity:
    """
    Create a new EmissionActivity, calculate CO2e, snapshot ADEME factor.

    If ``auto_validate=True`` (org-admin direct entry) the status is set
    straight to VALIDATED — no submit→validate loop needed.
    """
    factor, co2e_result = _resolve_factor(form)

    initial_status = ActivityStatus.VALIDATED if auto_validate else ActivityStatus.DRAFT

    activity = EmissionActivity(
        organization_id=user.organization_id,
        created_by_id=user.id,
        scope=EmissionScope(form["scope"]),
        category=form.get("category", "").strip(),
        activity_type=ActivityType(form.get("activity_type", ActivityType.SIMPLE.value)),
        description=form.get("description", "").strip() or None,
        quantity=float(form.get("quantity") or 0) or None,
        quantity_unit=form.get("quantity_unit", "").strip() or None,
        period_start=_parse_date(form["period_start"]),
        period_end=_parse_date(form["period_end"]),
        # transport
        tonnage=float(form.get("tonnage") or 0) or None,
        distance=float(form.get("distance") or 0) or None,
        transport_mode=form.get("transport_mode") or None,
        # ADEME snapshot
        ademe_factor_id=factor.id if factor else None,
        ademe_factor_name=factor.name_fr if factor else None,
        ademe_factor_value=factor.factor if factor else None,
        ademe_factor_unit=factor.unit_fr if factor else None,
        ademe_factor_source=factor.source if factor else None,
        ademe_factor_category=factor.category if factor else None,
        # result
        co2e_result=co2e_result,
        status=initial_status,
        activity_data=form.get("activity_data") or {},
    )

    db.session.add(activity)
    db.session.flush()

    action_label = "CREATE_EMISSION_VALIDATED" if auto_validate else "CREATE_EMISSION_DRAFT"
    _log(
        actor_id=user.id,
        org_id=user.organization_id,
        action=action_label,
        entity_id=activity.id,
        details=(
            f"Created {'auto-validated' if auto_validate else 'draft'}: "
            f"scope={activity.scope.value}, category={activity.category}, "
            f"co2e={co2e_result} kgCO2e, "
            f"factor={factor.name_fr if factor else 'none'}"
        ),
    )

    db.session.commit()
    return activity


# ---------------------------------------------------------------------------
# Submit / Validate / Reject
# ---------------------------------------------------------------------------

def submit_activity(user, activity_id: int) -> EmissionActivity:
    """Move a DRAFT activity to SUBMITTED."""
    activity = EmissionActivity.query.get_or_404(activity_id)

    if activity.created_by_id != user.id:
        raise PermissionError("You can only submit your own activities.")
    if activity.status != ActivityStatus.DRAFT:
        raise ValueError("Only DRAFT activities can be submitted.")

    activity.status = ActivityStatus.SUBMITTED
    _log(
        actor_id=user.id,
        org_id=activity.organization_id,
        action="SUBMIT_EMISSION",
        entity_id=activity.id,
        details=f"Submitted for validation. co2e={activity.co2e_result} kgCO2e",
    )
    db.session.commit()
    return activity


def validate_activity(validator, activity_id: int) -> EmissionActivity:
    """Approve a SUBMITTED activity (org-admin or auditor)."""
    activity = EmissionActivity.query.get_or_404(activity_id)

    if activity.status != ActivityStatus.SUBMITTED:
        raise ValueError("Only SUBMITTED activities can be validated.")

    activity.status = ActivityStatus.VALIDATED
    _log(
        actor_id=validator.id,
        org_id=activity.organization_id,
        action="VALIDATE_EMISSION",
        entity_id=activity.id,
        details=f"Validated by {validator.email}. co2e={activity.co2e_result} kgCO2e",
    )
    db.session.commit()
    return activity


def reject_activity(validator, activity_id: int, reason: str) -> EmissionActivity:
    """Reject a SUBMITTED activity with a reason."""
    activity = EmissionActivity.query.get_or_404(activity_id)

    if activity.status != ActivityStatus.SUBMITTED:
        raise ValueError("Only SUBMITTED activities can be rejected.")

    activity.status = ActivityStatus.REJECTED
    activity.rejection_reason = reason.strip() if reason else None
    _log(
        actor_id=validator.id,
        org_id=activity.organization_id,
        action="REJECT_EMISSION",
        entity_id=activity.id,
        details=f"Rejected by {validator.email}. Reason: {reason}",
    )
    db.session.commit()
    return activity


# ---------------------------------------------------------------------------
# Update (edit) an existing activity
# ---------------------------------------------------------------------------

def update_activity(user, activity_id: int, form: dict,
                    *, is_admin: bool = False) -> EmissionActivity:
    """
    Update fields of an existing EmissionActivity.

    Guard rails
    -----------
    - **AUDITED** activities are locked — raises ValueError.
    - Workers can only edit their own DRAFT / REJECTED activities.
    - Org-admins can edit any non-AUDITED activity in their organisation.

    Status after edit
    -----------------
    - Admin edit → VALIDATED  (stays validated, no re-approval needed)
    - Worker edit → DRAFT     (must be re-submitted for validation)
    """
    activity = EmissionActivity.query.get_or_404(activity_id)

    # -- permission checks -----------------------------------------------------
    if activity.status == ActivityStatus.AUDITED:
        raise ValueError("Audited activities are locked and cannot be edited.")

    if not is_admin:
        if activity.created_by_id != user.id:
            raise PermissionError("You can only edit your own activities.")
        if activity.status not in (ActivityStatus.DRAFT, ActivityStatus.REJECTED):
            raise ValueError("You can only edit DRAFT or REJECTED activities.")

    if is_admin and activity.organization_id != user.organization_id:
        raise PermissionError("You can only edit activities in your organization.")

    # -- re-resolve ADEME factor ------------------------------------------------
    factor, co2e_result = _resolve_factor(form)

    # -- update fields ---------------------------------------------------------
    activity.scope = EmissionScope(form["scope"])
    activity.category = form.get("category", "").strip()
    activity.activity_type = ActivityType(
        form.get("activity_type", ActivityType.SIMPLE.value)
    )
    activity.description = form.get("description", "").strip() or None
    activity.quantity = float(form.get("quantity") or 0) or None
    activity.quantity_unit = form.get("quantity_unit", "").strip() or None
    activity.period_start = _parse_date(form["period_start"])
    activity.period_end = _parse_date(form["period_end"])
    activity.tonnage = float(form.get("tonnage") or 0) or None
    activity.distance = float(form.get("distance") or 0) or None
    activity.transport_mode = form.get("transport_mode") or None

    # ADEME snapshot
    activity.ademe_factor_id = factor.id if factor else None
    activity.ademe_factor_name = factor.name_fr if factor else None
    activity.ademe_factor_value = factor.factor if factor else None
    activity.ademe_factor_unit = factor.unit_fr if factor else None
    activity.ademe_factor_source = factor.source if factor else None
    activity.ademe_factor_category = factor.category if factor else None

    activity.co2e_result = co2e_result
    activity.activity_data = form.get("activity_data") or {}

    # Status reset
    if is_admin:
        activity.status = ActivityStatus.VALIDATED
    else:
        activity.status = ActivityStatus.DRAFT
    activity.rejection_reason = None  # clear old rejection

    _log(
        actor_id=user.id,
        org_id=activity.organization_id,
        action="UPDATE_EMISSION",
        entity_id=activity.id,
        details=(
            f"Updated by {'admin' if is_admin else 'worker'}: "
            f"scope={activity.scope.value}, co2e={co2e_result} kgCO2e"
        ),
    )

    db.session.commit()
    return activity
