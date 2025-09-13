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
  const signalingUrl = import.meta.env.VITE_SIGNALING_URL || 'http://localhost:3002';
  
  let iceServers: ICEServer[] = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ];

  try {
    const iceServersEnv = import.meta.env.VITE_ICE_SERVERS;
    if (iceServersEnv && iceServersEnv.trim()) {
      iceServers = JSON.parse(iceServersEnv);
    }
  } catch (error) {
    console.warn('Failed to parse VITE_ICE_SERVERS, using default STUN servers:', error);
    // Ensure we have valid ICE servers even if parsing fails
    iceServers = [
      { urls: 'stun:stun.l.google.com:19302' },
      { urls: 'stun:stun1.l.google.com:19302' }
    ];
  }

  return {
    signalingUrl,
    iceServers
  };
};