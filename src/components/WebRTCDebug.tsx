import React from 'react'
import { useWebRTC } from '../hooks/useWebRTC'

interface WebRTCDebugProps {
  show: boolean
}

const WebRTCDebug: React.FC<WebRTCDebugProps> = ({ show }) => {
  const webRTC = useWebRTC()

  if (!show) return null

  return (
    <div className="fixed bottom-4 left-4 bg-black bg-opacity-80 text-white p-4 rounded-lg text-xs font-mono max-w-md">
      <h4 className="font-bold mb-2">WebRTC Debug Info</h4>
      <div className="space-y-1">
        <div>Call Active: {webRTC.isCallActive ? '✅' : '❌'}</div>
        <div>Connecting: {webRTC.isConnecting ? '🔄' : '⭕'}</div>
        <div>Muted: {webRTC.isMuted ? '🔇' : '🔊'}</div>
        <div>Peer ID: {webRTC.peerId || 'None'}</div>
        <div>Local Stream: {webRTC.localStream ? '✅' : '❌'}</div>
        <div>Remote Stream: {webRTC.remoteStream ? '✅' : '❌'}</div>
        <div>Quality Score: {webRTC.qualityScore || 0}%</div>
        {webRTC.qualityMetrics && (
          <div className="mt-2 text-xs">
            <div>RTT: {Math.round(webRTC.qualityMetrics.rtt)}ms</div>
            <div>Bitrate: {webRTC.qualityMetrics.bitrate}kbps</div>
            <div>Network: {webRTC.qualityMetrics.networkType}</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default WebRTCDebug