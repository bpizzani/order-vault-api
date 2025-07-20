from flask import Blueprint, request, jsonify, current_app, g
import hashlib
from order_vault.auth.api_auth import require_api_key_fingerprint
from order_vault.models.fingerprint import FingerprintEvents
from order_vault.main import db
from order_vault.utils.db_session import get_db_session_for_client  # helper we'll define

fingerprint_bp = Blueprint(
    "fingerprint", __name__, url_prefix="/api/fingerprint"
)

@fingerprint_bp.route("", methods=["GET","POST","OPTIONS"])
@require_api_key_fingerprint
def fingerprint():
    db_session = get_db_session_for_client(g.db_uri)

    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json(silent=True) or {}
    user_identifier_client = request.headers.get("user_identifier_client")
    print(f"user identifier detected: {user_identifier_client}")
    
    cookie_session = request.cookies.get('session')
    print(f"cookie_session detected: {cookie_session}")
    features = [
        str(data.get(k, "")) for k in (
            "userAgent","platform","screenRes","colorDepth",
            "timezone","languages","plugins",
            "webGLFingerprint","canvasFingerprint"
        )
    ]
    vid = hashlib.sha256("|".join(features).encode()).hexdigest()

    # Store in DB
    entry = FingerprintEvents(user_id=user_identifier_client, visitor_id=vid, cookie_session=cookie_session)
    db_session.add(new_rule)
    db_session.commit()
    print("Fingerprint Event Saved")

    return jsonify({"visitorId": vid}), 200
