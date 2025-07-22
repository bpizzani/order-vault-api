from flask import Blueprint, request, jsonify, current_app, g
import hashlib
from order_vault.auth.api_auth import require_api_key_fingerprint
from order_vault.models.fingerprint import FingerprintEvents
from order_vault.main import db
from order_vault.utils.db_session import get_db_session_for_client  # helper we'll define
from order_vault.main import limiter
from threading import Thread

fingerprint_bp = Blueprint(
    "fingerprint", __name__, url_prefix="/api/fingerprint"
)

def async_save_fingerprint_event(db_uri, client_id, user_identifier_client, data, visitor_id):
    # Create a new DB session in the background thread
    session = get_db_session_for_client(db_uri)
    try:
        save_fingerprint_event(session, client_id, data, visitor_id)
    except Exception as e:
        print("Error in async DB save:", e)
    finally:
        session.close()
        
def save_fingerprint_event(db_session, client_id, user_identifier_client, data, visitor_id):
    entry = FingerprintEvents(
        client_id=client_id,
        user_id=user_identifier_client,
        visitor_id=visitor_id,
        js_visitor_id=data.get("fingerprint_js_visitor_id"),
        tm_visitor_id=data.get("thumbmark_js_visitor_id"),
        cookie_session=data.get("sessionId"),
        local_storage_device=data.get("local_user_id"),
        user_agent=str(data.get("userAgent"))[0:50],
        webdriver=data.get("webdriver"),
        platform=data.get("platform", data.get("apiLevel")),
    )
    db_session.add(entry)
    db_session.commit()
    print("Fingerprint Event Saved")
    
@fingerprint_bp.route("", methods=["GET","POST","OPTIONS"])
@require_api_key_fingerprint
@limiter.limit("200 per day")
@limiter.limit("50 per hour")
@limiter.limit("15 per minute")
def fingerprint():
    print(f"client ID  Fignerprint Call: {g.client_id }")

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
    #db_session = get_db_session_for_client(g.db_uri)
    #save_fingerprint_event(db_session, g.client_id, user_identifier_client, data, vid)
    
    # Fire off background thread to save
    Thread(
        target=async_save_fingerprint_event,
        args=(g.db_uri, g.client_id, user_identifier_client, data, vid),
        daemon=True
    ).start()
    
    #entry = FingerprintEvents(client_id=g.client_id, user_id=user_identifier_client, visitor_id=vid,js_visitor_id=fingerprint_js_visitor_id,tm_visitor_id=thumbmark_js_visitor_id, cookie_session=cookie_session,local_storage_device=user_identifier_device, user_agent=str(data.get('userAgent'))[0:50], webdriver=data.get('webdriver'), platform=platform)
    #db_session.add(entry)
    #db_session.commit()

    return jsonify({"visitorId": vid}), 200
