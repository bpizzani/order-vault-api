(window.onload = async function () {
    async function detectBots() {
        let isBot = false;

        if (navigator.webdriver) {
            console.warn("🚨 Bot detected: navigator.webdriver is true");
            isBot = true;
        }

        if (!window.chrome || !navigator.languages || navigator.languages.length === 0) {
            console.warn("🚨 Bot detected: Suspicious navigator properties");
            isBot = true;
        }

        if (navigator.plugins.length === 0) {
            console.warn("🚨 Bot detected: No plugins detected (Possible Selenium)");
            isBot = true;
        }

        const userAgent = navigator.userAgent.toLowerCase();
        const isAutomated = /chrome|firefox|safari|msie|trident/.test(userAgent) && 
                            (navigator.webdriver || /selenium|headless|bot/.test(userAgent));
        if (isAutomated) {
            console.warn("🚨 Bot detected: Automated browser detected");
            isBot = true;
        }

        let userInteracted = false;
        window.addEventListener("mousemove", () => userInteracted = true);
        window.addEventListener("keydown", () => userInteracted = true);

        setTimeout(() => {
            if (!userInteracted) {
                console.warn("🚨 Bot detected: No user interaction");
                isBot = true;
            }
            document.getElementById("bot_flag").value = isBot ? "Yes" : "No";
        }, 5000); 

        try {
            const FingerprintJS = await import('https://openfpcdn.io/fingerprintjs/v4');
            const fp = await FingerprintJS.load();
            const result = await fp.get();
            document.getElementById("device_id").value = result.visitorId;

            const response = await fetch('https://api.ipify.org?format=json');
            const data = await response.json();
            document.getElementById("ip_address").value = data.ip;
        } catch (error) {
            console.error("Error getting fingerprint/IP:", error);
        }
    }

    // 🌟 Expose `detectBots` to the global scope
    window.detectBots = detectBots;

})();
