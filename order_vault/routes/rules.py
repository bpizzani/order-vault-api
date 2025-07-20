from flask import Blueprint, request, jsonify, g
from order_vault.models.rule import Rule
from order_vault.main import db
from order_vault.utils.auth import login_required
from order_vault.utils.db_session import get_db_session_for_client  # helper we'll define

rules_bp = Blueprint("rules", __name__, url_prefix="/api/rules")

@rules_bp.route("", methods=["GET","POST"])
def manage_rules():
    db_session = get_db_session_for_client(g.db_uri)
    try:
        if request.method == 'POST':
            data = request.json
            new_rule = Rule(
                attribute=data['attribute'],
                threshold=data['threshold'],
                promocode=data['promocode'],
                client_id=g.client_id,
            )
            db_session.add(new_rule)
            db_session.commit()
            return jsonify({
                "id": new_rule.id,
                "attribute": new_rule.attribute,
                "threshold": new_rule.threshold,
                "promocode": new_rule.promocode,
            }), 201

        rules = db_session.query(Rule).filter_by(client_id=g.client_id).all()
        return jsonify([{
            "id": r.id,
            "attribute": r.attribute,
            "threshold": r.threshold,
            "promocode": r.promocode
        } for r in rules])
    
    finally:
        db_session.close()

@rules_bp.route("<int:rule_id>", methods=["DELETE"])
def delete_rule(rule_id):
    db_session = get_db_session_for_client(g.db_uri)
    rule = db_session.query(Rule).filter_by(id=rule_id, client_id=g.client_id).first()
    
    if rule:
        db_session.delete(rule)
        db_session.commit()
        return jsonify({"message": "Rule deleted successfully"}), 200
    return jsonify({"error": "Rule not found"}), 404
