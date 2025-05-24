from flask import Blueprint, request, jsonify, current_app

bp = Blueprint("promocode", __name__, url_prefix="/api/promocode")

@bp.route("/usage", methods=["GET"])
def usage():
    promo = request.args.get("promocode", "").strip()
    if not promo:
        return jsonify({"error": "Missing promocode"}), 400

    q = """…"""  # your long abusive‐usage cypher
    recs = list(current_app.neo4j_driver.session().run(q, {"promocode": promo}))
    data = [r.data() for r in recs]
    return jsonify(data), 200
