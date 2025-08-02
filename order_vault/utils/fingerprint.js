<script>
    async function evaluateUserRisk() {
        const apiKey = "abcde";  // Replace with your actual API key
        const clientUrl = "https://api.rediim.com/api/evaluate";
	const client_id = "client_c"

		function generateRandomId(prefix = "") {
		    return prefix + Math.random().toString(36).substring(2, 10);
		}
		
	const user_id = localStorage.getItem("user_id");
	const device_id = localStorage.getItem("rediim_fingerprint");
	const local_session_id = localStorage.getItem("local_session_id");
	    
        // Sample values (replace with real ones from your app)
	const params = new URLSearchParams({
	    promocode:`promo_{Math.floor(Math.random() * 1000)}`,
	    device_id: device_id,
	    email: `user${Math.floor(Math.random() * 10000)}@example.com`,
	    phone: `555${Math.floor(1000000 + Math.random() * 9000000)}`,
	    session_id: local_session_id,
	    local_session_id: local_session_id,
	    user_id: user_id,
	    checkout_id: generateRandomId("chk_"),
	    order_id: generateRandomId("ord_"),
	    attribute_types: "device_id,phone,card_details,email,local_session_id,checkout_id,user_id,order_id,session_id"
	});

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
            }

        } catch (err) {
            console.error("Evaluation error:", err);
            alert("An error occurred while evaluating risk.");
        }
    }

    function getUserId() {
            let uid = localStorage.getItem("user_id");
            if (!uid) {
                uid = crypto.randomUUID();
                localStorage.setItem("user_id", uid);
            }
            return uid;
        }
  
    async function runInHouseFingerprint() {
            try {
                const InHouseFingerprint = await import('https://api.rediim.com/static/js/fingerprint_web.js');
                const { visitorId, localSessionId } = await InHouseFingerprint.sendFingerprint(key_api, client_id, user_id);

            } catch (error) {
                console.error("Error getting InHouseFingerprint:", error);
            }
    }

    window.onload = function() {
        const key_api = "abcd";
        const client_id = "meeder";
        const user_id = getUserId();
        runInHouseFingerprint();
        evaluateUserRisk();
    };



 </script>
