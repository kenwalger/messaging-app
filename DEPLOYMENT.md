# Heroku Deployment Guide

This guide explains how to deploy the Abiqua Asset Management app to Heroku for live multi-device demos.

## Architecture

For Heroku deployment, we use a **single dyno** approach:
- Backend (FastAPI) serves API endpoints and WebSocket connections
- Backend also serves frontend static files (built React app)
- Frontend and backend are on the same origin (no CORS issues)

## Prerequisites

1. Heroku CLI installed and authenticated
2. Git repository initialized
3. Python 3.14.0 (as specified in `.python-version`)
4. Node.js >= 18.0.0 (for building frontend)

## Deployment Steps

### 1. Build Frontend

First, build the frontend React app:

```bash
cd src/ui
npm install
npm run build
cd ../..
```

This creates `src/ui/dist/` with static files that will be served by the backend.

### 2. Create Heroku App

```bash
# Create Heroku app
heroku create abiqua-asset-management

# Or use existing app
heroku git:remote -a abiqua-asset-management
```

### 2. Set Environment Variables

```bash
# Set encryption mode (client for production, server for POC)
heroku config:set ENCRYPTION_MODE=client

# Set frontend origin (same as app URL for single-dyno deployment)
heroku config:set FRONTEND_ORIGIN=https://abiqua-asset-management.herokuapp.com

# Set environment to production (disables dev-only features)
heroku config:set ENVIRONMENT=production

# Optional: Set encryption key seed (only used if ENCRYPTION_MODE=server)
# heroku config:set ENCRYPTION_KEY_SEED=your-seed-here
```

### 3. Configure Buildpacks

Heroku needs both Node.js (to build frontend) and Python (to run backend):

```bash
# Add Node.js buildpack (builds frontend)
heroku buildpacks:add --index 1 heroku/nodejs

# Add Python buildpack (runs backend)
heroku buildpacks:add --index 2 heroku/python
```

**Note**: 
- The root-level `package.json` is required for Heroku Node.js buildpack detection
- The root `package.json` delegates to `src/ui/package.json` for the actual build
- The `heroku-postbuild` script uses `npm install --include=dev` to ensure devDependencies (TypeScript, Vite) are installed even when `NODE_ENV=production`
- This ensures build tools are available during the build phase

### 4. Deploy Backend

```bash
# Ensure all changes are committed
git add .
git commit -m "Deploy to Heroku"

# Deploy to Heroku
git push heroku main

# Or deploy specific branch
git push heroku your-branch:main
```

### 5. Build Frontend (if not auto-built)

The frontend should build automatically via `postinstall` script. If not, build manually:

```bash
# Build frontend locally and commit
cd src/ui
npm install
npm run build
cd ../..
git add src/ui/dist/
git commit -m "Add frontend build"
git push heroku main
```

**Note**: For production, consider using a build script or CI/CD to build frontend during deployment.

### 6. Verify Deployment

```bash
# Check app logs
heroku logs --tail

# Check app status
heroku ps

# Open app in browser
heroku open
```

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENCRYPTION_MODE` | Encryption mode: `client` or `server` | `client` | No |
| `FRONTEND_ORIGIN` | Frontend origin for CORS (same as app URL for single-dyno) | None | Yes (for CORS) |
| `ENVIRONMENT` | Environment mode: `production` or `development` | `development` | No |
| `ENCRYPTION_KEY_SEED` | Seed for server-side encryption (only if `ENCRYPTION_MODE=server`) | `dev-mode-encryption-key-seed` | No |
| `PORT` | Port number (set automatically by Heroku) | - | Auto |

## WebSocket Support

Heroku supports WebSockets natively. The app uses:
- `wss://` for HTTPS connections (Heroku default)
- Automatic WebSocket upgrade handling via FastAPI
- WebSocket connections authenticated via `device_id` query parameter

**No additional configuration required** - WebSockets work out of the box on Heroku.

## Frontend Build Integration

The backend automatically serves frontend static files if `src/ui/dist/` exists:
- Static assets (JS, CSS) served from `/assets/`
- `index.html` served for all non-API routes (SPA routing)
- API routes (`/api/*`) and WebSocket (`/ws/*`) handled by FastAPI

**Build Process**:
- Frontend builds automatically via `heroku-postbuild` script
- Node.js buildpack runs first:
  - Detects Node.js app via root-level `package.json`
  - Root `package.json` delegates to `src/ui/package.json` for actual build
  - Installs all dependencies in `src/ui/` (including devDependencies)
  - Runs `heroku-postbuild` script (builds frontend in `src/ui/`)
  - Prunes devDependencies after build (production optimization)
- Python buildpack runs second, starts backend server
- Backend serves built frontend files from `src/ui/dist/`

**Why root-level `package.json`**:
- Heroku Node.js buildpack requires `package.json` at repository root for detection
- Root `package.json` is minimal and delegates to `src/ui/package.json` for actual build
- This allows Heroku to detect the Node.js app while keeping source structure intact

**Why `heroku-postbuild` instead of `postinstall`**:
- `heroku-postbuild` runs after all dependencies are installed (including devDependencies)
- Build tools (TypeScript, Vite) are available during build phase
- Heroku prunes devDependencies after build completes (reduces slug size)

**Manual Build** (if needed):
```bash
cd src/ui && npm install && npm run build && cd ../..
```

## Multi-Device Demo Flow

1. **First Device (Chrome)**:
   - Opens app URL
   - Generates unique device ID (stored in localStorage)
   - Auto-creates conversation
   - Displays conversation ID

2. **Second Device (Safari/Mobile)**:
   - Opens same app URL
   - Generates different device ID
   - User pastes conversation ID from first device
   - Joins conversation
   - Can send/receive messages

3. **All Devices**:
   - Share same conversation ID
   - Messages delivered via WebSocket
   - Real-time updates across all devices

## Live Demo Checklist

### Pre-Demo Setup
- [ ] Deploy to Heroku
- [ ] Verify app loads in browser
- [ ] Check WebSocket connection (status indicator shows "WebSocket connected")
- [ ] Test message send/receive on single device

### Multi-Device Testing
- [ ] **Chrome → Safari**: Open app in both browsers, share conversation ID
- [ ] **Laptop → Mobile**: Open app on laptop and mobile phone, share conversation ID
- [ ] **Two Audience Members**: Two different people on different devices, share conversation ID
- [ ] **Message Flow**: Send message from Device A, verify it appears on Device B
- [ ] **Encryption**: Verify encryption mode indicator shows correct mode
- [ ] **WebSocket**: Verify status shows "WebSocket connected" (not REST polling)

### Verification Points
- [ ] Each device has unique device ID (check localStorage or debug mode)
- [ ] All devices can see same conversation
- [ ] Messages appear in real-time (no refresh needed)
- [ ] WebSocket delivers messages (not REST polling fallback)
- [ ] Encryption works (client mode encrypts, server mode sends plaintext)

## Troubleshooting

### WebSocket Not Connecting
- Check Heroku logs: `heroku logs --tail`
- Verify WebSocket URL uses `wss://` (not `ws://`)
- Check browser console for WebSocket errors
- Verify `FRONTEND_ORIGIN` matches app URL exactly

### CORS Errors
- Verify `FRONTEND_ORIGIN` is set to exact app URL (with `https://`)
- Check that `ENVIRONMENT=production` is set
- Verify CORS middleware is enabled in logs

### Frontend Not Loading
- Verify frontend is built: `ls src/ui/dist/`
- Check that `index.html` exists in `src/ui/dist/`
- Verify static file serving is enabled in logs

### Messages Not Delivering
- Check WebSocket connection status in UI
- Verify device IDs are different for each browser
- Check that devices are participants in conversation
- Verify encryption mode matches between devices

## Production Considerations

This deployment is configured for **POC/demo use**. For production:

1. **Security**:
   - Use `ENCRYPTION_MODE=client` (enforce client-side encryption)
   - Set strong `ENCRYPTION_KEY_SEED` if using server mode
   - Enable HTTPS only (Heroku default)

2. **Scaling**:
   - Consider separate frontend/backend dynos for better scaling
   - Use Redis for WebSocket connection management across dynos
   - Implement proper session management

3. **Monitoring**:
   - Set up Heroku metrics/alerts
   - Monitor WebSocket connection counts
   - Track message delivery rates

## Why This Supports Real Multi-Client Demos

1. **Same Origin**: Frontend and backend on same URL eliminates CORS complexity
2. **WebSocket Support**: Heroku natively supports WebSockets (no polling fallback needed)
3. **Device ID Persistence**: localStorage ensures each browser maintains identity
4. **Dynamic Conversations**: Auto-creation and join flow enable ad-hoc multi-device demos
5. **Relative URLs**: Frontend uses `window.location.origin` - works on any domain
6. **Encryption Mode**: Configurable via env var - can demo both client and server modes

## Quick Deploy Script

```bash
#!/bin/bash
# Quick deploy script for Heroku

set -e

echo "Deploying to Heroku..."
git add .
git commit -m "Deploy to Heroku" || true
git push heroku main

echo "Deployment complete!"
echo "App URL: https://$(heroku apps:info --json | jq -r '.app.name').herokuapp.com"
```

Save as `deploy.sh`, make executable (`chmod +x deploy.sh`), and run: `./deploy.sh`

**Note**: Frontend builds automatically during Heroku deployment via `heroku-postbuild` script (runs after dependencies are installed, before pruning devDependencies).
