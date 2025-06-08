from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, g
import threading
from order_vault.services.neo4j_service import trigger_process_and_update
from order_vault.main import app   # import your Flask app
from order_vault.auth.api_auth import require_api_key 

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/finalize-order", methods=["POST"])
@require_api_key
def finalize_order():
    order_data = request.get_json(force=True)
    order_data["created_at"] = datetime.utcnow().isoformat()

    def _background_task(data, neo4j_driver):
        with current_app.app_context():
            trigger_process_and_update(data, neo4j_driver)

    thread = threading.Thread(target=_background_task, args=(order_data, g.neo4j_driver))
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Order finalized and processing started."}), 200



