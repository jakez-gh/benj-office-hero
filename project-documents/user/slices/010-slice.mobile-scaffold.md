---
docType: slice-design
parent: ../project-guides/003-slices.office-hero.md
project: office-hero
dateCreated: 20260308
status: not_started
---

# Slice Design 010: Mobile app scaffold

This is the final foundation slice. It initializes a React Native Expo project with Android build
configuration, location permission setup, and basic navigation scaffolding. It establishes the
foundation for native mobile development while reusing the shared API client from slice 5.

It corresponds to slice 6 in the slice plan.

## Goals

* Initialize React Native Expo project in `apps/tech-mobile/`:
  * Use Expo template: `npx create-expo-app tech-mobile --template expo-template-blank-typescript`
  * Or manually configure: TypeScript, Expo SDK 50+, React Native
* Configure `app.json` for Android:
  * `"name": "Office Hero"`
  * `"slug": "office-hero"`
  * `"owner": "office-hero"` (Expo account)
  * `"android": { "package": "com.officehero.tech" }`
  * Request permissions: `"INTERNET"`, `"ACCESS_COARSE_LOCATION"`, `"ACCESS_FINE_LOCATION"`,
    `"ACCESS_BACKGROUND_LOCATION"` (for Slice 18 later)
* Add `expo-location` package: `pnpm --filter tech-mobile add expo-location`
* Create location permission request in `apps/tech-mobile/App.tsx`:
  * On app launch, request foreground location permission (`requestForegroundPermissionsAsync()`)
  * Request background location permission (`requestBackgroundPermissionsAsync()`) with explanation
  * Handle denial: show alert with instructions (user must grant in system Settings)
  * Only proceed to main app if at least foreground permission granted
* Set up React Navigation:
  * Add `@react-navigation/native`, `@react-navigation/stack`, `react-native-screens`, `react-native-safe-area-context`
  * Create a stack navigator in `apps/tech-mobile/src/navigation.tsx`:
    * `LoginScreen` (shows login form)
    * `RouteScreen` (shows technician's daily route — placeholder "Your route for today")
    * Navigate from Login → Route on successful auth
* Shared API integration:
  * Import `ApiClient` from `@office-hero/api-client` (pnpm workspace dependency)
  * Use in auth context similar to admin-web
* Create `apps/tech-mobile/src/screens/`:
  * `LoginScreen.tsx` — simple email + password form, login button, error handling
  * `RouteScreen.tsx` — placeholder text "Your route for today" + logout button
* Create `apps/tech-mobile/App.tsx`:
  * Location permission request on launch
  * Navigator setup
  * Auth context provider
  * Entry point with proper error boundaries
* Build configuration:
  * Create `eas.json` for EAS Build (Expo's cloud build service):

    ```json
    {
      "build": {
        "preview": { "android": { "buildType": "apk" } },
        "production": { "android": { "buildType": "aab" } }
      }
    }
    ```

  * Local build via `expo prebuild` + Android Studio, or via EAS Build CLI
* Test infrastructure:
  * `apps/tech-mobile/__tests__/` with Jest + `@testing-library/react-native`:
    * `test_permission_request.test.ts` — mock `expo-location` permission request; test flow
    * `test_navigation.test.ts` — test Login → Route navigation on successful auth
    * `test_login_screen.test.ts` — test login form renders and submits
  * Smoke test: `jest` runs successfully; no uncaught errors
* Documentation:
  * `apps/tech-mobile/README.md` — instructions to:
    * Set up Android Studio + emulator (see 950-tasks.maintenance.md DEV-01)
    * Run `pnpm install` (from workspace root)
    * Run `pnpm --filter tech-mobile start` to launch Expo dev server
    * Scan QR code with Expo Go app on emulator
    * Or: `pnpm --filter tech-mobile run android` to build APK and install on emulator
    * Permission request will appear on first launch; grant foreground + background location

## Structure

```text
apps/tech-mobile/
├── app.json               # Expo config with Android package + permissions
├── eas.json               # EAS Build config
├── tsconfig.json
├── package.json
├── babel.config.js        # Babel config for React Native
├── App.tsx                # Entry point + permission request + navigator
├── src/
│   ├── api.ts             # ApiClient singleton + auth context
│   ├── navigation.tsx      # Stack navigator setup
│   └── screens/
│       ├── LoginScreen.tsx
│       └── RouteScreen.tsx
├── __tests__/
│   ├── __mocks__/
│   │   └── expo-location.ts
│   ├── test_permission_request.test.ts
│   ├── test_navigation.test.ts
│   └── test_login_screen.test.ts
└── README.md
```

## Special Considerations

**Android 10+ Background Location Permissions:**

* `ACCESS_BACKGROUND_LOCATION` cannot be granted programmatically on Android 10+
* User must manually grant "Allow all the time" in system Settings
* The app must provide clear UX: show explanation dialog with link to Settings if permission denied
* **Testing note:** Test this on a real Android Virtual Device (AVD) before Slice 18 (location tracking)
  * Grant foreground permission in the app prompt
  * When background permission requested, dismiss the app prompt
  * Manually open Settings → Apps → Office Hero → Permissions → Location → "Allow all the time"
  * Re-launch app and verify location tracking works

**Expo vs native Android development:**

* This slice uses Expo CLI for simplicity and cross-platform compatibility
* Full native Android build via Android Studio is deferred to post-MVP
* Expo Go (on emulator) is sufficient for E2E testing in Slice 28

## Failing Test Outline

```typescript
// __tests__/test_permission_request.test.ts
import { render, fireEvent, waitFor } from '@testing-library/react-native'
import App from '../App'
import * as ExpoLocation from 'expo-location'

jest.mock('expo-location')

it('should request foreground location permission on launch', async () => {
  const mockForeground = jest.spyOn(ExpoLocation, 'requestForegroundPermissionsAsync')
  mockForeground.mockResolvedValue({ granted: true, expires: 'never' })

  render(<App />)

  await waitFor(() => {
    expect(mockForeground).toHaveBeenCalled()
  })
})

it('should show alert if foreground permission denied', async () => {
  const mockForeground = jest.spyOn(ExpoLocation, 'requestForegroundPermissionsAsync')
  mockForeground.mockResolvedValue({ granted: false })

  const alertSpy = jest.spyOn(global, 'alert')

  render(<App />)

  await waitFor(() => {
    expect(alertSpy).toHaveBeenCalled()
  })
})

// __tests__/test_navigation.test.ts
it('should navigate to RouteScreen after successful login', async () => {
  const { getByTestId, getByText } = render(<App />)

  // Fill login form
  fireEvent.changeText(getByTestId('email-input'), 'tech@tenant1.com')
  fireEvent.changeText(getByTestId('password-input'), 'password')

  // Submit
  fireEvent.press(getByText('Login'))

  // Assert RouteScreen visible
  await waitFor(() => {
    expect(getByText('Your route for today')).toBeTruthy()
  })
})
```

## Dependencies

Depends on slice 5 (Frontend scaffold — pnpm workspace + api-client) and slice 3 (Auth — login API).

Does NOT depend on slice 5a (admin web shell); they are parallel branches.

## Effort

Estimate: 2/5. Most work is Expo initialization and permission handling. Navigation setup is
straightforward React Navigation. API integration reuses the client from slice 5. Main concern:
testing location permission flows on a real AVD (will be done in a dedicated dev environment setup).

---

Once this design is approved, implementation starts with creating the Expo project and permission
request flow (failing tests first), then navigation, then verifying on an AVD. By the end of this
slice, developers can run the mobile app on an emulator and authenticate. Location tracking comes
in Slice 18.
