from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.organization import Organization, OrganizationStatus
from app.models.report import Report, ReportStatus
from app.models.user import User
import uuid

bp = Blueprint(
    'dashboard_admin',
    __name__,
    url_prefix='/dashboard/admin'
)


@bp.route('/')
@login_required
def admin_index():
    """
    Admin dashboard:
    - Organization overview
    - User management
    - Global KPIs
    - Web3 Notarization
    - Org Approval
    """
    pending_organizations = Organization.query.filter_by(status=OrganizationStatus.PENDING).all()
    audited_reports = Report.query.filter_by(status=ReportStatus.AUDITED).all()
    
    # Simple KPIs
    total_users = User.query.count()
    total_orgs = Organization.query.count()
    active_orgs = Organization.query.filter_by(status=OrganizationStatus.ACTIVE).count()
    total_reports = Report.query.count()

    return render_template(
        'pages/dashboard/admin/index.html',
        user=current_user,
        pending_organizations=pending_organizations,
        audited_reports=audited_reports,
        kpis={
            'total_users': total_users,
            'total_orgs': total_orgs,
            'active_orgs': active_orgs,
            'total_reports': total_reports
        }
    )

@bp.route('/organization/<int:org_id>/approve', methods=['POST'])
@login_required
def approve_organization(org_id):
    org = Organization.query.get_or_404(org_id)
    org.status = OrganizationStatus.ACTIVE
    org.is_active = True
    db.session.commit()
    flash(f'Organization {org.name} approved successfully.', 'success')
    return redirect(url_for('dashboard_admin.admin_index'))

@bp.route('/organization/<int:org_id>/reject', methods=['POST'])
@login_required
def reject_organization(org_id):
    org = Organization.query.get_or_404(org_id)
    org.status = OrganizationStatus.REJECTED
    org.is_active = False
    db.session.commit()
    flash(f'Organization {org.name} rejected.', 'info')
    return redirect(url_for('dashboard_admin.admin_index'))

@bp.route('/report/<int:report_id>/notarize', methods=['POST'])
@login_required
def notarize_report(report_id):
    report = Report.query.get_or_404(report_id)
    if report.status != ReportStatus.AUDITED:
        flash('Report is not ready for notarization.', 'error')
        return redirect(url_for('dashboard_admin.admin_index'))
    
    # Mock Notarization
    report.status = ReportStatus.NOTARIZED
    report.blockchain_tx_hash = f"0x{uuid.uuid4().hex}"
    db.session.commit()
    
    flash(f'Report notarized successfully. TX: {report.blockchain_tx_hash[:10]}...', 'success')
    return redirect(url_for('dashboard_admin.admin_index'))