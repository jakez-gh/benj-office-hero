import * as TaskManager from 'expo-task-manager';
import * as Location from 'expo-location';
import { postLocation } from '@office-hero/api-client';

const LOCATION_TASK_NAME = 'OFFICE_HERO_LOCATION_TASK';

// globals to hold token/vehicleId for background callback
declare global {
  var __OFFICE_HERO_TOKEN: string | null;
  var __OFFICE_HERO_VEHICLE_ID: string | null;
}

// initialize globals
global.__OFFICE_HERO_TOKEN = null;
global.__OFFICE_HERO_VEHICLE_ID = null;

TaskManager.defineTask(LOCATION_TASK_NAME, async ({ data, error }) => {
  if (error) {
    console.error('Location task error', error);
    return;
  }
  if (data) {
    const { locations } = data as any;
    if (locations && locations.length > 0) {
      const loc = locations[0];
      const token = global.__OFFICE_HERO_TOKEN;
      const vehicleId = global.__OFFICE_HERO_VEHICLE_ID;
      if (token && vehicleId) {
        try {
          await postLocation(token, vehicleId, loc.coords.latitude, loc.coords.longitude);
        } catch (e) {
          console.error('failed to post location', e);
        }
      }
    }
  }
});

export async function startLocationTracking(token: string, vehicleId: string) {
  global.__OFFICE_HERO_TOKEN = token;
  global.__OFFICE_HERO_VEHICLE_ID = vehicleId;

  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status !== 'granted') {
    console.warn('Foreground location permission not granted');
    return;
  }
  const bg = await Location.requestBackgroundPermissionsAsync();
  if (bg.status !== 'granted') {
    console.warn('Background location permission not granted');
    return;
  }

  const hasStarted = await Location.hasStartedLocationUpdatesAsync(LOCATION_TASK_NAME);
  if (!hasStarted) {
    await Location.startLocationUpdatesAsync(LOCATION_TASK_NAME, {
      accuracy: Location.Accuracy.Balanced,
      showsBackgroundLocationIndicator: true,
      foregroundService: {
        notificationTitle: 'Office Hero',
        notificationBody: 'Tracking location in background',
      },
    });
  }
}

export async function stopLocationTracking() {
  const hasStarted = await Location.hasStartedLocationUpdatesAsync(LOCATION_TASK_NAME);
  if (hasStarted) {
    await Location.stopLocationUpdatesAsync(LOCATION_TASK_NAME);
  }
}
