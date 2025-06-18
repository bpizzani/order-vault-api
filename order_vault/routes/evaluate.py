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

    # Start timing if needed
    import time; start = time.time()

    # Run Cypher query
    raw = evaluate_attributes(g.neo4j_driver.session(), types, promo)

    # Batch load all rules once
    rule_objs = Rule.query.filter(Rule.attribute.in_(types), Rule.promocode == promo).all()
    rule_map = {rule.attribute: rule for rule in rule_objs}

    final = {}
    overall = False
    for t, recs in raw.items():
        rule = rule_map.get(t)
        count = recs[0]["order_count"] if recs else 0
        abusive = rule and count >= rule.threshold
        final[t] = {
            "value": values.get(t),
            "promocode": promo,
            "count": count,
            "abusive": bool(abusive)
        }
        overall = overall or abusive

    print("Evaluate total time:", time.time() - start)

    return jsonify({"evaluation_results": final, "overall_abusive": overall}), 200
    
def evaluate_old():
    types = request.args.get("attribute_types","device_id").split(",")
    promo = request.args.get("promocode")
    values = {t: request.args.get(t) for t in types if request.args.get(t)}
    raw = evaluate_attributes(
        g.neo4j_driver.session(), types, promo
    )
    final = {}
    overall = False
    for t, recs in raw.items():
        rule = Rule.query.filter_by(attribute=t, promocode=promo).first()
        count = recs[0]["order_count"] if recs else 0
        abusive = rule and count >= rule.threshold
        final[t] = {"value": values.get(t), "promocode": promo,
                     "count": count, "abusive": bool(abusive)}
        overall = overall or abusive
    return jsonify({"evaluation_results": final, "overall_abusive": overall}), 200
