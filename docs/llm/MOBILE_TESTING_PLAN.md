# Mobile App Testing Plan

## Current Status (2026-03-08)

- PR #3 (Slice 6-19: Mobile App Features) successfully merged to `main`
- Mobile app (`apps/tech-mobile`) built with Expo ~55.0.5, React 19.2.0, React Native 0.83.2
- Core features implemented: LoginScreen, RouteScreen, JobEntryScreen, LocationService
- Background location tracking with proper permission flows

## Testing Strategy

### Phase 1: Unit & Component Tests

**Status:** Configuration in progress

- **Framework**: Jest + Testing Library for React Native
- **Files**: `apps/tech-mobile/__tests__/*.test.tsx`
- **Challenge**: React Native/jest integration on Windows requires:
  - babel.config.js setup with babel-preset-expo ✅
  - jest-expo preset configuration ✅
  - babel-jest for JSX/TypeScript transformation ✅
- **Next**: Resolve remaining jest setup issues (ES module imports in react-native setup.js)

### Phase 2: E2E Testing on Android Virtual Device (AVD)

**Status:** Pending Android Studio setup
**Required Setup**:

1. Install Android Studio
2. Create/launch Android Virtual Device
3. Install Expo Go on AVD
4. Run: `pnpm --filter tech-mobile start --android`

**Test Cases**:

- [ ] App launches without crashes
- [ ] LoginScreen displays, form validation works
- [ ] Email/password login succeeds (with mock API)
- [ ] Navigation to RouteScreen after successful auth
- [ ] RouteScreen displays job list
- [ ] JobEntryScreen form appears, submits successfully
- [ ] **Foreground location permission**:
  - App prompts on launch
  - Grant permission → location updates work
  - Deny permission → error handling works
- [ ] **Background location permission**:
  - Grant from app prompt → background updates continue
  - Or manually via Settings → Permissions → Location → Allow all the time
  - Location continues updating in background

### Phase 3: E2E Testing on Physical Device (Android)

**Status:** Future (after AVD testing complete)

- Same test cases as Phase 2
- More realistic battery/network conditions
- Better background location testing

### Phase 4: Integration with Backend API

**Status:** Blocked pending Slice 3 (Auth & RBAC) completion
**Steps**:

1. Backend API endpoint deployed (Fly.io)
2. Update `VITE_API_BASE_URL` in app.json
3. Test full auth flow: app → backend /auth/login endpoint
4. Verify JWT token storage in AsyncStorage
5. Test API calls with auth headers
6. Verify protected endpoint access

## Known Issues & Workarounds

### Jest Configuration

- React Native jest setup uses ES modules that aren't being properly transpiled
- **Workaround**: Use Expo Go for interactive testing instead of jest
- **Investigation needed**: Babel configuration to handle react-native/jest/setup.js

### React 19 vs Testing Libraries

- react-test-renderer expects React 18
- Peer dependency mismatch not blocking functionality
- May need to update testing libraries for React 19 compatibility

## Success Criteria

### For Slices 6-19 Completion

- ✅ App builds and runs on Android Virtual Device
- ✅ LoginScreen functional with form validation
- ✅ RouteScreen displays job list correctly
- ✅ JobEntryScreen accepts and processes form input
- ✅ Foreground location permission handling works
- ✅ Background location updates functional (with permission granted)
- ✅ All screens navigate correctly
- ✅ Error handling + retries implemented

### For Next Phase

- ✅ Backend API available (Slice 3 complete)
- ✅ Full integration test with real authentication
- ✅ App deployable to Fly.io via EAS Build

## Tools & Commands

```bash
# Start dev server
pnpm --filter tech-mobile start

# Open on Android emulator (requires AVD)
pnpm --filter tech-mobile start --android

# Open on web browser
pnpm --filter tech-mobile start --web

# Run unit tests (when jest is properly configured)
pnpm --filter tech-mobile test

# Build APK for deployment (requires EAS CLI)
# eas build --platform android --profile preview
```

## Files & Resources

- Slice 6 design: `project-documents/user/slices/010-slice.mobile-scaffold.md`
- ADR-055 (Frontend): `project-documents/user/architecture/055-adr.frontend.md`
- Spec: `project-documents/user/project-guides/002-spec.office-hero.md`

## Next Actions

1. **Immediate**: Set up Android Virtual Device
2. **Quick**: Run app on AVD, verify all screens load
3. **Short-term**: Fix jest configuration or defer unit testing
4. **Parallel**: Coordinate with backend team on API readiness
5. **Later**: Set up E2E testing with Detox or similar
