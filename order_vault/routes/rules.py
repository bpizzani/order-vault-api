from flask import Blueprint, request, jsonify
from order_vault.models.rule import Rule
from order_vault.main import db

rules_bp = Blueprint("rules", __name__, url_prefix="/api/rules")

@rules_bp.route("", methods=["GET","POST"])
def manage_rules():
    if request.method == 'POST':
        # Extracting the JSON data from the request
        data = request.json

        # Create a new Rule instance
        new_rule = Rule(attribute=data['attribute'], threshold=data['threshold'], promocode=data['promocode'])

        # Add to database and commit
        db.session.add(new_rule)
        db.session.commit()

        # Return the new rule as JSON (including ID)
        return jsonify({
            "id": new_rule.id,
            "attribute": new_rule.attribute,
            "threshold": new_rule.threshold,
            "promocode": new_rule.promocode
        }), 201  # 201 status means the resource was created successfully

    # GET request: Return all the rules from the database
    rules = Rule.query.all()
    return jsonify([{
        "id": r.id,
        "attribute": r.attribute,
        "threshold": r.threshold,
        "promocode": r.promocode
    } for r in rules])

@rules_bp.route("<int:rule_id>", methods=["DELETE"])
def delete_rule(rule_id):
    rule = Rule.query.get(rule_id)
    if rule:
        db.session.delete(rule)
        db.session.commit()
        return jsonify({"message": "Rule deleted successfully"}), 200
    return jsonify({"error": "Rule not found"}), 404
