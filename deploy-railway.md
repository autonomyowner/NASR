# Railway Deployment Guide

## Quick Fix for Current Service

1. **Go to Railway Dashboard**
2. **Click on "NASR" service**
3. **Go to "Settings" tab**
4. **Update these settings:**
   - Root Directory: `signaling-server`
   - Start Command: `npm start`
   - Build Command: `npm install`
5. **Click "Redeploy"**

## Alternative: Create New Service

1. **Click "+" in Railway**
2. **Select "GitHub Repo"**
3. **Choose your NASR repository**
4. **Set Root Directory:** `signaling-server`
5. **Deploy**

## Test Your Backend

After deployment, test:
```
https://nasr-production.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-XX...",
  "rooms": 0,
  "participants": 0
}
```

## Next: Deploy Frontend to Vercel

1. **Go to vercel.com**
2. **Import GitHub repo: NASR**
3. **Set environment variable:**
   ```
   VITE_SIGNALING_SERVER_URL=https://nasr-production.up.railway.app
   ```
4. **Deploy**
