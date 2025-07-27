<script>
	let user_id = null;
  
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
      	key_api = "abcd";
        client_id = "meeder";
		user_id = getUserId();
        runInHouseFingerprint();
    };

 </script>
