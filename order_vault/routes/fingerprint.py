from flask import Blueprint, request, jsonify, current_app
import hashlib

fingerprint_bp = Blueprint(
    "fingerprint", __name__, url_prefix="/api/fingerprint"
)

@fingerprint_bp.route("", methods=["GET","POST","OPTIONS"])
def fingerprint():
    if request.method == "OPTIONS":
        return "", 200
    data = request.get_json(silent=True) or {}
    features = [
        str(data.get(k, "")) for k in (
            "userAgent","platform","screenRes","colorDepth",
            "timezone","languages","plugins",
            "webGLFingerprint","canvasFingerprint"
        )
    ]
    vid = hashlib.sha256("|".join(features).encode()).hexdigest()
    return jsonify({"visitorId": vid}), 200
