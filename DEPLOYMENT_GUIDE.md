# 🚀 The HIVE - Complete Deployment Guide to Vercel & Cloud

## 📋 Overview

This guide will help you deploy **The HIVE Real-Time Translation System** to production with:
- Frontend on Vercel
- Backend services on Railway/Google Cloud Run
- Full WebRTC + LiveKit translation pipeline

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Signaling      │    │   Backend       │
│   (Vercel)      │ ←→ │  Server         │ ←→ │   Services      │
│   React App     │    │  (Railway)      │    │  (Railway/GCR)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ↓                       ↓                       ↓
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LiveKit SFU   │    │   Redis Cache   │    │   Monitoring    │
│   (Cloud/Self)  │    │  (Upstash)      │    │   (Optional)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎯 Step-by-Step Deployment

### 1. 📦 Prepare Your Repository

First, ensure your code is in a Git repository:

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit - Ready for deployment"

# Push to GitHub/GitLab
git remote add origin https://github.com/yourusername/thehive.git
git push -u origin main
```

### 2. 🌐 Deploy Frontend to Vercel

#### A. Connect Repository to Vercel

1. Go to [vercel.com](https://vercel.com) and sign in
2. Click "Import Project" → "Import Git Repository"
3. Select your GitHub repository
4. Choose the root directory (where package.json is located)

#### B. Configure Build Settings

Vercel should auto-detect your React app. Verify these settings:
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Install Command**: `npm install`

#### C. Add Environment Variables

In Vercel dashboard → Your Project → Settings → Environment Variables:

```env
NODE_ENV=production
VITE_SIGNALING_URL=https://your-signaling-server.railway.app
VITE_STT_SERVICE_URL=https://your-stt-service.railway.app
VITE_MT_SERVICE_URL=https://your-mt-service.railway.app
VITE_TTS_SERVICE_URL=https://your-tts-service.railway.app
VITE_LIVEKIT_URL=wss://your-project.livekit.cloud
VITE_LIVEKIT_API_KEY=your-api-key
VITE_LIVEKIT_SECRET_KEY=your-secret-key
```

### 3. 🚂 Deploy Signaling Server to Railway

#### A. Set Up Railway Account

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click "New Project" → "Deploy from GitHub repo"
3. Select your repository

#### B. Configure Signaling Server

1. Create a new service for "Signaling Server"
2. Set **Root Directory**: `signaling-server`
3. Railway will auto-detect Node.js

#### C. Add Environment Variables

```env
NODE_ENV=production
PORT=3002
CORS_ORIGINS=https://your-vercel-domain.vercel.app,https://your-custom-domain.com
```

### 4. ☁️ Deploy Backend Translation Services

You have two options for backend deployment:

#### Option A: Railway (Recommended for simplicity)

1. Create separate Railway services for each:
   - STT Service (`backend/services/stt`)
   - MT Service (`backend/services/mt`) 
   - TTS Service (`backend/services/tts`)
   - Auth Service (`backend/services/auth`)

2. For each service, set Root Directory to respective folder
3. Railway will auto-detect Python and install from `requirements.txt`

#### Option B: Google Cloud Run (For scale)

```bash
# Build and deploy each service
cd backend/services/stt
gcloud builds submit --tag gcr.io/PROJECT-ID/stt-service
gcloud run deploy stt-service --image gcr.io/PROJECT-ID/stt-service

# Repeat for mt, tts, auth services
```

### 5. 🔴 Set Up Redis Database

#### Option A: Upstash Redis (Recommended)

1. Go to [upstash.com](https://upstash.com)
2. Create a new Redis database
3. Copy the connection URL
4. Add to all backend services:

```env
REDIS_URL=rediss://user:password@host:port
```

#### Option B: Railway Redis

1. In Railway project, add "Redis" service
2. Connect to your backend services

### 6. 🎥 Configure LiveKit (Choose One)

#### Option A: LiveKit Cloud (Easiest)

1. Go to [livekit.io](https://livekit.io) → Sign up for Cloud
2. Create a new project
3. Get your credentials from dashboard:
   - `LIVEKIT_URL`: `wss://your-project.livekit.cloud`
   - `LIVEKIT_API_KEY`: Your API key
   - `LIVEKIT_SECRET_KEY`: Your secret

#### Option B: Self-Hosted LiveKit

Deploy LiveKit server using Docker:

```yaml
# docker-compose.yml for LiveKit
version: '3.8'
services:
  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880"
      - "7881:7881"
    environment:
      - LIVEKIT_CONFIG=/etc/livekit.yaml
    volumes:
      - ./livekit.yaml:/etc/livekit.yaml
```

### 7. 🔧 Production Environment Setup

#### A. Update Package.json Scripts

```json
{
  "scripts": {
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "deploy": "npm run build && echo 'Deploy to Vercel'",
    "build:production": "NODE_ENV=production npm run build"
  }
}
```

#### B. Create Production Build

```bash
# Test production build locally
npm run build
npm run preview

# Check build output
ls -la dist/
```

### 8. 🌍 Configure Custom Domain (Optional)

#### A. Add Domain to Vercel

1. Vercel Dashboard → Project → Settings → Domains
2. Add your custom domain
3. Update DNS records as instructed

#### B. Update CORS Origins

Update all backend services with new domain:

```env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 9. 🔒 Production Security Setup

#### A. Environment Variables Security

- Never commit `.env` files to Git
- Use platform-specific environment variable systems
- Rotate API keys regularly

#### B. HTTPS & Security Headers

Vercel automatically provides HTTPS. Our `vercel.json` includes security headers:
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: origin-when-cross-origin

### 10. 📊 Monitoring & Analytics

#### A. Add Error Tracking (Optional)

```bash
npm install @sentry/react @sentry/tracing
```

Add to your React app:

```javascript
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: process.env.VITE_SENTRY_DSN,
  environment: process.env.NODE_ENV,
});
```

#### B. Performance Monitoring

- Use Vercel Analytics (built-in)
- Monitor backend services via Railway/GCP dashboards
- Set up uptime monitoring (Pingdom, UptimeRobot)

## ✅ Deployment Checklist

### Pre-Deployment

- [ ] Code committed and pushed to Git
- [ ] All environment variables documented
- [ ] Production build tested locally
- [ ] Database/Redis configured

### Frontend (Vercel)

- [ ] Repository connected to Vercel
- [ ] Build settings configured
- [ ] Environment variables added
- [ ] Custom domain configured (if applicable)
- [ ] SSL certificate active

### Backend Services

- [ ] Signaling server deployed and accessible
- [ ] STT service deployed and responding
- [ ] MT service deployed and responding  
- [ ] TTS service deployed and responding
- [ ] Auth service deployed and responding
- [ ] Redis database connected
- [ ] LiveKit configured and accessible

### Testing

- [ ] Frontend loads without errors
- [ ] WebSocket connection to signaling server works
- [ ] WebRTC peer connection establishes
- [ ] Audio transmission works
- [ ] Translation services respond
- [ ] Delay toggle functions correctly
- [ ] Translation/Normal call toggle works

## 🚨 Troubleshooting Common Issues

### 1. Build Failures

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

### 2. Environment Variables Not Loading

- Check variable names start with `VITE_`
- Restart Vercel deployment after adding variables
- Verify no typos in variable names

### 3. WebSocket Connection Failures

- Ensure signaling server uses HTTPS/WSS in production
- Check CORS origins include your frontend domain
- Verify firewall/network settings

### 4. Translation Services Not Working

- Test each service endpoint individually
- Check service logs for errors
- Verify Redis connection
- Ensure sufficient memory allocation

## 🎯 Production URLs Template

After deployment, your URLs will look like:

```
Frontend:     https://your-app.vercel.app
Signaling:    https://your-signaling-server.railway.app  
STT Service:  https://your-stt-service.railway.app
MT Service:   https://your-mt-service.railway.app
TTS Service:  https://your-tts-service.railway.app
Auth Service: https://your-auth-service.railway.app
LiveKit:      wss://your-project.livekit.cloud
Redis:        rediss://user:pass@host:port
```

## 💰 Estimated Monthly Costs

### Free Tier Options

- **Vercel**: Free (Hobby plan)
- **Railway**: $5/month (Hobby plan) + usage
- **LiveKit Cloud**: 10,000 minutes free/month
- **Upstash Redis**: 10,000 requests/day free

### Scaled Production

- **Vercel Pro**: $20/month
- **Railway**: ~$20-50/month depending on usage
- **LiveKit Cloud**: ~$0.004/minute after free tier
- **Upstash Redis**: ~$10/month for production

**Total: $0-100/month** depending on scale and options chosen.

## 🔄 Continuous Deployment

### Auto-Deploy on Git Push

Both Vercel and Railway support automatic deployments:

1. **Vercel**: Auto-deploys on push to main branch
2. **Railway**: Configure auto-deploy from GitHub

### Environment-Specific Deployments

- `main` branch → Production
- `develop` branch → Staging (optional)

## 📞 Support & Next Steps

After deployment:

1. Test all features thoroughly
2. Monitor error rates and performance
3. Set up backup/disaster recovery
4. Plan scaling strategy
5. Document API endpoints for team

---

## 🎉 Ready to Deploy!

Your HIVE Real-Time Translation System is now ready for production deployment. Follow this guide step-by-step, and you'll have a fully functional live system within a few hours!

**Questions?** Check the troubleshooting section or review the deployment logs for specific error messages.