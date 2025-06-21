  async function runInHouseFingerprint() {
          try {
              const InHouseFingerprint = await import('https://api.rediim.com/static/js/fingerprint_es.js');
              const visitorId = await InHouseFingerprint.sendFingerprint();
              document.getElementById("fingerprint_inhouse").value = visitorId;

          } catch (error) {
              console.error("Error getting InHouseFingerprint:", error);
          }
  }


  async function botDetectionNodeTrail() {
          try {
              const botDetection = await import('https://api.rediim.com/static/js/nodetrail_bot.js');
              const botLabel = await botDetection.detectBots();
              document.getElementById("bot_flag").value = botLabel;

          } catch (error) {
              console.error("Error getting InHouseFingerprint:", error);
          }
  }
