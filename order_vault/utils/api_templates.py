
def risk_finalize_order_api(order_data, api_key=None, client_id=None):
    # Define the URL for the finalize-order API endpoint
    finalize_url = "https://api.rediim.com/finalize-order"
    
    headers = {
        "X-API-KEY": api_key,  # 🛡️ Important: pass the API key in the header
        "X-CLIENT-ID": client_id 
    }
    
    # Make the API call to finalize the order
    try:
        # Send the entire order data as JSON
        response = requests.post(finalize_url, json=order_data, headers=headers)
        
        # Handle the response
        if response.status_code == 200:
            return response.json()  # Assume the response is JSON
        else:
            return {"status": "failed", "error": f"Error: {response.status_code} - {response.text}"}
    
    except requests.exceptions.RequestException as e:
        return {"status": "failed", "error": f"Request failed: {str(e)}"}


def risk_api(attribute_types=None, values=None, promocode=None, api_key=None, client_id=None):
    """
    Calls the business API to get aggregated data by multiple attribute types (e.g., device_id, phone) 
    with corresponding values, and returns the overall evaluation (true/false for abusive).

    :param attribute_types: List of attribute types to aggregate by (e.g., ["device_id", "phone"])
    :param values: Dictionary of attribute values corresponding to each attribute type (e.g., {"device_id": "12345", "phone": "9876543210"})
    :param promocode: Optional promocode filter (default is None)
    :return: A dictionary containing the overall abusive evaluation (True/False), or an error message
    """

    business_api_url = "https://api.rediim.com/api/evaluate"
    
    # Prepare query parameters
    params = {"attribute_types": ",".join(attribute_types)}
    for attribute_type in attribute_types:
        if attribute_type in values:
            params[attribute_type] = values[attribute_type]
    if promocode:
        params["promocode"] = promocode

    headers = {
        "X-API-KEY": api_key,  # 🛡️ Important: pass the API key in the header
        "X-CLIENT-ID": client_id 
    }

    try:
        response = requests.get(business_api_url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return {"overall_abusive": data.get('overall_abusive', False)}
        else:
            return {"error": f"Error: {response.status_code} - {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}



      
        # Fetch aggregated data by device and phone if promocode is not null
        values = {
            "device_id": device_id,  
            "phone": phone,  
            "card_details": card_details,  
            "email": email,
            "local_session_id": local_session_id,
            "checkout_id":checkout_id,
            "user_id": user_id,
            "order_id": checkout_id,
            "session_id": local_session_id,
        }
        abuse = 0
        if promocode:
            risk_response = risk_api(attribute_types=["device_id", "phone", "card_details", "email", "local_session_id","checkout_id","user_id","order_id","session_id"], values=values, promocode=promocode, api_key="abcde", client_id="client_c")
            if risk_response["overall_abusive"] == True:
                abuse = 1
                return jsonify({"error": "PROMO ABUSE - Device or Phone or Card is already associated with more than one account"}), 500
        

            # Prepare order data to send in API call
            order_data = {
                "id": new_order.id,
                "user_id": new_order.user_id,
                "name": new_order.name,
                "email": new_order.email,
                "phone": new_order.phone,
                "card_details": new_order.card_details,
                "promocode": new_order.promocode,
                "device_id": new_order.device_id,
                "ip_address": new_order.ip_address,
                "created_at": str(new_order.created_at), # Format the datetime properly if needed
                "local_session_id": local_session_id
            }


            Thread(
                target=async_finalize_order,
                args=(order_data, "abcde", "client_c"),
                daemon=True
            ).start()
