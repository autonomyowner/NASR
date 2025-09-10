import { useState } from 'react'
// Using emoji icons instead of heroicons for simplicity

interface RoomManagerProps {
  onJoinRoom: (roomId: string, sourceLanguage: string, targetLanguage: string) => void
  onCreateRoom: (sourceLanguage: string, targetLanguage: string) => void
}

const LANGUAGES = [
  { code: 'en', name: 'English', flag: '🇺🇸' },
  { code: 'es', name: 'Spanish', flag: '🇪🇸' },
  { code: 'fr', name: 'French', flag: '🇫🇷' },
  { code: 'de', name: 'German', flag: '🇩🇪' },
  { code: 'it', name: 'Italian', flag: '🇮🇹' },
  { code: 'pt', name: 'Portuguese', flag: '🇵🇹' },
  { code: 'ar', name: 'Arabic', flag: '🇸🇦' },
  { code: 'zh', name: 'Chinese', flag: '🇨🇳' },
  { code: 'ja', name: 'Japanese', flag: '🇯🇵' },
  { code: 'ko', name: 'Korean', flag: '🇰🇷' }
]

const RoomManager: React.FC<RoomManagerProps> = ({ onJoinRoom, onCreateRoom }) => {
  const [roomId, setRoomId] = useState('')
  const [sourceLanguage, setSourceLanguage] = useState('en')
  const [targetLanguage, setTargetLanguage] = useState('es')
  const [activeTab, setActiveTab] = useState<'create' | 'join'>('create')

  const handleCreateRoom = () => {
    if (sourceLanguage && targetLanguage) {
      onCreateRoom(sourceLanguage, targetLanguage)
    }
  }

  const handleJoinRoom = () => {
    if (roomId && sourceLanguage && targetLanguage) {
      onJoinRoom(roomId, sourceLanguage, targetLanguage)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="text-center">
        <h2 className="text-3xl font-bold text-white mb-2">
          Real-Time Translation
        </h2>
        <p className="text-slate-300">
          Break language barriers with instant voice translation
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="flex bg-slate-800/50 backdrop-blur-sm rounded-lg p-1">
        <button
          onClick={() => setActiveTab('create')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-md font-medium transition-all ${
            activeTab === 'create'
              ? 'bg-hive-cyan text-slate-900'
              : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          ➕ Create Room
        </button>
        <button
          onClick={() => setActiveTab('join')}
          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-md font-medium transition-all ${
            activeTab === 'join'
              ? 'bg-hive-cyan text-slate-900'
              : 'text-slate-300 hover:text-white hover:bg-slate-700/50'
          }`}
        >
          ➡️ Join Room
        </button>
      </div>

      {/* Language Selection */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl p-6 border border-slate-700/50">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          🌐 Language Configuration
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Source Language */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Your Language (Speaking)
            </label>
            <select
              value={sourceLanguage}
              onChange={(e) => setSourceLanguage(e.target.value)}
              className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-hive-cyan focus:border-transparent"
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.name}
                </option>
              ))}
            </select>
          </div>

          {/* Target Language */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Translation To (Listening)
            </label>
            <select
              value={targetLanguage}
              onChange={(e) => setTargetLanguage(e.target.value)}
              className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-hive-cyan focus:border-transparent"
            >
              {LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.flag} {lang.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Room Interface */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl p-6 border border-slate-700/50">
        {activeTab === 'create' ? (
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Create New Room</h3>
            <p className="text-slate-300 mb-4">
              Start a new translation session and share the room ID with others
            </p>
            <button
              onClick={handleCreateRoom}
              className="w-full bg-gradient-to-r from-hive-cyan to-cyan-400 text-slate-900 font-semibold py-3 px-6 rounded-lg hover:from-cyan-400 hover:to-hive-cyan transition-all transform hover:scale-105 active:scale-95"
            >
              Create Translation Room
            </button>
          </div>
        ) : (
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">Join Existing Room</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Room ID
                </label>
                <input
                  type="text"
                  value={roomId}
                  onChange={(e) => setRoomId(e.target.value)}
                  placeholder="Enter room ID (e.g., abc-123-def)"
                  className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-400 focus:ring-2 focus:ring-hive-cyan focus:border-transparent"
                />
              </div>
              <button
                onClick={handleJoinRoom}
                disabled={!roomId}
                className="w-full bg-gradient-to-r from-hive-cyan to-cyan-400 text-slate-900 font-semibold py-3 px-6 rounded-lg hover:from-cyan-400 hover:to-hive-cyan transition-all transform hover:scale-105 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                Join Translation Room
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Instructions */}
      <div className="bg-slate-800/20 backdrop-blur-sm rounded-xl p-4 border border-slate-700/30">
        <h4 className="text-sm font-semibold text-slate-300 mb-2">Quick Start:</h4>
        <ol className="text-sm text-slate-400 space-y-1 list-decimal list-inside">
          <li>Select your speaking language and desired translation language</li>
          <li>Create a room or join an existing one with a room ID</li>
          <li>Allow microphone permissions when prompted</li>
          <li>Start speaking - translations will appear automatically</li>
        </ol>
      </div>
    </div>
  )
}

export default RoomManager