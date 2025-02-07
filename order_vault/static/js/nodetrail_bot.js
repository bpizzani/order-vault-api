export async function detectBots() {

        let isBot = false;

        if (navigator.webdriver) {
            console.warn("🚨 Bot detected: navigator.webdriver is true");
            isBot = true;
            return isBot ? "Yes" : "No"
        }

        if (!window.chrome || !navigator.languages || navigator.languages.length === 0) {
            console.warn("🚨 Bot detected: Suspicious navigator properties");
            isBot = true;
            return isBot ? "Yes" : "No"
        }

        if (navigator.plugins.length === 0) {
            console.warn("🚨 Bot detected: No plugins detected (Possible Selenium)");
            isBot = true;
            return isBot ? "Yes" : "No"
        }

        const userAgent = navigator.userAgent.toLowerCase();
        const isAutomated = /chrome|firefox|safari|msie|trident/.test(userAgent) && 
                            (navigator.webdriver || /selenium|headless|bot/.test(userAgent));
        if (isAutomated) {
            console.warn("🚨 Bot detected: Automated browser detected");
            isBot = true;
            return isBot ? "Yes" : "No"
        }

        let userInteracted = false;
        window.addEventListener("mousemove", () => userInteracted = true);
        window.addEventListener("keydown", () => userInteracted = true);

        setTimeout(() => {
            if (!userInteracted) {
                console.warn("🚨 Bot detected: No user interaction");
                isBot = true;
                return isBot ? "Yes" : "No"
            }
        }, 5000); 

        return isBot ? "Yes" : "No"
    }
