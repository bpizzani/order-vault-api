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

    #def _background_task(data):
    #    with app.app_context():
    #        trigger_process_and_update(data)

    #thread = threading.Thread(target=_background_task, args=(order_data,))
    #thread.daemon = True
    #thread.start()

    # Use the Neo4j driver from g (it's only valid inside the request context)
    trigger_process_and_update(order_data, g.neo4j_driver)

    return jsonify({"message": "Order finalized and processing completed."}), 200



