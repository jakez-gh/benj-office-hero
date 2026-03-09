---
slice: mobile-scaffold
project: office-hero
lld: user/slices/010-slice.mobile-scaffold.md
dependencies: [1, 1a, 5]
projectState: Slices 1-5 complete (Python scaffold, database foundation, auth/RBAC, observability, frontend scaffold). Ready to initialize React Native Expo mobile app with Android build configuration, location permissions, and navigation scaffolding.
dateCreated: 20260308
dateUpdated: 20260308
status: not_started
---

## Context Summary

- Working on **Slice 6: Mobile Scaffold** — initializing React Native Expo with Android build config, location permissions, navigation scaffolding
- Current state: pnpm monorepo ready (Slice 5); can add tech-mobile app with Expo setup
- Deliverable: Functional Expo app for Android with Expo Go for development, location permission handling, React Navigation stack, and integration with shared @office-hero/api-client
- Next: Slices 7-19 (route view, job entry, location tracking) build on this scaffold

---

## Task Breakdown

### Phase 1: Expo Project Initialization & Android Configuration

- [ ] **Initialize Expo project with TypeScript**
  - [ ] Command: `npx create-expo-app tech-mobile --template expo-template-blank-typescript` from `apps/` directory
  - [ ] Or manually:
    - Create `apps/tech-mobile/` directory
    - Copy Expo starter template with TypeScript support
    - Initialize git within the app if desired
  - [ ] Verify structure: `app.json`, `app.tsx`, `tsconfig.json` exist
  - [ ] Success: `npm start` or `npx expo start` runs without errors; Expo Metro bundler starts

- [ ] **Configure app.json for Android**
  - [ ] Update `app.json`:
    - `name`: "Office Hero"
    - `slug`: "office-hero"
    - `version`: "0.1.0"
    - Add `android` section:
      - `package`: "com.officehero.tech"
      - `permissions`: `["INTERNET", "ACCESS_COARSE_LOCATION", "ACCESS_FINE_LOCATION", "ACCESS_BACKGROUND_LOCATION"]`
      - `adaptiveIcon`: (optional, for app launcher)
  - [ ] Success: `app.json` is valid JSON; `npx eas build` can read it without errors

- [ ] **Set up Expo environment & credentials**
  - [ ] Create `.env.local` in tech-mobile:
    - `EXPO_PUBLIC_API_BASE_URL=http://localhost:8000` (or empty for Expo Go to connect to host machine)
  - [ ] Create `eas.json` in tech-mobile:
    - Configure preview build (APK): `expo.channels: "preview"`
    - Configure production build (AAB): `expo.channels: "production"`
    - Android version code & name
  - [ ] Success: EAS Build can read configuration

- [ ] **Test Expo project structure**
  - [ ] Run: `npx expo start` from tech-mobile directory
  - [ ] Verify Metro bundler starts (no errors)
  - [ ] Scan QR code with Expo Go on Android emulator or real device
  - [ ] Verify app launches with "Open up App.tsx to start working on your app" text
  - [ ] Success: Expo Go loads app successfully

---

### Phase 2: Location Permissions Setup

- [ ] **Install location library**
  - [ ] Add: `expo-location` via `npx expo install expo-location`
  - [ ] Add types: `npm install --save-dev @types/expo-location` (if using TypeScript)
  - [ ] Success: `import * as Location from 'expo-location'` works without errors

- [ ] **Create location permissions service**
  - [ ] Create `src/services/locationService.ts`:
    - Function `requestForegroundPermissions()`:
      - Call `Location.requestForegroundPermissionsAsync()`
      - Returns {status: 'granted' | 'denied'}
      - On success, start tracking via `Location.watchPositionAsync()` with callback
      - On deny, return error state
    - Function `requestBackgroundPermissions()`:
      - Call `Location.requestBackgroundPermissionsAsync()`
      - Requires user manual action (cannot be done programmatically on Android 10+)
      - Returns status
    - Function `getCurrentLocation()`:
      - Returns current lat/lon or null if permission not granted
  - [ ] Success: Functions export without errors; TypeScript types correct

- [ ] **Handle location permission UI & alerts**
  - [ ] Create `src/components/PermissionAlert.tsx`:
    - Alert component showing:
      - "Office Hero needs your location to track your route"
      - Button "Allow Once" (foreground only)
      - Button "Allow All the Time" (with explanation: "You must manually open Settings > Apps > Office Hero > Permissions > Location > Allow all the time")
      - Button "Don't Allow"
  - [ ] On "Allow Once": call requestForegroundPermissions()
  - [ ] On "Allow All the Time": show instruction alert, direct to Settings
  - [ ] On "Don't Allow": dismiss alert, continue without location
  - [ ] Success: Alert component renders; buttons trigger appropriate flows

- [ ] **Test location permissions (unit & integration tests)**
  - [ ] Create `src/services/__tests__/locationService.test.ts`:
    - Test requestForegroundPermissions returns status
    - Test requestBackgroundPermissions returns status
    - Mock `expo-location` module
  - [ ] Create `src/components/__tests__/PermissionAlert.test.tsx`:
    - Test alert renders
    - Test "Allow Once" button calls requestForegroundPermissions
    - Test "Allow All the Time" shows instruction alert
  - [ ] Success: `npm test` passes location permission tests

---

### Phase 3: React Navigation & Screen Scaffolds

- [ ] **Install React Navigation libraries**
  - [ ] Add: `@react-navigation/native`, `@react-navigation/stack`, `react-native-screens`, `react-native-safe-area-context`
  - [ ] Run: `npx expo install <package>` for each
  - [ ] Success: All packages importable without errors

- [ ] **Create navigation stack**
  - [ ] Create `src/navigation/RootNavigator.tsx`:
    - Define `RootStackParamList` type with routes: LoginScreen, RouteScreen
    - Create `Stack.Navigator` with initial route: "Login" (unauthenticated) or "Route" (authenticated)
    - Success: Navigator compiles without errors

- [ ] **Create screens**
  - [ ] Create `src/screens/LoginScreen.tsx`:
    - Form with email + password fields
    - Submit button (calls useAuth().login)
    - Shows loading state during request
    - Shows error message on failure
    - On success, navigates to RouteScreen
  - [ ] Create `src/screens/RouteScreen.tsx`:
    - Header showing "Your Route for Today"
    - Placeholder: list of jobs (empty or mocked)
    - Job card showing: customer name, address, status
    - Bottom button: "Start Route" (placeholder)
    - Top-right: logout button
  - [ ] Success: Both screens render without errors

- [ ] **Wire auth context into navigation**
  - [ ] In `App.tsx`:
    - Check `useAuth().token` to determine initial route
    - If no token: show LoginScreen stack
    - If token exists: show RouteScreen stack
  - [ ] Success: Navigation switches based on auth state

- [ ] **Test navigation & screens (unit & integration tests)**
  - [ ] Create `src/screens/__tests__/LoginScreen.test.tsx`:
    - Test form renders with email and password fields
    - Test submit calls useAuth().login
    - Test loading state during request
  - [ ] Create `src/screens/__tests__/RouteScreen.test.tsx`:
    - Test screen renders "Your Route for Today" header
    - Test logout button is visible
  - [ ] Create `src/navigation/__tests__/RootNavigator.test.tsx`:
    - Test navigator initializes without errors
    - Test route switching based on auth state (mocked useAuth)
  - [ ] Success: `npm test` passes navigation tests

---

### Phase 4: API Client & Auth Integration

- [ ] **Configure API client in monorepo**
  - [ ] Ensure tech-mobile `package.json` has dependency: `@office-hero/api-client` (from packages/)
  - [ ] Create `src/api.ts`:
    - Export singleton: `export const api = new ApiClient(process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000')`
    - Or use `getBaseUrl()` to detect platform-specific localhost (Expo Go requires special handling on Android)
  - [ ] Success: API client singleton works on both Expo Go and native build

- [ ] **Implement useAuth hook for mobile**
  - [ ] Create `src/contexts/AuthContext.tsx` (similar to web, but mobile-specific):
    - Use AsyncStorage (instead of localStorage) for token persistence
    - Implement login/refresh/logout methods
    - Implement 401 → refresh → retry flow
  - [ ] Or import useAuth from shared location if monorepo supports it
  - [ ] Success: Hook works with mobile storage (AsyncStorage)

- [ ] **Handle deep linking (placeholder)**
  - [ ] Create stub for deep linking config (e.g., app links for password reset)
  - [ ] Not fully implemented in Slice 6, but structure in place for Slice 7+
  - [ ] Success: Structure exists for future expansion

- [ ] **Test API integration (integration tests)**
  - [ ] Create `src/__tests__/api-integration.test.ts`:
    - Test API client singleton creation
    - Mock auth endpoints, test login/refresh/logout flows
  - [ ] Success: Tests pass with mocked API

---

### Phase 5: Build Configuration & EAS Setup

- [ ] **Configure EAS Build for preview (APK)**
  - [ ] In `eas.json`, configure preview build:

    ```json
    {
      "build": {
        "preview": {
          "android": {
            "buildType": "apk"
          }
        }
      }
    }
    ```

  - [ ] Create EAS Build project: `eas build:configure` (if not already done)
  - [ ] Success: `eas build --platform android --profile preview` can be run

- [ ] **Configure EAS Build for production (AAB)**
  - [ ] Configure production build for Google Play Store submission (AAB format)
  - [ ] Set up signing keys (or use EAS Credentials Manager)
  - [ ] Success: `eas build --platform android --profile production` can be run

- [ ] **Create README for mobile development**
  - [ ] Document setup: `npx expo install`, `npx expo start`
  - [ ] Document testing on Expo Go: scan QR code
  - [ ] Document Android emulator setup & testing
  - [ ] Document EAS Build process
  - [ ] Document permission grant flow (foreground + background, especially Android 10+ background location manual grant)
  - [ ] Success: README is clear for developers

- [ ] **Test Expo Go builds**
  - [ ] Start dev server: `npx expo start`
  - [ ] Scan QR code with Expo Go on Android emulator
  - [ ] Verify app loads: LoginScreen visible
  - [ ] Success: Expo Go build works

- [ ] **Test EAS preview build**
  - [ ] Command: `eas build --platform android --profile preview`
  - [ ] Wait for build to complete (takes ~10 min)
  - [ ] Download APK from EAS Build dashboard
  - [ ] Install on Android device/emulator: `adb install app-preview.apk`
  - [ ] Verify app launches and LoginScreen visible
  - [ ] Success: EAS preview build works end-to-end

---

### Phase 6: Permissions Testing on Android Virtual Device (AVD)

- [ ] **Set up Android Virtual Device (AVD)**
  - [ ] Use Android Studio to create/launch Android 10+ emulator (to test background location permission)
  - [ ] Verify emulator has location services enabled
  - [ ] Success: Emulator runs without errors

- [ ] **Test foreground location permission flow**
  - [ ] Run app on AVD via Expo Go or EAS build
  - [ ] Trigger LocationServiceexport component
  - [ ] Tap "Allow Once" button
  - [ ] Verify system permission dialog appears (emulator may show mock dialog)
  - [ ] Grant permission
  - [ ] Verify app receives location (or mock location from emulator)
  - [ ] Success: Foreground permission flow works

- [ ] **Test background location permission flow (Android 10+)**
  - [ ] Run app on AVD
  - [ ] Trigger background permission request
  - [ ] Dialog should state "Open Settings to complete request" (cannot grant programmatically)
  - [ ] Manually open Settings > Apps > Office Hero > Permissions > Location > "Allow all the time"
  - [ ] Return to app
  - [ ] Verify background location is now enabled
  - [ ] Note: This flow is mandatory on Android 10+; cannot be bypassed
  - [ ] Success: Background permission flow works with manual user action

- [ ] **Test permission denial flow**
  - [ ] Deny foreground permission request
  - [ ] Verify app shows error/alternative UI (graceful degradation)
  - [ ] Verify app does NOT crash
  - [ ] Success: App handles denial gracefully

- [ ] **Test location data accuracy (if available)**
  - [ ] Use emulator location simulator to set fake coordinates
  - [ ] Verify app receives those coordinates
  - [ ] Success: Location data flows correctly

---

### Phase 7: Testing & Validation

- [ ] **Run full test suite**
  - [ ] Command: `npm test`
  - [ ] Success: All unit + integration tests pass

- [ ] **Verify app builds**
  - [ ] Command: `npx expo prebuild` (generates native code)
  - [ ] Command: `eas build --platform android --profile preview`
  - [ ] Success: Builds complete without errors

- [ ] **Manual verification checklist**
  - [ ] ✅ Expo Go: scan QR code → app loads
  - [ ] ✅ LoginScreen: renders with email/password form
  - [ ] ✅ Navigation: after login, shows RouteScreen
  - [ ] ✅ RouteScreen: displays "Your Route for Today" and job list
  - [ ] ✅ Logout: returns to LoginScreen
  - [ ] ✅ Location permissions: foreground request + manual background grant works
  - [ ] ✅ EAS preview APK: downloads, installs, runs without errors
  - [ ] ✅ No crashes on app lifecycle (pause/resume, orientation change)
  - [ ] ✅ Console has no errors or warnings
  - [ ] Success: All checks pass

---

### Phase 8: Final Commit & Push

- [ ] **Final commit & push**
  - [ ] Commit: "Implement Slice 6 (Mobile Scaffold): Expo app, Android config, location permissions, React Navigation, EAS builds"
  - [ ] Push to feature branch (e.g., `phase-6/slice-6-implementation`)
  - [ ] Create PR with summary of mobile setup and testing notes
  - [ ] Success: GitHub CI passes (install, build, test)

---

## Success Criteria (Phase 6 Complete)

- ✅ Expo project initialized with TypeScript template
- ✅ app.json configured with Android package name + permissions
- ✅ expo-location library installed and functional
- ✅ Location permissions service created (foreground + background)
- ✅ PermissionAlert component shows permission requests and instructions
- ✅ React Navigation stack set up with LoginScreen and RouteScreen
- ✅ Auth context integrated (uses AsyncStorage for mobile storage)
- ✅ API client singleton configured (works on Expo Go and native)
- ✅ All unit + integration tests passing
- ✅ Expo Go development build works (scan QR → app loads)
- ✅ EAS preview build (APK) works on Android emulator/device
- ✅ Location permissions tested on AVD (foreground + background + denial flows)
- ✅ No crashes on lifecycle changes
- ✅ README documentation created
- ✅ All changes committed and pushed
- ✅ Ready for Slices 7–19 (route view, job entry, location tracking, etc.)
