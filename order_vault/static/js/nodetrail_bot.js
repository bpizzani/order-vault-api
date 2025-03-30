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
        let inputFields = document.querySelectorAll('input, textarea'); // Select all form fields
        let totalFields = inputFields.length;
        let filledFields = 0;  // To track how many fields have been filled
        
        // Monitor when the user starts typing (start time)
        inputFields.forEach(input => {
            input.addEventListener('focus', function() {
                if (formStartTime === 0) {  // Only set the start time once
                    formStartTime = Date.now();
                }
            });
        
            // Monitor when user types in each field
            input.addEventListener('input', function() {
                filledFields++;  // Increase filled fields count when user interacts with a field
                if (filledFields === totalFields) {  // All fields are filled
                    formEndTime = Date.now();
                    const formFillingTime = formEndTime - formStartTime;
        
                    // Check if form was filled too quickly (e.g., under 3 seconds)
                    if (formFillingTime < 10000) {  // 3 seconds threshold (adjust as needed)
                        console.warn("🚨 Bot detected: Form filled too quickly");
                        isBot = true;
                    }
                }
            });
        });
        
        
    return isBot ? "Yes" : "No"
    }
