from flask import Blueprint, request, jsonify, current_app, g
import hashlib
from order_vault.auth.api_auth import require_api_key_fingerprint
from order_vault.models.fingerprint import FingerprintEvents
from order_vault.main import db
from order_vault.utils.db_session import get_db_session_for_client  # helper we'll define
from order_vault.main import limiter
from threading import Thread
from functools import wraps
from datetime import datetime, timedelta
from order_vault.models.client_subscription import ClientSubscription
from order_vault.models.fingerprint import FingerprintEvents  # adjust import if needed

fingerprint_bp = Blueprint(
    "fingerprint", __name__, url_prefix="/api/fingerprint"
)


def limit_fingerprint_events(max_events=300):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            db_session = get_db_session_for_client(g.db_uri)
            client_id = g.client_id

            # Define time window
            start_time = datetime.utcnow() - timedelta(days=30)

            # Count how many fingerprint events in last 30 days
            count = db_session.query(FingerprintEvents).filter(
                FingerprintEvents.client_id == client_id,
                FingerprintEvents.created_at >= start_time
            ).count()
            db_session.close()

            if count >= max_events:
                return jsonify({"error": "API quota exceeded for fingerprint events"}), 429

            return f(*args, **kwargs)
        return wrapped
    return decorator


def limit_fingerprint_events_subscription():
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            db_session = get_db_session_for_client(g.db_uri)
            client_id = g.get("client_id")

            if not client_id:
                db_session.close()
                return jsonify({"error": "Missing client_id"}), 400

            now = datetime.utcnow()

            # Fetch the active subscription
            subscription = db_session.query(ClientSubscription).filter(
                ClientSubscription.client_id == client_id,
                ClientSubscription.type == 'demo',
                ClientSubscription.subscription_start <= now,
                ClientSubscription.subscription_end >= now
            ).first()

            if not subscription:
                db_session.close()
                return jsonify({"error": "No active subscription found"}), 403

            # Count fingerprint events during the subscription period
            count = db_session.query(FingerprintEvents).filter(
                FingerprintEvents.client_id == client_id,
                FingerprintEvents.created_at >= subscription.subscription_start,
                FingerprintEvents.created_at <= subscription.subscription_end
            ).count()
            
            db_session.close()
            if count >= subscription.max_api_calls:
                return jsonify({"error": "API quota exceeded"}), 429

            return f(*args, **kwargs)
        return wrapped
    return decorator
 
def async_save_fingerprint_event(db_uri, client_id, user_identifier_client, data, visitor_id):
    # Create a new DB session in the background thread
    session = get_db_session_for_client(db_uri)
    try:
        save_fingerprint_event(session, client_id, user_identifier_client, data, visitor_id)
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
        cookie_session=data.get("accept_languague"), #data.get("sessionId"),
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
@limiter.limit("100 per hour")
@limiter.limit("15 per minute")
#@limit_fingerprint_events(max_events=300)
@limit_fingerprint_events_subscription
def fingerprint():
    print(f"client ID  Fignerprint Call: {g.client_id }")

    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json(silent=True) or {}
    data["accept_languague"] = request.headers.get("Accept-Language")
    user_identifier_client = request.headers.get("user_identifier_client")
    user_identifier_device = data.get("local_user_id") 
    fingerprint_js_visitor_id = data.get("fingerprint_js_visitor_id") 
    thumbmark_js_visitor_id = data.get("thumbmark_js_visitor_id") 
    
    print(request.headers.get("Accept-Language"))

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
    
    features = [
        str(data.get(k, "")) for k in (
            "userAgent","platform","screenRes","colorDepth",
            "timezone","languages", "plugins",
            "webGLFingerprint","canvasFingerprint"
        )
    ]
    vid = hashlib.sha256("|".join(features).encode()).hexdigest()


    # Fire off background thread to save
    Thread(
        target=async_save_fingerprint_event,
        args=(g.db_uri, g.client_id, user_identifier_client, data, vid),
        daemon=True
    ).start()


    return jsonify({"visitorId": vid}), 200


