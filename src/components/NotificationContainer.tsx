import React from 'react'
import type { Notification } from '../hooks/useNotifications'

interface NotificationProps {
  notification: Notification
  onClose: (id: string) => void
}

const NotificationItem: React.FC<NotificationProps> = ({ notification, onClose }) => {
  const getIcon = () => {
    switch (notification.type) {
      case 'success': return '✅'
      case 'error': return '❌'
      case 'warning': return '⚠️'
      case 'info': return 'ℹ️'
      default: return 'ℹ️'
    }
  }

  const getColorClasses = () => {
    switch (notification.type) {
      case 'success': return 'bg-green-100 border-green-400 text-green-800'
      case 'error': return 'bg-red-100 border-red-400 text-red-800'
      case 'warning': return 'bg-yellow-100 border-yellow-400 text-yellow-800'
      case 'info': return 'bg-blue-100 border-blue-400 text-blue-800'
      default: return 'bg-gray-100 border-gray-400 text-gray-800'
    }
  }

  return (
    <div className={`${getColorClasses()} border rounded-lg p-4 mb-3 shadow-lg animate-slide-in-right`}>
      <div className="flex items-start">
        <span className="text-lg mr-3 flex-shrink-0">{getIcon()}</span>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm">{notification.title}</h4>
          {notification.message && (
            <p className="text-xs mt-1 opacity-90">{notification.message}</p>
          )}
        </div>
        <button
          onClick={() => onClose(notification.id)}
          className="ml-2 flex-shrink-0 text-lg opacity-60 hover:opacity-100 transition-opacity"
        >
          ×
        </button>
      </div>
    </div>
  )
}

interface NotificationContainerProps {
  notifications: Notification[]
  onClose: (id: string) => void
}

const NotificationContainer: React.FC<NotificationContainerProps> = ({ notifications, onClose }) => {
  if (notifications.length === 0) return null

  return (
    <div className="fixed top-4 right-4 z-50 w-80 max-w-sm">
      {notifications.map(notification => (
        <NotificationItem
          key={notification.id}
          notification={notification}
          onClose={onClose}
        />
      ))}
    </div>
  )
}

export default NotificationContainer