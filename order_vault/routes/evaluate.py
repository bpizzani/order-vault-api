from flask import Blueprint, request, jsonify
from ..models.rule import Rule
from ..extensions import db
from ..services.neo4j_service import evaluate_attributes

bp = Blueprint("evaluate", __name__, url_prefix="/api")

@bp.route("/evaluate", methods=["GET"])
def evaluate():
    attribute_types = request.args.get("attribute_types", "device_id").split(",")
    values = {t: request.args.get(t) for t in attribute_types if request.args.get(t)}
    promocode = request.args.get("promocode")

    # service returns dict: { attribute_type: [{ value, count }...] }
    raw = evaluate_attributes(
        current_app.neo4j_driver.session(),
        attribute_types, promocode
    )

    final = {}
    overall_abusive = False

    for attr, records in raw.items():
        rule = Rule.query.filter_by(attribute=attr, promocode=promocode).first()
        entry = {
            "value": values.get(attr),
            "promocode": promocode,
            "count": 0,
            "abusive": False
        }
        if records:
            entry["count"] = records[0]["order_count"]
            if rule:
                entry["abusive"] = entry["count"] >= rule.threshold
        final[attr] = entry
        overall_abusive = overall_abusive or entry["abusive"]

    return jsonify({
        "evaluation_results": final,
        "overall_abusive": overall_abusive
    }), 200
