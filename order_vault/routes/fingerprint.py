from flask import Blueprint, request, jsonify, current_app
import hashlib
from order_vault.auth.api_auth import require_api_key_fingerprint

fingerprint_bp = Blueprint(
    "fingerprint", __name__, url_prefix="/api/fingerprint"
)

@fingerprint_bp.route("", methods=["GET","POST","OPTIONS"])
@require_api_key_fingerprint
def fingerprint():
    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json(silent=True) or {}
    user_identifier_client = request.headers.get("user_identifier_client")
    features = [
        str(data.get(k, "")) for k in (
            "userAgent","platform","screenRes","colorDepth",
            "timezone","languages","plugins",
            "webGLFingerprint","canvasFingerprint"
        )
    ]
    vid = hashlib.sha256("|".join(features).encode()).hexdigest()
    return jsonify({"visitorId": vid}), 200
