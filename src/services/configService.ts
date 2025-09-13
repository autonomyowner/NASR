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