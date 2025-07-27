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
from order_vault.utils.auth import login_required
from sqlalchemy import text
from collections import defaultdict

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
            if count >= subscription.max_api_fingerprint_calls:
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
        local_storage_device=data.get("local_session_id"),
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
@limit_fingerprint_events_subscription()
def fingerprint():
    print(f"client ID  Fignerprint Call: {g.client_id }")

    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json(silent=True) or {}
    data["accept_languague"] = request.headers.get("Accept-Language")
    user_identifier_client = request.headers.get("user_identifier_client")
    user_identifier_device = data.get("local_session_id") 
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
    
# API route to fetch duplicate usage stats
@fingerprint_bp.route("/device-usage", methods=["GET"])
@login_required
def device_usage():
    db_uri = g.db_uri
    client_id = g.client_id
    if not db_uri:
        return jsonify({"error": "Missing db_uri"}), 400

    session = get_db_session_for_client(db_uri)
    
    try:
        results = session.execute(text("""
            SELECT 
                CASE 
                    WHEN user_id = 'null' THEN local_storage_device 
                    ELSE user_id 
                END AS user_id,
                tm_visitor_id AS device_id 
            FROM fingerprint_events
            WHERE client_id = :client_id
              AND user_id IS NOT NULL 
              AND tm_visitor_id IS NOT NULL
        """), {"client_id": client_id}).fetchall()

        device_users = defaultdict(set)
        all_users = set()

        for row in results:
            device_users[row.device_id].add(row.user_id)
            all_users.add(row.user_id)

        # Compute duplicate users (those sharing device with someone else)
        duplicate_users = set()
        for users in device_users.values():
            if len(users) >= 2:
                duplicate_users.update(users)

        stats = {
            "total_devices": len(device_users),
            "total_users": len(all_users),
            "duplicate_users": len(duplicate_users),
            "duplicate_user_rate": round(100.0 * len(duplicate_users) / len(all_users), 2) if all_users else 0,
            "user_per_device": sorted(
                [{"device_id": device_id, "user_count": len(users)} for device_id, users in device_users.items()],
                key=lambda x: x["user_count"],
                reverse=True
            )[:20]  # Top 20 devices
        }

        return jsonify(stats)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@fingerprint_bp.route("/duplicate-rate-daily", methods=["GET"])
@login_required
def daily_duplicate_rate():
    db_uri = g.db_uri
    client_id = g.client_id
    if not db_uri:
        return jsonify({"error": "Missing db_uri"}), 400

    session = get_db_session_for_client(db_uri)

    try:
        query = text("""
            SELECT 
                date_trunc('day', created_at) AS p_date,
                CASE 
                    WHEN tm_visitor_id IS NULL OR tm_visitor_id = 'null' THEN js_visitor_id
                    WHEN js_visitor_id IS NULL OR js_visitor_id = 'null' THEN visitor_id
                    ELSE visitor_id
                END AS device_id,
                CASE 
                    WHEN user_id = 'null' THEN local_storage_device
                    ELSE user_id
                END AS user_id
            FROM fingerprint_events
            WHERE client_id = :client_id
              AND user_id IS NOT NULL
              AND created_at IS NOT NULL
        """)

        rows = session.execute(query, {"client_id": client_id}).fetchall()

        from collections import defaultdict

        # Organize by date
        per_day_devices = defaultdict(lambda: defaultdict(set))  # {date: {device_id: set(user_ids)}}
        per_day_users = defaultdict(set)

        for row in rows:
            date = row.p_date.date()
            device_id = row.device_id
            user_id = row.user_id

            if device_id and user_id:
                per_day_devices[date][device_id].add(user_id)
                per_day_users[date].add(user_id)

        result = []

        for date in sorted(per_day_devices.keys()):
            device_map = per_day_devices[date]
            user_pool = per_day_users[date]

            duplicate_users = set()
            for users in device_map.values():
                if len(users) >= 2:
                    duplicate_users.update(users)

            result.append({
                "date": date.strftime("%Y-%m-%d"),
                "total_duplicate_user": len(duplicate_users),
                "total_users": len(user_pool),
                "duplicate_rate": round(100.0 * len(duplicate_users) / len(user_pool), 2) if user_pool else 0
            })

        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
        

def daily_duplicate_rate_deprecate():
    db_uri = g.db_uri
    client_id = g.client_id
    if not db_uri:
        return jsonify({"error": "Missing db_uri"}), 400

    session = get_db_session_for_client(db_uri)

    try:
        query = text("""
            WITH main AS (
                SELECT 
                    date_trunc('day', created_at) AS p_date,
                    CASE 
                        WHEN tm_visitor_id IS NULL OR tm_visitor_id = 'null' THEN js_visitor_id
                        WHEN js_visitor_id IS NULL OR js_visitor_id = 'null' THEN visitor_id
                        ELSE visitor_id
                    END AS device_id,
                    COUNT(DISTINCT 
                        CASE 
                            WHEN user_id = 'null' THEN local_storage_device 
                            ELSE user_id 
                        END
                    ) AS total_users
                FROM fingerprint_events
                WHERE client_id = :client_id
                AND user_id IS NOT NULL
                GROUP BY 1, 2
            )
            SELECT 
                p_date,
                COUNT(CASE WHEN total_users >= 2 THEN device_id END) AS total_duplicate_user,
                COUNT(device_id) AS total_users,
                COUNT(DISTINCT device_id) AS total_devices,
                1.0 * COUNT(CASE WHEN total_users >= 2 THEN device_id END) / COUNT(device_id) AS duplicate_rate
            FROM main
            GROUP BY 1
            ORDER BY 1;
        """)

        rows = session.execute(query, {"client_id": client_id}).fetchall()

        result = []
        for row in rows:
            result.append({
                "date": row.p_date.strftime('%Y-%m-%d'),
                "total_duplicate_user": row.total_duplicate_user,
                "total_users": row.total_users,
                "duplicate_rate": round(row.duplicate_rate * 100, 2)  # as %
            })

        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

