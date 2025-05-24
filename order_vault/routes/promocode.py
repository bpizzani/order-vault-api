from flask import Blueprint, request, jsonify, current_app

promocode_bp = Blueprint("promocode", __name__, url_prefix="/api/promocode")

@promocode_bp.route("/usage")
def usage():
    promo = request.args.get("promocode",""
        ).strip()
    if not promo:
        return jsonify({"error":"Missing promocode"}), 400
    q = """ ... abusive usage Cypher ... """
    rows = list(current_app.neo4j_driver.session().run(q, {"promocode":promo}))
    return jsonify([r.data() for r in rows]), 200
