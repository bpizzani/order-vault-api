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

@orders_bp.route("/simulate-order", methods=["POST"])
def simulate_order():
    def send_fake_order():
        url = "https://www.rediim.com/simulate-order"
        data = {
            "name": "Test User",
            "email": f"test{random.randint(1000, 9999)}@example.com",
            "phone": f"6{random.randint(100000000, 999999999)}",
            "card_details": str(uuid.uuid4())[:16],
            "promocode": "testpromo",
            "device_id": str(uuid.uuid4()),
            "ip_address": "127.0.0.1",
            "bot_flag": "NO",
            "fingerprint_inhouse": str(uuid.uuid4())
        }
    
        response = requests.post(url, json=data)
        print(response.status_code, response.text)
    
    # Usage
    send_fake_order()

