import { useState, useEffect, useCallback } from 'react'
import { callHistoryService } from '../services/callHistoryService'
import type { Contact, CallHistoryEntry } from '../services/callHistoryService'

interface CallHistoryHook {
  // Contacts
  contacts: Contact[]
  favoriteContacts: Contact[]
  recentContacts: Contact[]
  addContact: (contact: Omit<Contact, 'id'>) => Contact
  updateContact: (id: string, updates: Partial<Contact>) => void
  deleteContact: (id: string) => void
  findContact: (peerId: string) => Contact | null
  
  // Call History
  callHistory: CallHistoryEntry[]
  currentCall: CallHistoryEntry | null
  startCall: (peerId: string, contactName?: string, wasIncoming?: boolean) => CallHistoryEntry
  endCall: (quality: 'excellent' | 'good' | 'fair' | 'poor') => void
  addTranslationToCurrentCall: (text: string, translation: string) => void
  clearHistory: () => void
  
  // Statistics
  callStats: {
    totalCalls: number
    totalDuration: number
    answeredCalls: number
    avgDuration: number
    answerRate: number
  }
  
  refreshData: () => void
}

export const useCallHistory = (): CallHistoryHook => {
  const [contacts, setContacts] = useState<Contact[]>([])
  const [callHistory, setCallHistory] = useState<CallHistoryEntry[]>([])
  const [currentCall, setCurrentCall] = useState<CallHistoryEntry | null>(null)

  // Load data on mount
  const refreshData = useCallback(() => {
    setContacts(callHistoryService.getContacts())
    setCallHistory(callHistoryService.getCallHistory())
  }, [])

  useEffect(() => {
    refreshData()
  }, [refreshData])

  // Contact management
  const addContact = useCallback((contact: Omit<Contact, 'id'>): Contact => {
    const newContact = callHistoryService.saveContact(contact)
    refreshData()
    return newContact
  }, [refreshData])

  const updateContact = useCallback((id: string, updates: Partial<Contact>) => {
    callHistoryService.updateContact(id, updates)
    refreshData()
  }, [refreshData])

  const deleteContact = useCallback((id: string) => {
    callHistoryService.deleteContact(id)
    refreshData()
  }, [refreshData])

  const findContact = useCallback((peerId: string): Contact | null => {
    return callHistoryService.findContactByPeerId(peerId)
  }, [])

  // Call management
  const startCall = useCallback((peerId: string, contactName?: string, wasIncoming: boolean = false): CallHistoryEntry => {
    const contact = findContact(peerId)
    const name = contactName || contact?.name || peerId
    
    // Update contact's last called time if it exists
    if (contact) {
      updateContact(contact.id, { lastCalled: new Date() })
    }
    
    const newCall = callHistoryService.addCallHistoryEntry({
      contactId: contact?.id,
      peerId,
      contactName: name,
      startTime: new Date(),
      duration: 0,
      quality: 'good', // Default quality, will be updated on end
      wasIncoming,
      wasAnswered: true, // Assuming answered for now
      translations: []
    })
    
    setCurrentCall(newCall)
    refreshData()
    return newCall
  }, [findContact, updateContact, refreshData])

  const endCall = useCallback((quality: 'excellent' | 'good' | 'fair' | 'poor') => {
    if (!currentCall) return

    const endTime = new Date()
    const duration = Math.floor((endTime.getTime() - currentCall.startTime.getTime()) / 1000)
    
    callHistoryService.updateCallHistoryEntry(currentCall.id, {
      endTime,
      duration,
      quality
    })
    
    setCurrentCall(null)
    refreshData()
  }, [currentCall, refreshData])

  const addTranslationToCurrentCall = useCallback((text: string, translation: string) => {
    if (!currentCall) return

    const newTranslation = {
      text,
      translation,
      timestamp: new Date()
    }
    
    const updatedTranslations = [...(currentCall.translations || []), newTranslation]
    
    callHistoryService.updateCallHistoryEntry(currentCall.id, {
      translations: updatedTranslations
    })
    
    // Update current call state
    setCurrentCall(prev => prev ? {
      ...prev,
      translations: updatedTranslations
    } : null)
    
    refreshData()
  }, [currentCall, refreshData])

  const clearHistory = useCallback(() => {
    callHistoryService.clearCallHistory()
    refreshData()
  }, [refreshData])

  // Computed values
  const favoriteContacts = contacts.filter(c => c.isFavorite)
  const recentContacts = callHistoryService.getRecentContacts(5)
  const callStats = callHistoryService.getCallStats()

  return {
    contacts,
    favoriteContacts,
    recentContacts,
    addContact,
    updateContact,
    deleteContact,
    findContact,
    callHistory,
    currentCall,
    startCall,
    endCall,
    addTranslationToCurrentCall,
    clearHistory,
    callStats,
    refreshData
  }
}