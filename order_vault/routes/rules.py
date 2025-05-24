from flask import Blueprint, request, jsonify
from ..models.rule import Rule
from ..extensions import db

bp = Blueprint("rules", __name__, url_prefix="/api/rules")

@bp.route("", methods=["GET", "POST"])
def manage_rules():
    if request.method == "POST":
        data = request.get_json(force=True)
        rule = Rule(attribute=data["attribute"],
                    threshold=data["threshold"],
                    promocode=data.get("promocode"))
        db.session.add(rule)
        db.session.commit()
        return jsonify(rule.to_dict()), 201

    rules = Rule.query.all()
    return jsonify([r.to_dict() for r in rules]), 200

@bp.route("/<int:rule_id>", methods=["DELETE"])
def delete_rule(rule_id):
    rule = Rule.query.get_or_404(rule_id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": "Rule deleted"}), 200
