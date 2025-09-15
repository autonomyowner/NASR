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
  // Try multiple signaling server URLs for fallback
  const signalingUrl = import.meta.env.VITE_SIGNALING_URL || 
                      import.meta.env.VITE_SIGNALING_SERVER_URL || 
                      'https://nasr-production.up.railway.app';
  
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