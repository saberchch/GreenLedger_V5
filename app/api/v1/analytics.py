from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func
from datetime import datetime

from app.models.emission_activity import EmissionActivity, ActivityStatus, EmissionScope
from app.security.permissions import PermissionManager
from app.extensions import db

bp = Blueprint('api_analytics', __name__, url_prefix='/api/v1/analytics')

@bp.route('/emissions', methods=['GET'])
@login_required
def get_emissions_analytics():
    """
    Returns aggregated emissions data for graphs.
    Filters: date_from, date_to, scope, category, status.
    Workers can only see their own emissions unless they have org-admin rights.
    """
    try:
        # Determine the target organization ID
        target_org_id = request.args.get('org_id', type=int)

        # 1. Platform Admins can see everything (global view if no org_id, specific org if org_id)
        if PermissionManager.is_platform_admin(current_user):
            query = EmissionActivity.query
            if target_org_id:
                query = query.filter_by(organization_id=target_org_id)

        # 2. Auditors can see data for orgs they are contracted with
        elif current_user.role == UserRole.AUDITOR:
            if not target_org_id:
                return jsonify({'error': 'Auditors must specify an org_id'}), 400
                
            from app.models.contract import AuditorContract, ContractStatus
            has_contract = AuditorContract.query.filter(
                AuditorContract.auditor_id == current_user.id,
                AuditorContract.organization_id == target_org_id,
                AuditorContract.status.in_([ContractStatus.TRIAL, ContractStatus.ACTIVE])
            ).first()
            
            if not has_contract:
                return jsonify({'error': 'Not authorized to view analytics for this organization'}), 403
            
            query = EmissionActivity.query.filter_by(organization_id=target_org_id)

        # 3. Org Admins and Viewers can see everything WITHIN their own org
        elif current_user.role in (UserRole.ORG_ADMIN, UserRole.VIEWER):
            if not current_user.organization_id:
                return jsonify({'error': 'No organization assigned'}), 403
            query = EmissionActivity.query.filter_by(organization_id=current_user.organization_id)

        # 4. Workers can only see their OWN activities
        elif current_user.role == UserRole.WORKER:
            if not current_user.organization_id:
                return jsonify({'error': 'No organization assigned'}), 403
            query = EmissionActivity.query.filter_by(
                organization_id=current_user.organization_id, 
                created_by_id=current_user.id
            )
            
        else:
            return jsonify({'error': 'Unauthorized role for analytics'}), 403

        # Apply Filters from request args
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        scope = request.args.get('scope')
        category = request.args.get('category')
        status = request.args.get('status')

        if date_from:
            query = query.filter(EmissionActivity.period_start >= datetime.strptime(date_from, '%Y-%m-%d').date())
        if date_to:
            query = query.filter(EmissionActivity.period_end <= datetime.strptime(date_to, '%Y-%m-%d').date())
        if scope:
            query = query.filter(EmissionActivity.scope == EmissionScope(scope))
        if category:
            query = query.filter(EmissionActivity.category == category)
        if status:
            query = query.filter(EmissionActivity.status == ActivityStatus(status))

        # We only care about activities with actual calculated results
        query = query.filter(EmissionActivity.co2e_result.isnot(None))

        # Execute query
        activities = query.all()

        # Aggregations
        total_co2e_kg = sum(a.co2e_result for a in activities)
        total_co2e_t = total_co2e_kg / 1000

        # Scope Breakdown
        scopes = {}
        for a in activities:
            s = a.scope.value
            scopes[s] = scopes.get(s, 0) + a.co2e_result

        # Category Breakdown
        categories = {}
        for a in activities:
            c = a.category or 'Uncategorized'
            categories[c] = categories.get(c, 0) + a.co2e_result

        # Trend Data (Monthly)
        trend = {}
        for a in activities:
            # Group by year-month of the period start date
            month_key = a.period_start.strftime('%Y-%m')
            trend[month_key] = trend.get(month_key, 0) + a.co2e_result

        # Sort trend chronologically
        sorted_trend_keys = sorted(trend.keys())
        trend_labels = sorted_trend_keys
        trend_data = [trend[k] / 1000 for k in sorted_trend_keys] # Convert to tonnes for charts

        # Activity Types (Radar chart)
        activity_types = {}
        for a in activities:
            t = a.activity_type.value
            activity_types[t] = activity_types.get(t, 0) + a.co2e_result

        return jsonify({
            'summary': {
                'total_kg': total_co2e_kg,
                'total_t': total_co2e_t,
                'count': len(activities)
            },
            'scopes': {
                'labels': list(scopes.keys()),
                'data': [v / 1000 for v in scopes.values()]
            },
            'categories': {
                # top 10 categories
                'labels': [k for k, v in sorted(categories.items(), key=lambda item: item[1], reverse=True)[:10]],
                'data': [v / 1000 for k, v in sorted(categories.items(), key=lambda item: item[1], reverse=True)[:10]]
            },
            'trend': {
                'labels': trend_labels,
                'data': trend_data
            },
            'activity_types': {
                'labels': list(activity_types.keys()),
                'data': [v / 1000 for v in activity_types.values()]
            }
        })

    except Exception as e:
        current_app.logger.error(f"Analytics API Error: {e}")
        return jsonify({'error': str(e)}), 500
