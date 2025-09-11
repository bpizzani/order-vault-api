// fingerprint.js

// Function to collect data
export async function collectData() {
    console.log("Collecting data...");
    try {
        const cookies = document.cookie || "";
        const sessionMatch = cookies.match(/session=([^;]+)/);
        const sessionId = sessionMatch ? sessionMatch[1] : "";
        const local_session_id = getOrCreateSessionId();

        const data = {
            userAgent: navigator.userAgent,
            webdriver: navigator.webdriver,
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
            canvasFingerprint: await getCanvasFingerprint(),
                    // Optionally include session ID directly if accessible
             cookies,
             sessionId,
             bot_framework: /selenium|headless|bot/i.test(navigator.userAgent),
             local_session_id
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


function getOrCreateSessionId() {
    let uid = localStorage.getItem("local_session_id");
    if (!uid) {
        uid = crypto.randomUUID();
        localStorage.setItem("local_session_id", uid);
    }
    return uid;
}

async function runFingerprintJs() {
    try {
        const FingerprintJS = await import('https://openfpcdn.io/fingerprintjs/v4');
        const fp = await FingerprintJS.load();
        const result = await fp.get();
        return result.visitorId;
    } catch (error) {
        console.error("Error getting fingerprint:", error);
        return null;
    }
}

async function runThumbmarkJs() {
  try {
    await import('https://cdn.jsdelivr.net/npm/@thumbmarkjs/thumbmarkjs/dist/thumbmark.umd.js');
    const tm = new ThumbmarkJS.Thumbmark();
    const result = await tm.get();
    const thumbmark = result.thumbmark;
    return thumbmark;
  } catch (err) {
    console.error("Error loading ThumbmarkJS:", err);
  }
}


function appendHiddenInput(name, value) {
  const form = document.querySelector("form");
  if (!form) {
    console.warn('⚠ appendHiddenInput: <form> not found. Skipping input ${name}');
    return;
  }
  const input = document.createElement("input");
  input.type = "hidden";
  input.name = name;
  input.value = value;
  form.appendChild(input);
}

function appendHiddenInputOrderForm(name, value) {
  const form = document.getElementById("order-form");
  if (!form) {
    console.error("Form not found: #order-form");
    return;
  }

  const input = document.createElement("input");
  input.type = "hidden";
  input.name = name;
  input.value = value;
  form.appendChild(input);
}

export async function getAccessToken() { // Client side API
  try {
    const res = await fetch("/rediim/token", {
      method: "POST",
      credentials: "include"
    });

    if (!res.ok) {
      console.warn("Failed to get access token:", res.status, res.statusText);
      return null; // return null instead of throwing
    }

    const data = await res.json();
    return data.access_token || null;
  } catch (err) {
    console.error("Error fetching access token:", err);
    return null;
  }
}

// Function to send fingerprint data to the API
export async function sendFingerprint(pk_key, client_id, type = null, user_id = null, coupon = null) {
    let rediim_fingerprint = localStorage.getItem("rediim_fingerprint");
    console.log("Sending fingerprint data...");
    if (!rediim_fingerprint || rediim_fingerprint === "undefined" || rediim_fingerprint === "" || rediim_fingerprint === "null" || rediim_fingerprint === null) {
            try {
            const data = await collectData();
            const fingerprint_js_visitorId = await runFingerprintJs();
            const thumbmark_js_visitorId = await runThumbmarkJs();
            data.fingerprint_js_visitor_id = fingerprint_js_visitorId;
            data.thumbmark_js_visitor_id = thumbmark_js_visitorId;
            data.coupon = coupon;
            data.call_type = type;
                
            const accessToken = await getAccessToken();
            const response = await fetch("https://api.rediim.com/api/fingerprint", {
                method: "POST",
                credentials: "include",
                headers: { "Content-Type": "application/json",
                          "Authorization": `Bearer ${accessToken}`,
                         "X-PUBLISHABLE-KEY": pk_key,
                         "X-CLIENT-ID": client_id,
                         "user_identifier_client": user_id},
    
                body: JSON.stringify(data)
            });

                
            if (response.ok) {
                const result = await response.json();
                appendHiddenInput("fingerprint_js_visitor_id", fingerprint_js_visitorId);
                appendHiddenInput("thumbmark_js_visitor_id", thumbmark_js_visitorId);
                appendHiddenInput("inhouse_js_visitor_id", result.visitorId);
                appendHiddenInput("local_session_id", data.local_session_id);
                localStorage.setItem("rediim_fingerprint", thumbmark_js_visitorId); // result.visitorId
                localStorage.setItem("local_session_id", data.local_session_id);
                console.log("Response from API: ", result);
                return {
                        visitorId: result.visitorId,
                        localSessionId: data.local_session_id
                    };
            } else {
                console.error("Error with the API response:", response.status, response.statusText);
                return response.statusText;
            }
        } catch (error) {
            console.error("Error sending fingerprint data:", error);
            return error;
        }
    } else { 
        appendHiddenInput("inhouse_js_visitor_id", localStorage.getItem("rediim_fingerprint"));
        appendHiddenInput("local_session_id", localStorage.getItem("local_session_id"));
        return {
                visitorId: localStorage.getItem("rediim_fingerprint"),
                localSessionId: localStorage.getItem("local_session_id")
            }
    }
}
