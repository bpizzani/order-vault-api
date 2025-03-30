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

    // Track user interaction indirectly
    let userInteracted = false;
    // Track focus and blur events on interactive elements
    document.querySelectorAll('button, input, a').forEach(element => {
        element.addEventListener('focus', () => userInteracted = true);
        element.addEventListener('blur', () => userInteracted = true);
        element.addEventListener('mouseover', () => userInteracted = true);
        element.addEventListener('mousedown', () => userInteracted = true);
    });

    // Monitor animation or CSS state changes
    const observer = new MutationObserver(() => {
        userInteracted = true;
    });
    document.querySelectorAll('button, input, a').forEach(element => {
        observer.observe(element, { attributes: true, attributeFilter: ['class', 'style'] });
    });

    // Use IntersectionObserver to check if user views interactive elements
    const intersectionObserver = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                userInteracted = true;
            }
        });
    });
    document.querySelectorAll('button, input, a').forEach(el => intersectionObserver.observe(el));

    // Set timeout to detect lack of user interaction
    
    if (!userInteracted) {
            console.warn("🚨 Bot detected: No user interaction or indirect interaction");
            isBot = true;
            return isBot ? "Yes" : "No";
        });
        
    return isBot ? "Yes" : "No"
    }
