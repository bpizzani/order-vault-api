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
        
        let formFillingStartTime = null;
        let formFillingEndTime = null;
        let formFillingTime = 0;
        
        const form = document.querySelector("form");  // Assuming your form element
        
        // Listen for the input events to start and end form filling
        form.addEventListener("focusin", (event) => {
            if (formFillingStartTime === null) {
                formFillingStartTime = new Date().getTime();
            }
        });
        
        form.addEventListener("input", (event) => {
            formFillingEndTime = new Date().getTime();
            formFillingTime = formFillingEndTime - formFillingStartTime;
        });
        
        // Monitor form filling speed (too fast means bot)
        setTimeout(() => {
            if (formFillingTime < 5000 && formFillingTime > 0) {
                console.warn("🚨 Bot detected: Form filled too quickly");
                // You can flag the user as a bot here, show a warning, or prevent submission
                isBot = true;
                return isBot ? "Yes" : "No"
            }
        }, 10000);  // Set a threshold for form filling speed, e.g., 3 seconds
        
        
    return isBot ? "Yes" : "No"
    }
