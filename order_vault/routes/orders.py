from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
import threading
from order_vault.services.neo4j_service import trigger_process_and_update
from order_vault.main import app   # import your Flask app

orders_bp = Blueprint("orders", __name__)

@orders_bp.route("/finalize-order", methods=["POST"])
def finalize_order():
    order_data = request.get_json(force=True)
    order_data["created_at"] = datetime.utcnow().isoformat()
    
    def _background_task(data):
        # Push an application context so current_app is bound
        with app.app_context():
            trigger_process_and_update(data)

    thread = threading.Thread(target=_background_task, args=(order_data,))
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Order finalized and processing started."}), 200



