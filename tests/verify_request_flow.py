import os
import sys

# Setup Flask app context
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.factory import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.auditor_request import AuditorRequest, RequestStatus

app = create_app('testing')

def run_verify():
    with app.app_context():
        db.create_all()
        print("--- Testing Auditor Request Flow ---")
        
        # 1. Setup Data
        org = Organization.query.first()
        if not org:
            org = Organization(name="Test Org")
            db.session.add(org)
            db.session.commit()
            
        org_admin = User.query.filter_by(organization_id=org.id, role=UserRole.ORG_ADMIN).first()
        if not org_admin:
            org_admin = User(email="admin@test.com", password_hash="hash", role=UserRole.ORG_ADMIN, organization_id=org.id)
            db.session.add(org_admin)
            
        auditor = User.query.filter_by(role=UserRole.AUDITOR).first()
        if not auditor:
            auditor = User(email="auditor@test.com", password_hash="hash", role=UserRole.AUDITOR)
            db.session.add(auditor)
            
        db.session.commit()

        # Ensure auditor isn't already assigned
        if org in auditor.audited_organizations:
            auditor.audited_organizations.remove(org)
            db.session.commit()
            
        AuditorRequest.query.delete()
        db.session.commit()

        # 2. Org Admin Sends Request
        print(f"1. Org Admin ({org_admin.email}) requests Auditor ({auditor.email})")
        req = AuditorRequest(
            organization_id=org.id,
            auditor_id=auditor.id,
            status=RequestStatus.PENDING
        )
        db.session.add(req)
        db.session.commit()
        
        # Verify Pending state
        pending_req = AuditorRequest.query.filter_by(auditor_id=auditor.id, status=RequestStatus.PENDING).first()
        if not pending_req:
            print("FAILED: Pending request not found.")
            return
        else:
            print("SUCCESS: Request is PENDING.")

        # 3. Auditor Accepts Request
        print(f"2. Auditor accepts the request.")
        pending_req.status = RequestStatus.ACCEPTED
        if pending_req.organization not in auditor.audited_organizations:
            auditor.audited_organizations.append(pending_req.organization)
        db.session.commit()

        # Verify Accepted state & delegation
        accepted_req = AuditorRequest.query.get(pending_req.id)
        if accepted_req.status != RequestStatus.ACCEPTED:
            print("FAILED: Request status is not ACCEPTED.")
            return
            
        if org not in auditor.audited_organizations:
            print("FAILED: Auditor was not added to delegated_auditors.")
            return
            
        print("SUCCESS: Auditor successfully delegated!")
        print("--- Test Complete ---")

if __name__ == '__main__':
    run_verify()
