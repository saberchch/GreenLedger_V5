from flask import Blueprint, render_template, abort, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.academy import AcademyProgress
from app.extensions import db
import json

bp = Blueprint('academy', __name__, url_prefix='/academy')

# ── Exam configuration ────────────────────────────────────────────────────────
MAX_EXAM_ATTEMPTS = 3  # Maximum failed attempts before the exam is locked

@bp.route('/')
@login_required
def index():
    """Academy landing page."""
    progress = AcademyProgress.query.filter_by(user_id=current_user.id).order_by(AcademyProgress.updated_at.desc()).all()
    progress_map = {p.module_id: p for p in progress}
    
    resume_module_id = 1
    if progress:
        incomplete = [p for p in progress if not p.is_completed]
        if incomplete:
            resume_module_id = min((p.module_id for p in incomplete))
        else:
            resume_module_id = 17
            
    return render_template('academy/index.html', progress_map=progress_map, resume_module_id=resume_module_id)

@bp.route('/module/<int:module_id>')
@login_required
def module(module_id):
    """Render a specific training module."""
    if module_id < 1 or module_id > 17:
        abort(404)
    
    # Get or create progress record
    progress = AcademyProgress.query.filter_by(user_id=current_user.id, module_id=module_id).first()
    if not progress:
        progress = AcademyProgress(user_id=current_user.id, module_id=module_id)
        db.session.add(progress)
        db.session.commit()

    template_path = f'academy/modules/module_{module_id}.html'
    return render_template(template_path, module_id=module_id, progress=progress)

@bp.route('/api/progress', methods=['POST'])
@login_required
def update_progress():
    """API endpoint to update section progress and quiz results."""
    data = request.json
    module_id = data.get('module_id')
    section_id = data.get('section_id')
    is_completed = data.get('is_completed', False)
    score = data.get('score')

    progress = AcademyProgress.query.filter_by(user_id=current_user.id, module_id=module_id).first()
    if not progress:
        progress = AcademyProgress(user_id=current_user.id, module_id=module_id)
        db.session.add(progress)

    if section_id:
        try:
            viewed = json.loads(progress.viewed_sections or "[]")
        except:
            viewed = []
            
        if section_id not in viewed:
            viewed.append(section_id)
            progress.viewed_sections = json.dumps(viewed)

    if is_completed:
        progress.mark_completed(score=score)
        
        # Achievement Logic
        from app.models.academy import Achievement
        achievement_name = f"Module {module_id} Graduate"
        existing_achievement = Achievement.query.filter_by(user_id=current_user.id, name=achievement_name).first()
        
        if not existing_achievement:
            new_achievement = Achievement(
                user_id=current_user.id,
                name=achievement_name,
                description=f"Completed all sections and mastery check for Module {module_id}.",
                achievement_type='MODULE_COMPLETION'
            )
            db.session.add(new_achievement)

    db.session.commit()
    return jsonify({
        "status": "success", 
        "module_id": module_id,
        "is_completed": progress.is_completed,
        "viewed_count": len(json.loads(progress.viewed_sections or "[]"))
    })

@bp.route('/certification')
@login_required
def certification():
    """Certification rules page."""
    from app.models.academy import Certificate
    cert = Certificate.query.filter_by(user_id=current_user.id, passed=True).first()
    # Count attempts regardless of pass/fail so rules page shows remaining attempts
    attempts_used = Certificate.query.filter_by(user_id=current_user.id).count()
    attempts_remaining = max(0, MAX_EXAM_ATTEMPTS - attempts_used) if not cert else None
    return render_template(
        'academy/certification.html',
        certificate=cert,
        attempts_used=attempts_used,
        attempts_remaining=attempts_remaining,
        max_attempts=MAX_EXAM_ATTEMPTS
    )

@bp.route('/certification/exam')
@login_required
def certification_exam():
    """Actual exam interface."""
    from app.models.academy import Certificate
    import os

    # Already passed → go to success page
    cert = Certificate.query.filter_by(user_id=current_user.id, passed=True).first()
    if cert:
        return redirect(url_for('academy.certification'))

    # Count how many attempts (pass OR fail) this user has used
    attempts_used = Certificate.query.filter_by(user_id=current_user.id).count()
    if attempts_used >= MAX_EXAM_ATTEMPTS:
        flash(f'You have used all {MAX_EXAM_ATTEMPTS} attempts. Please contact support to unlock your exam.', 'error')
        return redirect(url_for('academy.certification'))

    # Use absolute path from blueprint root
    q_path = os.path.join(bp.root_path, 'questions.json')
    try:
        with open(q_path, 'r') as f:
            questions = json.load(f)
    except Exception:
        questions = []

    attempt_number = attempts_used + 1
    return render_template(
        'academy/exam.html',
        questions=questions,
        attempt_number=attempt_number,
        max_attempts=MAX_EXAM_ATTEMPTS
    )

@bp.route('/certification/submit', methods=['POST'])
@login_required
def certification_submit():
    data = request.json
    answers = data.get('answers', {})
    
    import os
    import secrets
    from app.models.academy import Certificate
    from app.models.notification import Notification, NotificationType
    from app.models.user import User, UserRole
    
    # Use absolute path from blueprint root
    q_path = os.path.join(bp.root_path, 'questions.json')
    try:
        with open(q_path, 'r') as f:
            questions = json.load(f)
    except Exception as e:
        print(f"DEBUG: Error loading questions from {q_path}: {e}")
        questions = []
        
    correct = 0
    total = len(questions)
    if total == 0:
        return jsonify({"error": "No questions found", "path": q_path}), 400
        
    for q in questions:
        q_id = str(q['id'])
        if q_id in answers and int(answers[q_id]) == q['correct_index']:
            correct += 1
            
    score = (correct / total) * 100
    passed = score >= 70
    
    cert = Certificate(
        user_id=current_user.id,
        score=score,
        passed=passed
    )
    
    if passed:
        cert.crypto_hash = secrets.token_hex(32)
        db.session.add(cert)
        db.session.flush() # to get cert.id
        
        # Notify admin
        admin = User.query.filter_by(role=UserRole.PLATFORM_ADMIN).first()
        if admin:
            notif = Notification(
                user_id=admin.id,
                title="Pending Certification Notarization",
                message=f"User {current_user.first_name} {current_user.last_name} passed the Academy with {score:.1f}%. Please notarize their certificate.",
                type=NotificationType.INFO,
                related_entity_type='certificate',
                related_entity_id=cert.id
            )
            db.session.add(notif)
    else:
        db.session.add(cert)
        
    db.session.commit()
    
    return jsonify({"score": score, "passed": passed, "cert_id": cert.id})

@bp.route('/certification/results/<int:cert_id>')
@login_required
def certification_results(cert_id):
    """Unified results page for exam attempts."""
    from app.models.academy import Certificate
    cert = Certificate.query.get_or_404(cert_id)
    
    if cert.user_id != current_user.id:
        abort(403)
        
    attempts_used = Certificate.query.filter_by(user_id=current_user.id).count()
    attempts_remaining = max(0, MAX_EXAM_ATTEMPTS - attempts_used)
    
    return render_template(
        'academy/results.html',
        certificate=cert,
        attempts_remaining=attempts_remaining,
        max_attempts=MAX_EXAM_ATTEMPTS
    )

@bp.route('/certification/pdf/<int:cert_id>')
@login_required
def certification_pdf(cert_id):
    from app.models.academy import Certificate
    from flask import send_file, abort
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    
    cert = Certificate.query.get_or_404(cert_id)
    if cert.user_id != current_user.id and current_user.role.value != 'platform_admin':
        abort(403)
        
    if not cert.passed:
        abort(400)
        
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 24)
    p.drawString(100, 700, "GreenLedger Academy Certificate")
    
    p.setFont("Helvetica", 14)
    p.drawString(100, 650, f"This is to certify that {cert.user.first_name} {cert.user.last_name}")
    p.drawString(100, 620, f"has successfully passed the Carbon Accounting Certification.")
    
    p.drawString(100, 580, f"Score: {cert.score:.1f}%")
    p.drawString(100, 550, f"Date: {cert.issued_at.strftime('%Y-%m-%d')}")
    
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(100, 500, f"Verification Hash: {cert.crypto_hash}")
    p.drawString(100, 480, f"Blockchain TX: {cert.blockchain_tx or 'Pending Notarization'}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return send_file(
        buffer, 
        as_attachment=True, 
        download_name=f"GreenLedger_Certificate_{cert.user.last_name}.pdf", 
        mimetype='application/pdf'
    )
