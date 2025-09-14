import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Enhancement {
  id: string
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  phase: number
  category: string
  features: string[]
  estimatedTime: string
  status: 'planned' | 'in-progress' | 'completed'
  icon: string
}

interface Phase {
  id: number
  title: string
  description: string
  color: string
  enhancements: Enhancement[]
}

const Roadmap: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<'phases' | 'timeline' | 'categories'>('phases')

  const enhancements: Enhancement[] = [
    // Phase 1: Website & Call Functionality (Month 1)
    {
      id: 'website-optimization',
      title: 'Website Performance & UI Polish',
      description: 'Optimize website performance, improve UI/UX, and ensure smooth call experience',
      priority: 'high',
      phase: 1,
      category: 'Frontend',
      features: ['Performance optimization', 'UI/UX improvements', 'Mobile responsiveness', 'Call quality optimization'],
      estimatedTime: '2-3 weeks',
      status: 'in-progress',
      icon: '🌐'
    },
    {
      id: 'call-stability',
      title: 'Call Stability & Quality',
      description: 'Enhance call reliability, audio quality, and connection stability',
      priority: 'high',
      phase: 1,
      category: 'Features',
      features: ['Connection stability', 'Audio quality improvements', 'Error handling', 'Network optimization'],
      estimatedTime: '2-3 weeks',
      status: 'in-progress',
      icon: '📞'
    },
    {
      id: 'basic-room-management',
      title: 'Basic Room Management',
      description: 'Essential room features for smooth communication experience',
      priority: 'high',
      phase: 1,
      category: 'Features',
      features: ['Room creation', 'Join/leave functionality', 'Basic controls', 'User presence'],
      estimatedTime: '1-2 weeks',
      status: 'in-progress',
      icon: '🏠'
    },

    // Phase 2: API Integration & Real-time Translation (Month 2)
    {
      id: 'api-integration',
      title: 'API Integration & Backend Services',
      description: 'Integrate translation APIs and build robust backend services',
      priority: 'high',
      phase: 2,
      category: 'Backend',
      features: ['Translation API integration', 'Backend service architecture', 'Database setup', 'API endpoints'],
      estimatedTime: '3-4 weeks',
      status: 'planned',
      icon: '🔌'
    },
    {
      id: 'real-time-translation',
      title: 'Real-time Translation Engine',
      description: 'Implement live translation during calls with multiple language support',
      priority: 'high',
      phase: 2,
      category: 'AI/ML',
      features: ['Live speech translation', 'Multi-language support', 'Translation accuracy', 'Real-time processing'],
      estimatedTime: '3-4 weeks',
      status: 'planned',
      icon: '🌐'
    },
    {
      id: 'translation-ui',
      title: 'Translation User Interface',
      description: 'Build intuitive UI for translation controls and language selection',
      priority: 'medium',
      phase: 2,
      category: 'UI/UX',
      features: ['Language selector', 'Translation controls', 'Visual indicators', 'Settings panel'],
      estimatedTime: '2-3 weeks',
      status: 'planned',
      icon: '🎨'
    },

    // Phase 3: Mobile App Development (Months 2-3)
    {
      id: 'mobile-app-core',
      title: 'Mobile App Core Features',
      description: 'Develop core mobile app functionality with call and translation features',
      priority: 'high',
      phase: 3,
      category: 'Mobile',
      features: ['Mobile call interface', 'Translation integration', 'Push notifications', 'Offline capabilities'],
      estimatedTime: '4-6 weeks',
      status: 'planned',
      icon: '📱'
    },
    {
      id: 'mobile-optimization',
      title: 'Mobile App Optimization',
      description: 'Optimize mobile app performance and user experience',
      priority: 'medium',
      phase: 3,
      category: 'Mobile',
      features: ['Performance optimization', 'Touch interactions', 'Battery optimization', 'App store preparation'],
      estimatedTime: '2-3 weeks',
      status: 'planned',
      icon: '⚡'
    },
    {
      id: 'cross-platform-sync',
      title: 'Cross-Platform Synchronization',
      description: 'Ensure seamless experience between web and mobile platforms',
      priority: 'medium',
      phase: 3,
      category: 'Backend',
      features: ['Account synchronization', 'Call history sync', 'Settings sync', 'Real-time updates'],
      estimatedTime: '2-3 weeks',
      status: 'planned',
      icon: '🔄'
    }
  ]

  const phases: Phase[] = [
    {
      id: 1,
      title: 'Website & Call Foundation',
      description: 'Month 1: Optimize website performance and ensure stable call functionality',
      color: 'from-red-500 to-pink-500',
      enhancements: enhancements.filter(e => e.phase === 1)
    },
    {
      id: 2,
      title: 'API Integration & Translation',
      description: 'Month 2: Integrate translation APIs and build real-time translation engine',
      color: 'from-blue-500 to-cyan-500',
      enhancements: enhancements.filter(e => e.phase === 2)
    },
    {
      id: 3,
      title: 'Mobile App Development',
      description: 'Months 2-3: Develop and optimize mobile applications with full feature parity',
      color: 'from-green-500 to-emerald-500',
      enhancements: enhancements.filter(e => e.phase === 3)
    }
  ]

  const categories = ['all', 'Frontend', 'Backend', 'Features', 'UI/UX', 'Mobile', 'AI/ML']

  const filteredEnhancements = enhancements.filter(enhancement => {
    const matchesSearch = enhancement.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         enhancement.description.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = selectedCategory === 'all' || enhancement.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'bg-red-500/20 text-red-300 border-red-500/30'
      case 'medium': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30'
      case 'low': return 'bg-green-500/20 text-green-300 border-green-500/30'
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500/20 text-green-300 border-green-500/30'
      case 'in-progress': return 'bg-blue-500/20 text-blue-300 border-blue-500/30'
      case 'planned': return 'bg-gray-500/20 text-gray-300 border-gray-500/30'
      default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30'
    }
  }

  return (
    <section className="section-padding relative overflow-hidden min-h-screen">
      {/* Background Image */}
      <div className="absolute inset-0 z-0">
        <img 
          src="/photo_2025-09-03_05-58-08.jpg" 
          alt="Roadmap Background" 
          className="w-full h-full object-cover"
        />
      </div>
      
      {/* Content Container */}
      <div className="relative z-10">
        <div className="container-custom">
          {/* Header */}
          <div className="text-center mb-16">
            <motion.h1 
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="text-5xl md:text-6xl font-bold text-white mb-6"
            >
              Product <span className="premium-text">Roadmap</span>
            </motion.h1>
            <motion.p 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="text-gray-300 text-xl max-w-3xl mx-auto"
            >
              Strategic enhancements to transform Travoice into a comprehensive, 
              enterprise-ready communication platform with real-time translation
            </motion.p>
          </div>

          {/* Controls */}
          <div className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 p-6 rounded-3xl shadow-2xl mb-8">
            <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
              {/* Search */}
              <div className="flex-1 max-w-md">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search enhancements..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full p-3 pl-10 bg-white/10 border border-white/20 rounded-2xl focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                  />
                  <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">🔍</span>
                </div>
              </div>

              {/* View Mode Toggle */}
              <div className="flex bg-white/10 rounded-2xl p-1 border border-white/20">
                {(['phases', 'timeline', 'categories'] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => setViewMode(mode)}
                    className={`px-4 py-2 rounded-xl font-medium transition-all duration-300 capitalize ${
                      viewMode === mode
                        ? 'bg-cyan-500 text-slate-900 shadow-lg'
                        : 'text-gray-300 hover:text-white'
                    }`}
                  >
                    {mode}
                  </button>
                ))}
              </div>

              {/* Category Filter */}
              <div className="flex flex-wrap gap-2">
                {categories.map((category) => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`px-3 py-1 rounded-lg text-sm font-medium transition-all duration-300 capitalize ${
                      selectedCategory === category
                        ? 'bg-cyan-500 text-slate-900'
                        : 'bg-white/10 text-gray-300 hover:bg-white/20'
                    }`}
                  >
                    {category}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Content */}
          <AnimatePresence mode="wait">
            {viewMode === 'phases' && (
              <motion.div
                key="phases"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
                className="space-y-8"
              >
                {phases.map((phase) => (
                  <motion.div
                    key={phase.id}
                    initial={{ opacity: 0, x: -50 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6, delay: phase.id * 0.1 }}
                    className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 rounded-3xl shadow-2xl overflow-hidden"
                  >
                    {/* Phase Header */}
                    <div className={`bg-gradient-to-r ${phase.color} p-6`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-2xl font-bold text-white mb-2">
                            Phase {phase.id}: {phase.title}
                          </h3>
                          <p className="text-white/90">{phase.description}</p>
                        </div>
                        <div className="text-right">
                          <div className="text-3xl font-bold text-white">
                            {phase.enhancements.length}
                          </div>
                          <div className="text-white/80 text-sm">Enhancements</div>
                        </div>
                      </div>
                    </div>

                    {/* Enhancements Grid */}
                    <div className="p-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {phase.enhancements.map((enhancement) => (
                          <motion.div
                            key={enhancement.id}
                            whileHover={{ scale: 1.02 }}
                            className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-all duration-300"
                          >
                            <div className="flex items-start space-x-3 mb-4">
                              <span className="text-2xl">{enhancement.icon}</span>
                              <div className="flex-1">
                                <h4 className="text-lg font-semibold text-white mb-2">
                                  {enhancement.title}
                                </h4>
                                <p className="text-gray-300 text-sm mb-3">
                                  {enhancement.description}
                                </p>
                              </div>
                            </div>

                            {/* Tags */}
                            <div className="flex flex-wrap gap-2 mb-4">
                              <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${getPriorityColor(enhancement.priority)}`}>
                                {enhancement.priority} priority
                              </span>
                              <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${getStatusColor(enhancement.status)}`}>
                                {enhancement.status}
                              </span>
                              <span className="px-2 py-1 rounded-lg text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30">
                                {enhancement.estimatedTime}
                              </span>
                            </div>

                            {/* Features */}
                            <div className="space-y-2">
                              <h5 className="text-sm font-medium text-gray-300">Key Features:</h5>
                              <ul className="space-y-1">
                                {enhancement.features.slice(0, 3).map((feature, index) => (
                                  <li key={index} className="text-xs text-gray-400 flex items-center">
                                    <span className="w-1 h-1 bg-cyan-400 rounded-full mr-2"></span>
                                    {feature}
                                  </li>
                                ))}
                                {enhancement.features.length > 3 && (
                                  <li className="text-xs text-gray-500">
                                    +{enhancement.features.length - 3} more features
                                  </li>
                                )}
                              </ul>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )}

            {viewMode === 'timeline' && (
              <motion.div
                key="timeline"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
                className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 rounded-3xl shadow-2xl p-8"
              >
                <h3 className="text-2xl font-bold text-white mb-6 text-center">Development Timeline</h3>
                <div className="space-y-6">
                  {phases.map((phase, index) => (
                    <motion.div
                      key={phase.id}
                      initial={{ opacity: 0, x: -50 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.6, delay: index * 0.1 }}
                      className="flex items-center space-x-4"
                    >
                      <div className={`w-12 h-12 rounded-full bg-gradient-to-r ${phase.color} flex items-center justify-center text-white font-bold text-lg`}>
                        {phase.id}
                      </div>
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-white">{phase.title}</h4>
                        <p className="text-gray-300 text-sm">{phase.description}</p>
                        <div className="text-xs text-gray-400 mt-1">
                          {phase.enhancements.length} enhancements • {phase.id === 1 ? 'Month 1' : phase.id === 2 ? 'Month 2' : 'Months 2-3'}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            )}

            {viewMode === 'categories' && (
              <motion.div
                key="categories"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
                className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
              >
                {filteredEnhancements.map((enhancement) => (
                  <motion.div
                    key={enhancement.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5 }}
                    whileHover={{ scale: 1.02 }}
                    className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 rounded-3xl shadow-2xl p-6 hover:shadow-cyan-500/20 transition-all duration-300"
                  >
                    <div className="flex items-start space-x-3 mb-4">
                      <span className="text-2xl">{enhancement.icon}</span>
                      <div className="flex-1">
                        <h4 className="text-lg font-semibold text-white mb-2">
                          {enhancement.title}
                        </h4>
                        <p className="text-gray-300 text-sm mb-3">
                          {enhancement.description}
                        </p>
                      </div>
                    </div>

                    {/* Tags */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${getPriorityColor(enhancement.priority)}`}>
                        {enhancement.priority}
                      </span>
                      <span className="px-2 py-1 rounded-lg text-xs font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30">
                        Phase {enhancement.phase}
                      </span>
                      <span className="px-2 py-1 rounded-lg text-xs font-medium bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                        {enhancement.category}
                      </span>
                    </div>

                    {/* Features */}
                    <div className="space-y-2">
                      <h5 className="text-sm font-medium text-gray-300">Features:</h5>
                      <ul className="space-y-1">
                        {enhancement.features.map((feature, index) => (
                          <li key={index} className="text-xs text-gray-400 flex items-center">
                            <span className="w-1 h-1 bg-cyan-400 rounded-full mr-2"></span>
                            {feature}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="mt-4 pt-4 border-t border-white/10">
                      <div className="flex justify-between items-center text-xs text-gray-400">
                        <span>Est. {enhancement.estimatedTime}</span>
                        <span className={`px-2 py-1 rounded ${getStatusColor(enhancement.status)}`}>
                          {enhancement.status}
                        </span>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Statistics */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.8 }}
            className="glass-effect backdrop-blur-xl bg-white/10 border border-cyan-400/30 rounded-3xl shadow-2xl p-8 mt-12"
          >
            <h3 className="text-2xl font-bold text-white mb-6 text-center">Roadmap Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-3xl font-bold text-cyan-400 mb-2">{phases.length}</div>
                <div className="text-gray-300 text-sm">Development Phases</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-cyan-400 mb-2">{enhancements.length}</div>
                <div className="text-gray-300 text-sm">Total Enhancements</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-cyan-400 mb-2">{categories.length - 1}</div>
                <div className="text-gray-300 text-sm">Feature Categories</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-cyan-400 mb-2">~3</div>
                <div className="text-gray-300 text-sm">Months Timeline*</div>
              </div>
            </div>
            <div className="mt-6 text-center">
              <p className="text-gray-400 text-sm">
                *Timeline is approximate and may vary based on development pace. 3 months could represent 1 month of dedicated work time.
              </p>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

export default Roadmap
