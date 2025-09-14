from flask import Blueprint, request, jsonify, current_app, g
from order_vault.models.rule import Rule
from order_vault.models.client_subscription import ClientSubscription
from order_vault.models.evaluation import Evaluation
from order_vault.services.neo4j_service import evaluate_attributes
from order_vault.auth.api_auth import require_api_key   
from order_vault.auth.bearer import require_auth
from order_vault.utils.db_session import get_db_session_for_client 
from threading import Thread

evaluate_bp = Blueprint("evaluate", __name__, url_prefix="/api")


def limit_risk_evlauation_events_subscription():
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
            count = db_session.query(Evaluation).filter(
                Evaluation.client_id == client_id,
                Evaluation.created_at >= subscription.subscription_start,
                Evaluation.created_at <= subscription.subscription_end
            ).count()
            
            db_session.close()
            if count >= subscription.max_api_calls:
                return jsonify({"error": "API quota exceeded"}), 429

            return f(*args, **kwargs)
        return wrapped
    return decorator
 
 
def async_save_evaluation_event(db_uri, client_id,  user_id, checkout_id, order_id, session_id, promo, values, risk_decision):
    # Create a new DB session in the background thread
    session = get_db_session_for_client(db_uri)
    try:
        save_evaluation_event(session, client_id, user_id, checkout_id, order_id, session_id, promo, values, risk_decision)
    except Exception as e:
        print("Error in async DB save:", e)
    finally:
        session.close()
        
def save_evaluation_event(db_session, client_id, user_id, checkout_id, order_id, session_id, promo, values, risk_decision):
    entry = Evaluation(
        client_id = client_id,
        user_id = user_id,
        checkout_id = checkout_id,
        order_id = order_id,
        session_id = session_id,
        promocode = promo,
        promotion_id = promo,
        visitor_id = values["device_id"],
        local_storage_device = values["local_session_id"],
        risk_decision = risk_decision["overall_abusive"],
        risk_features = str(risk_decision["evaluation_results"]),
    )
    db_session.add(entry)
    db_session.commit()
    print("Risk Evaluation Event Saved")
    
@evaluate_bp.route("/evaluate", methods=["POST"])
#@require_api_key
@require_auth()
def evaluate():
    data = request.get_json(force=True)

    accepted_types = ['card_details', 'email', 'device_id', 'phone', 'local_session_id']
    
    types = data.get("attribute_types", ["device_id"])
    coupon = data.get("coupon")
    promo = coupon.get("promotion_id")
    values = {t: data.get(t) for t in accepted_types if data.get(t)}
    
    print(values["device_id"])

    checkout_id = data.get("checkout_id", "")
    user_id = data.get("user_id", "")
    session_id = data.get("session_id", "")
    order_id = data.get("order_id", "")
    
    import time
    start = time.time()

    # Run Cypher query
    raw = evaluate_attributes(g.neo4j_driver.session(), accepted_types, promo)

    # Batch load rules
    rule_objs = Rule.query.filter(Rule.attribute.in_(accepted_types), Rule.promocode == promo,Rule.client_id == g.client_id).all()
    rule_map = {rule.attribute: rule for rule in rule_objs}

    final = {}
    overall = False

    for t in accepted_types:
        input_value = values.get(t)
        recs = raw.get(t, [])
        
        # Find the specific record that matches the input value
        matching = next((r for r in recs if r["attribute_value"] == input_value), None)
        count = matching["order_count"] if matching else 0

        rule = rule_map.get(t)
        abusive = rule and count >= rule.threshold

        final[t] = {
            "value": input_value,
            "promocode": promo,
            "count": count,
            "abusive": bool(abusive)
        }

        overall = overall or abusive

    print("Evaluate total time:", time.time() - start)

    risk_decision = {"evaluation_results": final, "overall_abusive": overall}
    # Fire off background thread to save

    Thread(
        target=async_save_evaluation_event,
        args=(g.db_uri, g.client_id, user_id, checkout_id, order_id, session_id, promo, values, risk_decision),
        daemon=True
    ).start()

    return jsonify({"evaluation_results": final, "overall_abusive": overall}), 200

