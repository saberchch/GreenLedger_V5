from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models.report import Report, ReportStatus

bp = Blueprint(
    'dashboard_viewer',
    __name__,
    url_prefix='/dashboard/viewer'
)


@bp.route('/')
@login_required
def viewer_index():
    """
    Viewer dashboard:
    - Read-only reports
    """
    # Show Audited and Notarized reports for the organization
    query = Report.query.filter(Report.status.in_([ReportStatus.AUDITED, ReportStatus.NOTARIZED]))
    if current_user.organization_id:
         query = query.filter_by(organization_id=current_user.organization_id)
         
    reports = query.order_by(Report.created_at.desc()).all()
    
    return render_template(
        'pages/dashboard/viewer/index.html',
        user=current_user,
        reports=reports,
        kpis={
            'total_reports': len(reports),
            'notarized_reports': len([r for r in reports if r.status == ReportStatus.NOTARIZED]),
            'carbon_offset': '1,240 tCO2e' # Mock
        }
    )