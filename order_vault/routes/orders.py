from flask import Blueprint, request, jsonify, current_app
import threading
from order_vault.services.neo4j_service import save_order_graph, trigger_process_and_update

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/finalize-order", methods=["POST"])
def finalize_order():
    try:
        # Get order data from the request (client confirms finalization)
        order_data = request.json  # Expecting JSON with order details

        # After client confirms, trigger the background process to handle data processing
        threading.Thread(target=trigger_process_and_update, args=(order_data,)).start()

        return jsonify({"message": "Order finalized and processing started."}), 200

    except Exception as e:
        return jsonify({"error": "An error occurred while finalizing the order", "details": str(e)}), 500



def finalize_order_old():
    data = request.get_json(force=True)
    threading.Thread(
        target=lambda d: save_order_graph(
            current_app.neo4j_driver.session(),
            d
        ),
        args=(data,)
    ).start()
    return jsonify({"message":"Order finalized"}), 200



