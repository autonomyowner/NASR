export interface ICEServer {
  urls: string;
  username?: string;
  credential?: string;
}

export interface AppConfig {
  signalingUrl: string;
  iceServers: ICEServer[];
}

export const getConfig = (): AppConfig => {
  // Debug environment variables
  console.log('🔧 Environment variables debug:', {
    VITE_SIGNALING_URL: import.meta.env.VITE_SIGNALING_URL,
    VITE_SIGNALING_SERVER_URL: import.meta.env.VITE_SIGNALING_SERVER_URL,
    allEnvVars: import.meta.env
  });
  
  // Try multiple signaling server URLs for fallback
  let signalingUrl = import.meta.env.VITE_SIGNALING_URL || 
                    import.meta.env.VITE_SIGNALING_SERVER_URL || 
                    'https://nasr-production.up.railway.app';
  
  // TEMPORARY FIX: Force correct URL if placeholder is detected
  if (signalingUrl.includes('your-signaling-server.railway.app')) {
    signalingUrl = 'https://nasr-production.up.railway.app';
    console.log('🔧 TEMPORARY FIX: Overriding placeholder URL with correct Railway URL');
  }
  
  console.log('🔧 Selected signaling URL:', signalingUrl);
  
  let iceServers: ICEServer[] = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ];

  // Always use default ICE servers for reliability
  iceServers = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ];

  return {
    signalingUrl,
    iceServers
  };
};