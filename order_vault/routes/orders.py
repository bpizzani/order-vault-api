from flask import Blueprint, request, jsonify, current_app
import threading
from ..services.neo4j_service import save_order_graph
import requests

bp = Blueprint("orders", __name__)

@bp.route("/", methods=["GET"])
def home():
    return current_app.send_static_file("home2.html")

@bp.route("/rules", methods=["GET"])
def rules_ui():
    return current_app.send_static_file("rules.html")

@bp.route("/promotion_dashboard", methods=["GET"])
def promotion_ui():
    return current_app.send_static_file("promotion_dashboard.html")

@bp.route("/island", methods=["GET"])
def customer_ui():
    return current_app.send_static_file("island.html")

@bp.route("/finalize-order", methods=["POST"])
def finalize_order():
    data = request.get_json(force=True)
    threading.Thread(
        target=lambda d: save_order_graph(current_app.neo4j_driver.session(), d),
        args=(data,)
    ).start()
    return jsonify({"message": "Order finalized and processing started."}), 200

@bp.route("/process-and-update-deprecated", methods=["GET"])
def process_and_update_deprecated():
    resp = requests.get(current_app.config["CLIENT_APP_API_URL"])
    resp.raise_for_status()
    orders = resp.json().get("orders", [])
    session = current_app.neo4j_driver.session()
    for order in orders:
        save_order_graph(session, order)
    return jsonify({"message": "Data processed and graph updated successfully."}), 200
