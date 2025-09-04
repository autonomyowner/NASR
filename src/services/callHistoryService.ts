export interface Contact {
  id: string
  name: string
  peerId: string
  avatar?: string
  language: string
  lastCalled?: Date
  isFavorite: boolean
}

export interface CallHistoryEntry {
  id: string
  contactId?: string
  peerId: string
  contactName: string
  startTime: Date
  endTime?: Date
  duration: number // in seconds
  quality: 'excellent' | 'good' | 'fair' | 'poor'
  wasIncoming: boolean
  wasAnswered: boolean
  translations?: {
    text: string
    translation: string
    timestamp: Date
  }[]
}

class CallHistoryService {
  private readonly CONTACTS_KEY = 'nasr_contacts'
  private readonly HISTORY_KEY = 'nasr_call_history'

  // Contacts Management
  getContacts(): Contact[] {
    try {
      const contacts = localStorage.getItem(this.CONTACTS_KEY)
      return contacts ? JSON.parse(contacts) : []
    } catch {
      return []
    }
  }

  saveContact(contact: Omit<Contact, 'id'>): Contact {
    const contacts = this.getContacts()
    const newContact: Contact = {
      ...contact,
      id: Date.now().toString(),
    }
    
    contacts.push(newContact)
    localStorage.setItem(this.CONTACTS_KEY, JSON.stringify(contacts))
    return newContact
  }

  updateContact(id: string, updates: Partial<Contact>): Contact | null {
    const contacts = this.getContacts()
    const index = contacts.findIndex(c => c.id === id)
    
    if (index === -1) return null
    
    contacts[index] = { ...contacts[index], ...updates }
    localStorage.setItem(this.CONTACTS_KEY, JSON.stringify(contacts))
    return contacts[index]
  }

  deleteContact(id: string): boolean {
    const contacts = this.getContacts()
    const filtered = contacts.filter(c => c.id !== id)
    
    if (filtered.length === contacts.length) return false
    
    localStorage.setItem(this.CONTACTS_KEY, JSON.stringify(filtered))
    return true
  }

  findContactByPeerId(peerId: string): Contact | null {
    const contacts = this.getContacts()
    return contacts.find(c => c.peerId === peerId) || null
  }

  getFavoriteContacts(): Contact[] {
    return this.getContacts().filter(c => c.isFavorite)
  }

  // Call History Management
  getCallHistory(): CallHistoryEntry[] {
    try {
      const history = localStorage.getItem(this.HISTORY_KEY)
      if (!history) return []
      
      return JSON.parse(history).map((entry: any) => ({
        ...entry,
        startTime: new Date(entry.startTime),
        endTime: entry.endTime ? new Date(entry.endTime) : undefined,
        translations: entry.translations?.map((t: any) => ({
          ...t,
          timestamp: new Date(t.timestamp)
        })) || []
      }))
    } catch {
      return []
    }
  }

  addCallHistoryEntry(entry: Omit<CallHistoryEntry, 'id'>): CallHistoryEntry {
    const history = this.getCallHistory()
    const newEntry: CallHistoryEntry = {
      ...entry,
      id: Date.now().toString(),
    }
    
    // Add to beginning (most recent first)
    history.unshift(newEntry)
    
    // Keep only last 100 calls
    const limitedHistory = history.slice(0, 100)
    
    localStorage.setItem(this.HISTORY_KEY, JSON.stringify(limitedHistory))
    return newEntry
  }

  updateCallHistoryEntry(id: string, updates: Partial<CallHistoryEntry>): CallHistoryEntry | null {
    const history = this.getCallHistory()
    const index = history.findIndex(h => h.id === id)
    
    if (index === -1) return null
    
    history[index] = { ...history[index], ...updates }
    localStorage.setItem(this.HISTORY_KEY, JSON.stringify(history))
    return history[index]
  }

  deleteCallHistoryEntry(id: string): boolean {
    const history = this.getCallHistory()
    const filtered = history.filter(h => h.id !== id)
    
    if (filtered.length === history.length) return false
    
    localStorage.setItem(this.HISTORY_KEY, JSON.stringify(filtered))
    return true
  }

  clearCallHistory(): void {
    localStorage.removeItem(this.HISTORY_KEY)
  }

  getCallHistoryForContact(contactId: string): CallHistoryEntry[] {
    return this.getCallHistory().filter(h => h.contactId === contactId)
  }

  getRecentContacts(limit: number = 5): Contact[] {
    const history = this.getCallHistory()
    const recentPeerIds = new Set<string>()
    const recentContacts: Contact[] = []
    
    for (const entry of history) {
      if (recentContacts.length >= limit) break
      if (recentPeerIds.has(entry.peerId)) continue
      
      recentPeerIds.add(entry.peerId)
      const contact = this.findContactByPeerId(entry.peerId)
      
      if (contact) {
        recentContacts.push(contact)
      } else {
        // Create a temporary contact for unknown peers
        recentContacts.push({
          id: `temp-${entry.peerId}`,
          name: entry.contactName || entry.peerId,
          peerId: entry.peerId,
          language: 'en-US',
          isFavorite: false,
          lastCalled: entry.startTime
        })
      }
    }
    
    return recentContacts
  }

  // Statistics
  getCallStats() {
    const history = this.getCallHistory()
    const totalCalls = history.length
    const totalDuration = history.reduce((sum, call) => sum + call.duration, 0)
    const answeredCalls = history.filter(h => h.wasAnswered).length
    const avgDuration = totalCalls > 0 ? totalDuration / totalCalls : 0
    
    return {
      totalCalls,
      totalDuration,
      answeredCalls,
      avgDuration,
      answerRate: totalCalls > 0 ? (answeredCalls / totalCalls) * 100 : 0
    }
  }
}

export const callHistoryService = new CallHistoryService()