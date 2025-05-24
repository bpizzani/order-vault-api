def select_features(data):
    keys = [
        "userAgent","platform","screenRes","colorDepth",
        "timezone","languages","plugins",
        "webGLFingerprint","canvasFingerprint"
    ]
    return [str(data.get(k, "")) for k in keys]
