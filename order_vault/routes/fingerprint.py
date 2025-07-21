from flask import Blueprint, request, jsonify, current_app, g
import hashlib
from order_vault.auth.api_auth import require_api_key_fingerprint
from order_vault.models.fingerprint import FingerprintEvents
from order_vault.main import db
from order_vault.utils.db_session import get_db_session_for_client  # helper we'll define
from order_vault.main import limiter

fingerprint_bp = Blueprint(
    "fingerprint", __name__, url_prefix="/api/fingerprint"
)

@fingerprint_bp.route("", methods=["GET","POST","OPTIONS"])
@require_api_key_fingerprint
@limiter.limit("200 per day")
@limiter.limit("50 per hour")
@limiter.limit("1 per minute")
def fingerprint():
    print(f"client ID  Fignerprint Call: {g.client_id }")
    db_session = get_db_session_for_client(g.db_uri)

    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json(silent=True) or {}
    user_identifier_client = request.headers.get("user_identifier_client")
    user_identifier_device = data.get("local_user_id") 
    fingerprint_js_visitor_id = data.get("fingerprint_js_visitor_id") 
    thumbmark_js_visitor_id = data.get("thumbmark_js_visitor_id") 

    platform = data.get("platform", data.get("apiLevel"))
    
    print(f"platform: {platform}")
    print(f"user identifier detected: {user_identifier_client}")
    print(f"thumbmark_js_visitor_id detected: {thumbmark_js_visitor_id}")
    print(f"user_identifier_device detected: {user_identifier_device}")
    print(f"fingerprint_js_visitor_id detected: {fingerprint_js_visitor_id}")
    print(f"sessions_id: {request.headers.get('sessions_id')}")
    print(f"User Agent: {data.get('userAgent') }")
    print(f"webdriver: {data.get('webdriver') }")

    
    cookie_session = data.get("sessionId")
    print(f"cookie_session detected: {cookie_session}")

    #existing = (
    #    db_session.query(FingerprintEvents)
    #    .filter_by(client_id=g.client_id, local_storage_device=user_identifier_device)
    #    .order_by(FingerprintEvents.id.desc())  # get last by id
    #    .first())
    
    #if existing:
    #    print("Existing fingerprint match found, returning saved visitorId.")
    #    return jsonify({"visitorId": existing.visitor_id}), 200
    
    features = [
        str(data.get(k, "")) for k in (
            "userAgent","platform","screenRes","colorDepth",
            "timezone","languages", "plugins",
            "webGLFingerprint","canvasFingerprint"
        )
    ]
    vid = hashlib.sha256("|".join(features).encode()).hexdigest()

    # Store in DB
    entry = FingerprintEvents(client_id=g.client_id, user_id=user_identifier_client, visitor_id=vid,js_visitor_id=fingerprint_js_visitor_id,tm_visitor_id=thumbmark_js_visitor_id, cookie_session=cookie_session,local_storage_device=user_identifier_device, user_agent=str(data.get('userAgent'))[0:50], webdriver=data.get('webdriver'), platform=platform)
    db_session.add(entry)
    db_session.commit()
    print("Fingerprint Event Saved")

    return jsonify({"visitorId": vid}), 200
