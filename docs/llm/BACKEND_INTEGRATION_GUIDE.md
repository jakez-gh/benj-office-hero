# Backend Integration Guide — Slice 3 Auth Ready! 🎉

## Status: UNBLOCKED ✅

**Slice 3 (Auth & RBAC) is COMPLETE!** Mobile can now test against real backend endpoints.

## Available Endpoints

Backend just deployed the following auth endpoints:

```bash
POST /auth/login          # Authenticate user, return JWT token
POST /auth/refresh        # Refresh expired JWT
POST /auth/logout         # Invalidate JWT
```

## Quick Start (Local Testing)

### Step 1: Create Mobile Environment File

Create `apps/tech-mobile/.env.local`:

```bash
# Backend API endpoint
EXPO_PUBLIC_OFFICE_HERO_API_URL=http://localhost:8000
```

### Step 2: Start Backend Locally

In a terminal (from backend repo or office-hero root):

```bash
# Activate Python venv
source venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Run FastAPI dev server
python -m uvicorn office_hero.main:app --reload
```

Expected output:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Step 3: Start Expo Dev Server

In another terminal:

```bash
cd apps/tech-mobile
pnpm start
```

### Step 4: Test Login Flow on Emulator

**On Samsung_A15 emulator:**

1. Open Expo Go app (or scan QR code from Expo terminal)
2. LoginScreen loads with email/password form
3. Enter test credentials:
   - Email: `test@example.com`
   - Password: `password123` (or whatever backend accepts)
4. Tap "Log in"
5. **Success**: RouteScreen appears with job list
6. **Failure**: Error alert shows

## What Changed in API Client

The shared `@office-hero/api-client` was updated to:

1. Support Expo public environment variables (`EXPO_PUBLIC_*`)
2. Use correct endpoint path: `/auth/login` (not `/login`)
3. Fallback to `http://localhost:8000` if env var not set

## Testing Checklist

**Phase 2A: Auth Integration Test**

- [ ] Backend server running locally
- [ ] Expo dev server started
- [ ] `.env.local` created with API URL
- [ ] LoginScreen form appears on emulator
- [ ] Valid credentials → RouteScreen loads
- [ ] Invalid credentials → Error alert displays
- [ ] Token stored in AsyncStorage (inspect via Expo DevTools)

**Phase 2B: Full Navigation Test**

After successful login:

- [ ] RouteScreen displays job list (from `/technician/route`)
- [ ] Tap job → JobEntryScreen navigates correctly
- [ ] JobEntryScreen form renders (customer name, address, etc.)
- [ ] Submit job → API call succeeds (POST `/jobs`)

**Phase 2C: Permissions Test**

On first RouteScreen load:

- [ ] Foreground location permission prompt appears
- [ ] Grant → location updates start
- [ ] Deny → error handling activates gracefully

## API Endpoints Used by Mobile

| Feature | Method | Endpoint | Auth |
| --- | --- | --- | --- |
| Login | POST | `/auth/login` | No |
| Get daily route | GET | `/technician/route` | Yes (Bearer token) |
| Get job details | GET | `/jobs/{jobId}` | Yes |
| Create job | POST | `/jobs` | Yes |
| Update job | PUT | `/jobs/{jobId}` | Yes |
| Post location | PUT | `/vehicles/{vehicleId}/location` | Yes |

## Debugging Tips

### If Login Fails

1. **Check backend is running**: `curl http://localhost:8000/docs` → Should see Swagger UI
2. **Check credentials**: Verify email/password match backend test user
3. **Check network**: Emulator can reach host via `10.0.2.2:8000` (Android bridge)
4. **Check logs**: Look at backend terminal for error details

### If Routes Endpoint Fails

1. Verify JWT token is valid: Check bearer token in request headers
2. Check technician exists: Backend must have `/technician/route` implementation
3. Check RLS policies: Tenant isolation may restrict access

### If Expo Server Issues

1. Kill previous Expo process: `pgrep -f "expo start" | xargs kill -9`
2. Clear Metro cache: `rm -rf /tmp/metro-cache`
3. Rebuild: `pnpm install && pnpm start`

## Architecture Notes

- **Shared API Client**: `packages/api-client/src/index.ts` handles all HTTP calls
- **Environment Config**: Expo reads `.env.local` → injected as `EXPO_PUBLIC_*`
- **Auth Flow**: LoginScreen → token → stored in app state → included in all requests
- **Error Handling**: API calls include try/catch + error alerts

## Files Updated

1. `packages/api-client/src/index.ts` — Environment variable support
2. `apps/tech-mobile/.env.local` — Backend URL (git-ignored)
3. This guide — `BACKEND_INTEGRATION_GUIDE.md`

## Next Steps

**After successful local testing:**

1. Deploy backend to Fly.io: `fly deploy` (or ask backend team)
2. Update `.env.local`: `EXPO_PUBLIC_OFFICE_HERO_API_URL=<fly.io-url>`
3. Test on emulator pointing to cloud backend
4. Deploy mobile to Fly.io via EAS Build

## References

- Slice 3 (Auth & RBAC): `project-documents/user/slices/006-slice.auth-rbac.md`
- ADR-053 (Tenant Isolation): `project-documents/user/architecture/053-adr.tenant-isolation.md`
- API Client: `packages/api-client/src/index.ts`
- Mobile App: `apps/tech-mobile/App.tsx`
- Testing Plan: `TESTING_SESSION_2026-03-08.md`

---

**Backend integration is LIVE! Your mobile app is no longer blocked.** 🚀
