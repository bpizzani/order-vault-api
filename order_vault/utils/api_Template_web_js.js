
  -- get Fingerprint

    let rediim_fingerprint = null;
    async function runInHouseFingerprint(api_key,client_id, user_id = 0) {
            try {
                const InHouseFingerprint = await import('https://api.rediim.com/static/js/fingerprint_web.js');
                const { visitorId, localSessionId } = await InHouseFingerprint.sendFingerprint(api_key, client_id,user_id);
		rediim_fingerprint = visitorId
				
		localStorage.setItem("rediim_fingerprint", visitorId);
        localStorage.setItem("local_session_id", localSessionId);

            } catch (error) {
                console.error("Error getting InHouseFingerprint:", error);
            }
    }


---- JS

	async function finalizeOrderFrontend(orderData, api_key, client_id ) {
	    try {
	        const response = await fetch("https://api.rediim.com/finalize-order", {
	            method: "POST",
	            headers: {
	                "Content-Type": "application/json",
	                "X-API-KEY": api_key,
	                "X-CLIENT-ID": client_id
	            },
	            body: JSON.stringify(orderData)
	        });
	
	        const result = await response.json();
	
	        if (!response.ok) {
	            throw new Error(result.error || "Failed to finalize order");
	        }
	
	        console.log("✅ Order Finalized:", result);
	    } catch (error) {
	        console.error("⚠️ Finalize Order Error:", error);
	    }
	}

    async function evaluateUserRiskApi(params, orderData, apiKey, client_id) {
	    
	        const clientUrl = "https://api.rediim.com/api/evaluate";
		    
	        try {
	            const response = await fetch("https://api.rediim.com/api/evaluate", {
	                method: "POST",
	                headers: {
	                    "X-API-KEY": apiKey,
			             "X-CLIENT-ID":client_id,
	                },
                    body: JSON.stringify(params)
	            });
	
	            const data = await response.json();
	            
	            if (!response.ok) {
	                throw new Error(data.error || "Evaluation failed");
	            }
	
	            console.log("Risk Evaluation Results:", data);
	
	            if (data.overall_abusive) {
	                alert("⚠️ Risk detected! This user may be abusing the promocode.");
	            } else {
	                alert("✅ User is clean.");
			finalizeOrderFrontend(orderData, apiKey, client_id);
	            }
	
	        } catch (err) {
	            console.error("Evaluation error:", err);
	            alert("An error occurred while evaluating risk.");
	        }
	}	   


window.onload = async function() {

        const user_id = getUserId(); -- Optional, but useful to have
        const key_api_fingerprint = "trial_abc";
        const client_id_fingerprint = "client_1";
	    
        await runInHouseFingerprint(key_api_fingerprint,client_id_fingerprint, user_id );

	    
        const apiKey = "abcde";
        const client_id = "client_c";
	    
    };


    const form = document.getElementById('checkout-form');
    form.addEventListener('submit', async (e) => {
	    
	function generateRandomId(prefix = "") {
	    return prefix + Math.random().toString(36).substring(2, 10);
	}
	    
      e.preventDefault();
      const data = {
        email: form.email.value,
        phone: form.phone.value,
        name: form.name.value,
        card: form.card.value,
        promo: form.promo.value,
	user_id: localStorage.getItem("user_id"),
	device_id: rediim_fingerprint,
	local_session_id: localStorage.getItem("local_session_id"),
      };

	const user_id = localStorage.getItem("user_id");
	const device_id = rediim_fingerprint;
	const local_session_id = localStorage.getItem("local_session_id");

	const promocode = form.promo.value;
	const email = form.email.value;
	const phone =  form.phone.value;
	const session_id = local_session_id;
	const checkout_id = generateRandomId("chk_");
	const order_id = generateRandomId("ord_");
	const card_details = form.card.value;

	const params = {
	promocode,
	device_id,
	email,
	phone,
	card_details,
	session_id,
	local_session_id,
	user_id,
	checkout_id,
	order_id,
	attribute_types: "device_id,phone,card_details,email,local_session_id"
	};

	// Build orderData for finalize-order API
	const orderData = {
	id: order_id, // or use checkout_id depending on your backend
	user_id,
	name: `User ${user_id}`, // optional mock
	email,
	phone,
	card_details,
	promocode,
	device_id,
	local_session_id
	};
	const apiKey = "abcde";
	const client_id = "client_c";
	    
	evaluateUserRiskApi(params, orderData, apiKey, client_id);
    });
  </script>


