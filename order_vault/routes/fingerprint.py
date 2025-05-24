from flask import Blueprint, request, jsonify, current_app
import hashlib
from ..services.fingerprint_service import select_features

bp = Blueprint("fingerprint", __name__, url_prefix="/api/fingerprint")

@bp.route("", methods=["GET","POST","OPTIONS"])
def fingerprint():
    if request.method == "OPTIONS":
        return "", 200

    data = request.get_json(force=True, silent=True) or {}
    selected = select_features(data)
    visitor_id = hashlib.sha256("|".join(selected).encode()).hexdigest()
    return jsonify({"visitorId": visitor_id}), 200
