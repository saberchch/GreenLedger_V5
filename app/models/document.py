from app.extensions import db
from app.models.base import BaseModel

class Document(BaseModel):
    __tablename__ = "documents"

    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(1024), nullable=False) # Path on disk (encrypted)
    
    encrypted = db.Column(db.Boolean, default=True, nullable=False)
    hash_checksum = db.Column(db.String(128), nullable=False) # SHA-256 of original file for integrity
    
    content_type = db.Column(db.String(100)) # MIME type
    file_size = db.Column(db.Integer) # Size in bytes

    uploaded_by_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id"), 
        nullable=False
    )
    
    organization_id = db.Column(
        db.Integer, 
        db.ForeignKey("organizations.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Optional link to a specific activity
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("emission_activities.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    uploaded_by = db.relationship("User", backref="uploaded_documents")
    organization = db.relationship("Organization", backref="documents")
    activity = db.relationship("EmissionActivity", backref="documents")

    def __repr__(self):
        return f"<Document {self.filename} ({self.organization.name})>"
