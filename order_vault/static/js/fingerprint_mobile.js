// fingerprint.js
import DeviceInfo from 'react-native-device-info';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform, Dimensions } from 'react-native';

export async function collectData() {
  try {
    const local_user_id = await getOrCreateUserId();

    const data = {
      userAgent: await DeviceInfo.getUserAgent(),
      androidId: await DeviceInfo.getAndroidId(),
      deviceId: DeviceInfo.getDeviceId(),
      brand: DeviceInfo.getBrand(),
      systemName: DeviceInfo.getSystemName(),
      systemVersion: DeviceInfo.getSystemVersion(),
      model: DeviceInfo.getModel(),
      manufacturer: await DeviceInfo.getManufacturer(),
      isEmulator: await DeviceInfo.isEmulator(),
      isTablet: DeviceInfo.isTablet(),
      timezone: DeviceInfo.getTimezone(),
      uniqueId: DeviceInfo.getUniqueId(),
      screenRes: `${Dimensions.get('screen').width}x${Dimensions.get('screen').height}`,
      fontScale: Dimensions.get('screen').scale,
      deviceMemory: DeviceInfo.getTotalMemorySync(),
      apiLevel: Platform.OS === 'android' ? await DeviceInfo.getApiLevel() : null,
      local_user_id
    };

    return data;
  } catch (error) {
    console.error('Error collecting fingerprint data:', error);
    return {};
  }
}

async function getOrCreateUserId() {
  try {
    let uid = await AsyncStorage.getItem("user_id");
    if (!uid) {
      uid = crypto.randomUUID?.() || Math.random().toString(36).substring(2);
      await AsyncStorage.setItem("user_id", uid);
    }
    return uid;
  } catch (e) {
    console.error("Error accessing storage:", e);
    return "unknown";
  }
}

export async function sendFingerprint(api_key, client_id, user_id = null) {
  try {
    const data = await collectData();

    const response = await fetch("https://api.rediim.com/api/fingerprint", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-KEY": api_key,
        "X-CLIENT-ID": client_id,
        "user_identifier_client": user_id || ""
      },
      body: JSON.stringify(data)
    });

    if (response.ok) {
      const result = await response.json();
      return result.visitorId;
    } else {
      console.error("Server error:", response.statusText);
      return null;
    }
  } catch (error) {
    console.error("Error sending fingerprint:", error);
    return null;
  }
}
