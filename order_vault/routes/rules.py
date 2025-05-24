from flask import Blueprint, request, jsonify
from order_vault.models.rule import Rule
from main import db

rules_bp = Blueprint("rules", __name__, url_prefix="/api/rules")

@rules_bp.route("", methods=["GET","POST"])
def manage_rules():
    if request.method == "POST":
        data = request.get_json(force=True)
        rule = Rule(
            attribute=data["attribute"],
            threshold=data["threshold"],
            promocode=data.get("promocode")
        )
        db.session.add(rule)
        db.session.commit()
        return jsonify(rule.to_dict()), 201
    return jsonify([r.to_dict() for r in Rule.query.all()]), 200

@rules_bp.route("/<int:id>", methods=["DELETE"])
def delete_rule(id):
    rule = Rule.query.get_or_404(id)
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message":"Deleted"}), 200
