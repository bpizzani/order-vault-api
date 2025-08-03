
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
