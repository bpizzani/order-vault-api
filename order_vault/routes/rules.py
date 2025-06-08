from flask import Blueprint, request, jsonify, g
from order_vault.models.rule import Rule
from order_vault.main import db
from order_vault.auth.sessions import login_required  # decorator that loads tenant
from order_vault.utils.db_session import get_db_session_for_client  # helper we'll define

rules_bp = Blueprint("rules", __name__, url_prefix="/api/rules")

@rules_bp.route("", methods=["GET","POST"])
@login_required
def manage_rules():
    db_session = get_db_session_for_client(g.db_uri)
    if request.method == 'POST':
        # Extracting the JSON data from the request
        data = request.json

        # Create a new Rule instance
        new_rule = Rule(attribute=data['attribute'], threshold=data['threshold'], promocode=data['promocode'])

        # Add to database and commit
        db_session.add(new_rule)
        db_session.commit()

        # Return the new rule as JSON (including ID)
        return jsonify({
            "id": new_rule.id,
            "attribute": new_rule.attribute,
            "threshold": new_rule.threshold,
            "promocode": new_rule.promocode
        }), 201  # 201 status means the resource was created successfully

    # GET request: Return all the rules from the database
    rules = db_session.query(Rule).all()
    
    return jsonify([{
        "id": r.id,
        "attribute": r.attribute,
        "threshold": r.threshold,
        "promocode": r.promocode
    } for r in rules])

@rules_bp.route("<int:rule_id>", methods=["DELETE"])
@login_required
def delete_rule(rule_id):
    db_session = get_db_session_for_client(g.db_uri)
    rule = db_session.query(Rule).get(rule_id)
    
    if rule:
        db_session.delete(rule)
        db_session.commit()
        return jsonify({"message": "Rule deleted successfully"}), 200
    return jsonify({"error": "Rule not found"}), 404
