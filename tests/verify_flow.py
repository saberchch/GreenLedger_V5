
import os
import unittest
from app.factory import create_app
from app.extensions import db
from app.models.user import User, UserRole
from app.models.organization import Organization, OrganizationStatus
from app.models.emission_activity import EmissionActivity, ActivityStatus, EmissionScope
from app.models.audit_log import AuditLog
from app.security.encryption import EncryptionManager

class VerificationTestCase(unittest.TestCase):
    def setUp(self):
        # Set MASTER_KEY for encryption testing
        os.environ['MASTER_KEY'] = 'test_master_key_1234567890123456'
        
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Setup Data
        self.org = Organization(name="Test Org", status=OrganizationStatus.ACTIVE)
        db.session.add(self.org)
        db.session.commit()
        
        self.worker = User(email="worker@test.com", password_hash="hash", role=UserRole.WORKER, organization_id=self.org.id)
        self.auditor = User(email="auditor@test.com", password_hash="hash", role=UserRole.AUDITOR, organization_id=self.org.id)
        db.session.add(self.worker)
        db.session.add(self.auditor)
        db.session.commit()
        
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_encryption_module(self):
        """Step 3 Verify: Encryption logic"""
        data = b"Sensitive Data"
        encrypted = EncryptionManager.encrypt_file(data, self.org.id)
        decrypted = EncryptionManager.decrypt_file(encrypted, self.org.id)
        self.assertEqual(data, decrypted)
        
        # Verify isolation: Different org ID should fail
        with self.assertRaises(Exception):
            EncryptionManager.decrypt_file(encrypted, self.org.id + 1)

    def test_ghg_workflow(self):
        """Step 5/6 Verify: GHG Pipeline and RBAC"""
        from datetime import date
        # 1. Create Activity (Manual DB for simplicity in unit test, simulating form)
        activity = EmissionActivity(
            organization_id=self.org.id,
            created_by_id=self.worker.id,
            scope=EmissionScope.SCOPE_1,
            category="Fuel",
            status=ActivityStatus.DRAFT,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            activity_data={"amount": 100}
        )
        db.session.add(activity)
        db.session.commit()
        
        # 2. Worker submits
        # Using permission manager directly to verify logic
        from app.security.permissions import PermissionManager
        
        self.assertTrue(PermissionManager.can_submit_activity(self.worker))
        
        # Worker cannot validate
        self.assertFalse(PermissionManager.can_validate_activity(self.worker, activity))
        
        # 3. Auditor can validate
        self.assertTrue(PermissionManager.can_validate_activity(self.auditor, activity))
        
        # 4. Perform workflow
        activity.status = ActivityStatus.SUBMITTED
        db.session.commit()
        self.assertEqual(activity.status, ActivityStatus.SUBMITTED)
        
        activity.status = ActivityStatus.VALIDATED
        db.session.commit()
        self.assertEqual(activity.status, ActivityStatus.VALIDATED)

    def test_audit_logging(self):
        """Step 8 Verify: Audit Log creation"""
        log = AuditLog(
            actor_id=self.worker.id,
            organization_id=self.org.id,
            action="TEST_ACTION",
            entity_type="Test",
            entity_id=1
        )
        db.session.add(log)
        db.session.commit()
        
        saved_log = AuditLog.query.first()
        self.assertIsNotNone(saved_log)
        self.assertEqual(saved_log.action, "TEST_ACTION")

if __name__ == '__main__':
    unittest.main()
