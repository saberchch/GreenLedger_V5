from flask import Blueprint, send_file, abort, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.models.document import Document
from app.security.permissions import PermissionManager
from app.security.encryption import EncryptionManager
from app.models.audit_log import AuditLog
import io
import os

bp = Blueprint('documents', __name__, url_prefix='/documents')

@bp.route('/<int:doc_id>/download')
@login_required
def download_document(doc_id):
    document = Document.query.get_or_404(doc_id)
    
    # Check permissions
    if not PermissionManager.can_decrypt_document(current_user, document):
        # Audit access denial
        log = AuditLog(
            actor_id=current_user.id,
            organization_id=document.organization_id,
            action="ACCESS_DENIED_DOCUMENT",
            entity_type="Document",
            entity_id=document.id,
            details="User attempted to access document without permission."
        )
        db.session.add(log)
        db.session.commit()
        abort(403)

    try:
        # Read encrypted file
        with open(document.file_path, "rb") as f:
            encrypted_data = f.read()
            
        # Decrypt
        decrypted_data = EncryptionManager.decrypt_file(encrypted_data, document.organization_id)
        
        # Log Access
        log = AuditLog(
            actor_id=current_user.id,
            organization_id=document.organization_id,
            action="ACCESS_DOCUMENT",
            entity_type="Document",
            entity_id=document.id,
            details=f"User downloaded document {document.filename}"
        )
        db.session.add(log)
        db.session.commit()
        
        return send_file(
            io.BytesIO(decrypted_data),
            download_name=document.filename,
            as_attachment=True,
            mimetype=document.content_type
        )
    except Exception as e:
        current_app.logger.error(f"Decryption failed: {str(e)}")
        abort(500)
