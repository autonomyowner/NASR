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
  const signalingUrl = import.meta.env.VITE_SIGNALING_URL || 'ws://localhost:3001';
  
  let iceServers: ICEServer[] = [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ];

  try {
    const iceServersEnv = import.meta.env.VITE_ICE_SERVERS;
    if (iceServersEnv) {
      iceServers = JSON.parse(iceServersEnv);
    }
  } catch (error) {
    console.warn('Failed to parse VITE_ICE_SERVERS, using default STUN servers:', error);
  }

  return {
    signalingUrl,
    iceServers
  };
};