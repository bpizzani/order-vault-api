from flask import Blueprint, request, jsonify, current_app
import threading
from services.neo4j_service import save_order_graph

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/finalize-order", methods=["POST"])
def finalize_order():
    data = request.get_json(force=True)
    threading.Thread(
        target=lambda d: save_order_graph(
            current_app.neo4j_driver.session(),
            d
        ),
        args=(data,)
    ).start()
    return jsonify({"message":"Order finalized"}), 200
