(async function () {
    async function collectData() {
        return {
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
            localStorage: typeof localStorage !== "undefined" ? localStorage.length > 0 : false,
            webGLFingerprint: getWebGLFingerprint(),
            canvasFingerprint: await getCanvasFingerprint()
        };
    }

      // WebGL Fingerprinting
      function getWebGLFingerprint() {
          const canvas = document.createElement('canvas');
          const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
          if (!gl) return 'no-webgl';
          const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
          if (debugInfo) {
              return gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
          }
          return 'no-webgl-info';
      }

      // Canvas Fingerprinting
      function getCanvasFingerprint() {
          return new Promise((resolve, reject) => {
              const canvas = document.createElement('canvas');
              const ctx = canvas.getContext('2d');
              const text = "Hello, world!";
              ctx.textBaseline = "top";
              ctx.font = "14px Arial";
              ctx.fillText(text, 2, 2);
              try {
                  const fingerprint = canvas.toDataURL();
                  resolve(fingerprint);
              } catch (e) {
                  reject('Canvas fingerprinting failed');
              }
          });
      }

    async function sendFingerprint() {
        const data = await collectData();
        const response = await fetch("https://order-vault-api-cb7f5f7bf4f1.herokuapp.com/api/fingerprint", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        const result = await response.json();

        // Store in a hidden input field
        document.querySelectorAll("[data-fingerprint]").forEach(el => el.value = result.visitorId);
    }

    sendFingerprint();
})();
