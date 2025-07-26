from flask import Blueprint, request, jsonify, current_app, g
from order_vault.models.rule import Rule
from order_vault.services.neo4j_service import evaluate_attributes
from order_vault.auth.api_auth import require_api_key   

evaluate_bp = Blueprint("evaluate", __name__, url_prefix="/api")

@evaluate_bp.route("/evaluate", methods=["GET"])
@require_api_key
def evaluate():
    types = request.args.get("attribute_types", "device_id").split(",")
    promo = request.args.get("promocode")
    values = {t: request.args.get(t) for t in types if request.args.get(t)}
    checkout_id = request.args.get("checkout_id")
    print(checkout_id)
    
    import time
    start = time.time()

    # Run Cypher query
    raw = evaluate_attributes(g.neo4j_driver.session(), types, promo)

    # Batch load rules
    rule_objs = Rule.query.filter(Rule.attribute.in_(types), Rule.promocode == promo,Rule.client_id == g.client_id).all()
    rule_map = {rule.attribute: rule for rule in rule_objs}

    final = {}
    overall = False

    for t in types:
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

    return jsonify({"evaluation_results": final, "overall_abusive": overall}), 200

