# 🚀 **DEPLOY NOW - Quick Start Guide**

## ⚡ **5-Minute Vercel Deployment**

### 1. **Push to GitHub** (2 minutes)
```bash
git add .
git commit -m "Ready for production deployment"
git push origin main
```

### 2. **Deploy to Vercel** (2 minutes)
1. Go to [vercel.com](https://vercel.com) → Sign in with GitHub
2. Import your repository
3. **Build Settings**: Auto-detected ✅
   - Framework: Vite
   - Build Command: `npm run build`
   - Output Directory: `dist`

### 3. **Add Environment Variables** (1 minute)
In Vercel dashboard → Settings → Environment Variables:

**Essential Variables (for basic functionality):**
```
NODE_ENV=production
VITE_SIGNALING_URL=https://your-signaling-server.railway.app
```

**Deploy!** ✅ Your frontend is now live!

---

## 🔗 **Complete System Deployment**

For full real-time translation functionality, follow these steps:

### **Phase 1: Core Services** ⭐ *Start Here*

#### A. **Signaling Server → Railway**
1. [railway.app](https://railway.app) → New Project → From GitHub
2. Root Directory: `signaling-server`
3. Environment Variables:
   ```
   NODE_ENV=production
   PORT=3002
   CORS_ORIGINS=https://your-app.vercel.app
   ```

#### B. **Update Vercel Environment**
Add your Railway signaling URL:
```
VITE_SIGNALING_URL=https://your-signaling-server.up.railway.app
```

🎉 **Your basic voice calling system is now live!**

---

### **Phase 2: Translation Services** ⭐ *For Full Translation*

#### A. **Deploy Backend Services**

**Option 1: Quick Setup (Railway)**
Deploy each service separately:
- STT Service: Root dir `backend/services/stt`
- MT Service: Root dir `backend/services/mt`  
- TTS Service: Root dir `backend/services/tts`
- Auth Service: Root dir `backend/services/auth`

**Option 2: Docker (Advanced)**
```bash
# Build and deploy with Docker
cd backend/services/stt
docker build -t stt-service .
# Deploy to your preferred platform
```

#### B. **Set Up Redis Database**
1. [upstash.com](https://upstash.com) → New Redis Database
2. Copy Redis URL to all backend services:
   ```
   REDIS_URL=rediss://username:password@host:port
   ```

#### C. **Configure LiveKit**
**Option 1: LiveKit Cloud** (Recommended)
1. [livekit.io](https://livekit.io) → Create Account
2. New Project → Get credentials
3. Add to Vercel:
   ```
   VITE_LIVEKIT_URL=wss://your-project.livekit.cloud
   VITE_LIVEKIT_API_KEY=your-api-key  
   VITE_LIVEKIT_SECRET_KEY=your-secret-key
   ```

#### D. **Update Vercel with Service URLs**
```
VITE_STT_SERVICE_URL=https://your-stt-service.up.railway.app
VITE_MT_SERVICE_URL=https://your-mt-service.up.railway.app
VITE_TTS_SERVICE_URL=https://your-tts-service.up.railway.app
VITE_AUTH_SERVICE_URL=https://your-auth-service.up.railway.app
```

---

## ✅ **Deployment Checklist**

### **Phase 1: Basic Deployment** ✨
- [ ] Code pushed to GitHub
- [ ] Vercel account created and connected
- [ ] Frontend deployed to Vercel
- [ ] Signaling server deployed to Railway
- [ ] Environment variables configured
- [ ] **Test**: Basic voice calling works

### **Phase 2: Full Translation** 🌍
- [ ] Backend services deployed (STT, MT, TTS, Auth)
- [ ] Redis database configured
- [ ] LiveKit configured
- [ ] All service URLs added to Vercel environment
- [ ] **Test**: Translation functionality works
- [ ] **Test**: Delay toggle works (your new feature!)
- [ ] **Test**: Translation/Normal call toggle works

---

## 🏃‍♂️ **Start Deployment Now!**

**Choose your path:**

### 🎯 **Just Want It Live? (5 minutes)**
→ Follow **⚡ 5-Minute Vercel Deployment** above
→ You'll have a live website with basic functionality

### 🚀 **Want Full Translation System? (30 minutes)**
→ Follow **Phase 1** then **Phase 2** above
→ You'll have the complete real-time translation system

### 💡 **Pro Tip**
Deploy Phase 1 first, test it, then add Phase 2 services incrementally. This way you always have a working system!

---

## 🆘 **Need Help?**

**Common Issues:**
- **Build fails?** → Run `npm run build` locally first
- **Can't connect services?** → Check CORS origins include your Vercel URL
- **Environment variables not working?** → Ensure they start with `VITE_`

**Resources:**
- Full guide: `DEPLOYMENT_GUIDE.md`
- Vercel docs: [vercel.com/docs](https://vercel.com/docs)
- Railway docs: [docs.railway.app](https://docs.railway.app)

---

## 🎉 **Your System Will Be:**

- ✅ **Live on the Internet** 
- ✅ **Fully Functional Real-Time Translation**
- ✅ **Your New Features** (10s delay + translation toggle)
- ✅ **Production Ready**
- ✅ **Auto-scaling**
- ✅ **HTTPS Secure**

**Ready? Let's deploy! 🚀**