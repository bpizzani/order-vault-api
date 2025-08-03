    	    
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
	            const response = await fetch(`${clientUrl}?${params.toString()}`, {
	                method: "GET",
	                headers: {
	                    "X-API-KEY": apiKey,
			    "X-CLIENT-ID":client_id,
	                }
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

    async function evaluateUserRisk(apiKey, client_id) {
	    
        const clientUrl = "https://api.rediim.com/api/evaluate";
    
	function generateRandomId(prefix = "") {
	    return prefix + Math.random().toString(36).substring(2, 10);
	}
		
	const user_id = localStorage.getItem("user_id");
	const device_id = localStorage.getItem("rediim_fingerprint");
	const local_session_id = localStorage.getItem("local_session_id");

	const promocode = `promo_${Math.floor(Math.random() * 1000)}`;
	const email = `user${Math.floor(Math.random() * 10000)}@example.com`;
	const phone = `555${Math.floor(1000000 + Math.random() * 9000000)}`;
	const session_id = local_session_id;
	const checkout_id = generateRandomId("chk_");
	const order_id = generateRandomId("ord_");
	const card_details = `4444${Math.floor(1000 + Math.random() * 9000)}`;
	
	// Params for evaluation API
	const params = new URLSearchParams({
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
	attribute_types: "device_id,phone,card_details,email,local_session_id,checkout_id,user_id,order_id,session_id"
	});

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

        try {
            const response = await fetch(`${clientUrl}?${params.toString()}`, {
                method: "GET",
                headers: {
                    "X-API-KEY": apiKey,
		    "X-CLIENT-ID":client_id,
                }
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
            
function getUserId() {
    let uid = localStorage.getItem("user_id");
    if (!uid) {
	uid = Math.floor(Math.random() * 1000) + 1; // Random number between 1 and 1000
	localStorage.setItem("user_id", uid);
    }
    return uid;
}
  

    async function runInHouseFingerprint(api_key,client_id, user_id = 0) {
            try {
                const InHouseFingerprint = await import('https://api.rediim.com/static/js/fingerprint_web.js');
                const { visitorId, localSessionId } = await InHouseFingerprint.sendFingerprint(api_key, client_id,user_id);
		rediim_fingerprint = visitorId
                document.getElementById("fingerprint_inhouse").value = visitorId;
		localStorage.setItem("rediim_fingerprint", visitorId);
                localStorage.setItem("local_session_id", localSessionId);

            } catch (error) {
                console.error("Error getting InHouseFingerprint:", error);
            }
    }

    let rediim_fingerprint = null;

    window.onload = async function() {

        const user_id = getUserId();
        const key_api_fingerprint = "trial_abc";
        const client_id_fingerprint = "client_1";
	    
        await runInHouseFingerprint(key_api_fingerprint,client_id_fingerprint, user_id );

	    
        const apiKey = "abcde";
        const client_id = "client_c";
	    
        await evaluateUserRisk(apiKey, client_id);
	    
	//finalizeOrderFrontend(orderData);

        
    };


// api call 
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
	
	// Params for evaluation API
	const params = new URLSearchParams({
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
	attribute_types: "device_id,phone,card_details,email,local_session_id,checkout_id,user_id,order_id,session_id"
	});

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
	    
      //const response = await fetch('https://order-vault-client-webapp-13ee822f0ba9.herokuapp.com/checkout', {
      //  method: 'POST',
      //  headers: {
      //    'Content-Type': 'application/json'
      //  },
      //  body: JSON.stringify(data)
      //});

      //const result = await response.json();
      //document.getElementById('response').textContent = JSON.stringify(result, null, 2);
    });
