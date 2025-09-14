# Deployment Fixes for Live Server Issues

## Issues Identified

1. **CORS Policy Violation**: Frontend cannot connect to Railway signaling server
2. **Railway Service Configuration**: Service returning 404 errors
3. **Environment Variable Mismatch**: Frontend using wrong signaling server URL

## Fixes Applied

### 1. Updated CORS Configuration
- Enhanced CORS settings in `signaling-server/simple-server.js`
- Added proper headers and methods
- Included Vercel domain in allowed origins

### 2. Fixed Railway Configuration
- Updated `railway.json` to use correct start command
- Added proper health check configuration
- Created `Procfile` for Railway deployment

### 3. Updated Frontend Configuration
- Modified `configService.ts` to handle multiple environment variables
- Added fallback URL configuration
- Improved error handling in signaling service

## Deployment Steps

### Railway (Backend)
1. Go to Railway dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add:
   ```
   FRONTEND_URL=https://travoice1.vercel.app
   NODE_ENV=production
   PORT=3001
   ```
5. Redeploy the service

### Vercel (Frontend)
1. Go to Vercel dashboard
2. Select your project
3. Go to Settings → Environment Variables
4. Add:
   ```
   VITE_SIGNALING_URL=https://nasr-production-0c99.up.railway.app
   VITE_SIGNALING_SERVER_URL=https://nasr-production-0c99.up.railway.app
   ```
5. Redeploy the application

## Testing
After deployment, test the connection:
1. Visit https://travoice1.vercel.app/call
2. Check browser console for connection status
3. Try creating a room to test functionality

## Troubleshooting
If issues persist:
1. Check Railway logs for errors
2. Verify environment variables are set correctly
3. Test signaling server health endpoint: https://nasr-production-0c99.up.railway.app/health


