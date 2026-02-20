"""
API v1 — Emission Factor Search
Exposes the ADEME Base Carbone search engine over HTTP as JSON endpoints.
Used by the new-emission wizard frontend (Step 2 factor picker).
"""

from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.services.emission_factor_loader import get_loader

bp = Blueprint("api_factors", __name__, url_prefix="/api/v1/factors")


@bp.route("/search")
@login_required
def search():
    """
    GET /api/v1/factors/search?q=<query>&lang=fr&limit=20&valid_only=1

    Returns a JSON list of matching emission factors ordered by relevance.
    """
    q = request.args.get("q", "").strip()
    lang = request.args.get("lang", "fr")
    limit = min(int(request.args.get("limit", 20)), 50)
    valid_only = request.args.get("valid_only", "1") == "1"

    if not q or len(q) < 2:
        return jsonify([])

    loader = get_loader()
    raw_results = loader.search(q, language=lang, max_results=limit * 2)

    results = []
    for factor, score in raw_results:
        if valid_only and factor.status == "Archivé":
            continue
        results.append({
            "id": factor.id,
            "name_fr": factor.name_fr,
            "name_en": factor.name_en,
            "factor": factor.factor,
            "unit_fr": factor.unit_fr,
            "unit_en": factor.unit_en,
            "category": factor.category,
            "source": factor.source,
            "geographic_location": factor.geographic_location,
            "validity_period": factor.validity_period,
            "status": factor.status,
            "co2_fossil": factor.co2_fossil,
            "ch4_fossil": factor.ch4_fossil,
            "n2o": factor.n2o,
            "tags_fr": factor.tags_fr,
            "score": round(score, 3),
        })
        if len(results) >= limit:
            break

    return jsonify(results)


@bp.route("/<factor_id>")
@login_required
def get_factor(factor_id: str):
    """
    GET /api/v1/factors/<id>

    Returns a single factor by ADEME ID.
    """
    loader = get_loader()
    factor = loader.get_by_id(factor_id)
    if not factor:
        return jsonify({"error": "Factor not found"}), 404

    return jsonify({
        "id": factor.id,
        "name_fr": factor.name_fr,
        "name_en": factor.name_en,
        "factor": factor.factor,
        "unit_fr": factor.unit_fr,
        "unit_en": factor.unit_en,
        "category": factor.category,
        "source": factor.source,
        "geographic_location": factor.geographic_location,
        "validity_period": factor.validity_period,
        "status": factor.status,
        "co2_fossil": factor.co2_fossil,
        "ch4_fossil": factor.ch4_fossil,
        "ch4_bio": factor.ch4_bio,
        "n2o": factor.n2o,
        "co2_bio": factor.co2_bio,
        "other_ghg": factor.other_ghg,
        "tags_fr": factor.tags_fr,
        "comment_fr": factor.comment_fr,
    })
