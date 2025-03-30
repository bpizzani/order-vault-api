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
        
        // Monitor for user interaction on the page
        document.addEventListener("mousemove", () => userInteracted = true);
        document.addEventListener("keydown", () => userInteracted = true);
        document.addEventListener("focusin", () => userInteracted = true);
        document.addEventListener("click", () => userInteracted = true);  // Detect clicks
        
        
        // Form fields you want to track
        const formFields = document.querySelectorAll("#name, #email, #phone, #card_details");
        
        formFields.forEach((field) => {
            field.addEventListener("input", (event) => {
                // Check if there was no user interaction before input
                if (!userInteracted) {
                    console.warn("🚨 Bot detected: Text input without user interaction");
                    // Optionally, clear the field or prevent further input
                    event.target.value = '';  // Clear the text field
                    isBot = true;
                    return isBot ? "Yes" : "No"
                }
            });
        });

        // Optionally monitor form submission if needed
        document.querySelector("form").addEventListener("submit", (event) => {
            if (!userInteracted) {
                console.warn("🚨 Bot detected: Submit button clicked without user interaction");
                // Prevent the form submission if it's a bot
                event.preventDefault();
                isBot = true;
                return isBot ? "Yes" : "No"
            }
        });
                
    return isBot ? "Yes" : "No"
    }
