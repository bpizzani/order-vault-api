// fingerprint.js

// Function to collect data
export async function collectData() {
    console.log("Collecting data...");
    try {
        const data = {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            screenRes: `${screen.width}x${screen.height}`,
            colorDepth: screen.colorDepth,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            languages: navigator.languages ? navigator.languages.join(",") : "",
            plugins: navigator.plugins ? Array.from(navigator.plugins).map(p => p.name).join(",") : "",
            hardwareConcurrency: navigator.hardwareConcurrency || "",
            deviceMemory: navigator.deviceMemory || "",
            cookiesEnabled: navigator.cookieEnabled,
            touchSupport: "ontouchstart" in window,
            sessionStorage: typeof sessionStorage !== "undefined" ? sessionStorage.length > 0 : false,
            webGLFingerprint: getWebGLFingerprint(),
            canvasFingerprint: await getCanvasFingerprint()
        };
        console.log("Data collected: ", data);
        return data;
    } catch (error) {
        console.error("Error collecting data:", error);
    }
}

// Function to get WebGL Fingerprint
function getWebGLFingerprint() {
    console.log("Getting WebGL Fingerprint...");
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return 'no-webgl';
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (debugInfo) {
            const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
            console.log("WebGL Fingerprint: ", renderer);
            return renderer;
        }
        return 'no-webgl-info';
    } catch (error) {
        console.error("Error getting WebGL fingerprint:", error);
        return 'no-webgl-info';
    }
}

// Function to get Canvas Fingerprint
function getCanvasFingerprint() {
    console.log("Getting Canvas Fingerprint...");
    return new Promise((resolve, reject) => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const text = "Hello, world!";
        ctx.textBaseline = "top";
        ctx.font = "14px Arial";
        ctx.fillText(text, 2, 2);
        try {
            const fingerprint = canvas.toDataURL();
            console.log("Canvas Fingerprint: ", fingerprint);
            resolve(fingerprint);
        } catch (e) {
            console.error("Error in Canvas fingerprinting:", e);
            reject('Canvas fingerprinting failed');
        }
    });
}

// Function to send fingerprint data to the API
export async function sendFingerprint() {
    console.log("Sending fingerprint data...");
    try {
        const data = await collectData();
        const response = await fetch("https://order-vault-api-cb7f5f7bf4f1.herokuapp.com/api/fingerprint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            const result = await response.json();
            console.log("Response from API: ", result);
            return result.visitorId;
        } else {
            console.error("Error with the API response:", response.status, response.statusText);
            return response.statusText;
        }
    } catch (error) {
        console.error("Error sending fingerprint data:", error);
        return error;
    }
}
