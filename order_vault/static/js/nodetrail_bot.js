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

            // Track user interaction and form field changes
            let userInteracted = false;
            let formFillingStartTime = Date.now();
            let formFillingTime = 0;
        
            // Track focus and blur events on interactive form elements
            const formElements = document.querySelectorAll('input, textarea, select');
            formElements.forEach((element) => {
                element.addEventListener('focus', () => userInteracted = true);
                element.addEventListener('blur', () => userInteracted = true);
                element.addEventListener('input', () => {
                    if (formFillingTime === 0) {
                        formFillingTime = Date.now() - formFillingStartTime; // Time taken for form filling
                    }
                });
            });
        
            // Monitor form filling speed (too fast means bot)
            setTimeout(() => {
                // If the form filling time is too fast (i.e., less than 1 second), flag as bot
                if (formFillingTime < 1000) {
                    console.warn("🚨 Bot detected: Form filled too quickly");
                    isBot = true;
                    return isBot ? "Yes" : "No";
                }
            }, 1000);
        
    return isBot ? "Yes" : "No"
    }
