from app.extensions import db
from app.models.base import BaseModel
from datetime import datetime

class AcademyProgress(BaseModel):
    __tablename__ = "academy_progress"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    module_id = db.Column(db.Integer, nullable=False)
    
    # Store viewed sections as a comma-separated string or a JSON list
    # For simplicity in this SQLite context, we'll use a JSON-ready string
    viewed_sections = db.Column(db.Text, default="[]") 
    
    # Completion status
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Quiz results
    quiz_score = db.Column(db.Integer, nullable=True) # Percentage
    
    # Relationship
    user = db.relationship("User", backref=db.backref("academy_progress", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<AcademyProgress User:{self.user_id} Module:{self.module_id} Completed:{self.is_completed}>"

    def mark_completed(self, score=None):
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        if score is not None:
            self.quiz_score = score
        db.session.commit()

class Achievement(BaseModel):
    __tablename__ = "academy_achievements"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    achievement_type = db.Column(db.String(50)) # e.g., 'MODULE_COMPLETION', 'QUIZ_MASTER'

    # Relationship
    user = db.relationship("User", backref=db.backref("achievements", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Achievement {self.name} for User:{self.user_id}>"

class Certificate(BaseModel):
    __tablename__ = "academy_certificates"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    score = db.Column(db.Float, nullable=False)
    passed = db.Column(db.Boolean, default=False)
    crypto_hash = db.Column(db.String(255), unique=True, nullable=True)
    blockchain_tx = db.Column(db.String(255), unique=True, nullable=True)
    status = db.Column(db.String(50), default="PENDING") # PENDING or NOTARIZED
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship("User", backref=db.backref("certificates", cascade="all, delete-orphan"))

    def __repr__(self):
        return f"<Certificate User:{self.user_id} Passed:{self.passed} Status:{self.status}>"
