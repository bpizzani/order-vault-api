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

        let formStartTime = 0;
        let formEndTime = 0;
        let isBot = false;
        
        // Monitor when the form starts to be filled
        document.querySelector('form').addEventListener('focus', function() {
            if (formStartTime === 0) {  // Only set the start time once
                formStartTime = Date.now();
            }
        }, true);
        
        // Monitor form filling (e.g., user interacts with fields)
        document.querySelectorAll('input, textarea').forEach(input => {
            input.addEventListener('input', function() {
                // Do something when fields are filled (like tracking)
            });
        });
        
        // Monitor form submission
        document.querySelector('form').addEventListener('submit', function(event) {
            formEndTime = Date.now();
            
            const formFillingTime = formEndTime - formStartTime;
            
            // Check if form was filled too quickly
            if (formFillingTime < 3000) {
                console.warn("🚨 Bot detected: Form filled too quickly");
                isBot = true;
                event.preventDefault();  // Prevent form submission if you want to block it
            }
        });
        
        
    return isBot ? "Yes" : "No"
    }
