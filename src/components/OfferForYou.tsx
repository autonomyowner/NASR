const OfferForYou = () => {
  return (
    <section className="min-h-screen flex items-center justify-center relative overflow-hidden glass-effect section-padding">

      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10 z-5">
        <div className="absolute top-20 left-20 w-32 h-32 bg-yellow-500 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-yellow-500 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-60 h-60 bg-yellow-500 rounded-full blur-3xl"></div>
      </div>

      <div className="container-custom text-center relative z-10">
        <div className="max-w-6xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-2 glass-effect border border-yellow-500/30 rounded-full premium-text text-sm font-medium mb-8">
            <span className="mr-2"></span>
            Live Demo Available
          </div>

          {/* Main Heading */}
          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
            Experience Real-Time
            <span className="block premium-text">Translation</span>
          </h1>

          {/* Subtitle */}
          <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-4xl mx-auto leading-relaxed">
            See how NASR APP breaks language barriers in seconds, enabling seamless communication 
            between people speaking different languages anywhere in the world.
          </p>

          {/* Pain Point Section */}
          <div className="bg-red-900/20 border border-red-500/30 rounded-3xl p-8 mb-12">
            <h2 className="text-3xl font-bold text-white mb-6">Global Communication Challenges</h2>
            <div className="grid md:grid-cols-2 gap-6 text-left">
              <div className="space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="text-red-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Language Barriers</h4>
                    <p className="text-gray-300 text-sm">Millions of meaningful conversations are lost daily due to language differences, limiting global opportunities and connections.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-red-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Miscommunication Costs</h4>
                    <p className="text-gray-300 text-sm">International businesses lose billions annually due to translation errors and cultural misunderstandings in global communications.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-red-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Travel Communication</h4>
                    <p className="text-gray-300 text-sm">Travelers struggle with basic communication, limiting authentic cultural experiences and creating barriers to exploration.</p>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="text-red-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Educational Gaps</h4>
                    <p className="text-gray-300 text-sm">Language learning takes years, preventing immediate communication needs and limiting access to global education resources.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-red-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Social Isolation</h4>
                    <p className="text-gray-300 text-sm">Language differences create social barriers, preventing immigrants and expats from fully integrating into new communities.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-red-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Cultural Exchange Loss</h4>
                    <p className="text-gray-300 text-sm">Rich cultural exchanges and global friendships are missed due to the inability to communicate across languages naturally.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Solution Section */}
          <div className="bg-green-900/20 border border-green-500/30 rounded-3xl p-8 mb-12">
            <h2 className="text-3xl font-bold text-white mb-6">The Solution: NASR APP Innovation</h2>
            <div className="grid md:grid-cols-2 gap-6 text-left">
              <div className="space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="text-green-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Real-Time Voice Translation</h4>
                    <p className="text-gray-300 text-sm">Speak naturally in your language and hear responses instantly in the listener's native language with &lt;3 second latency.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-green-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Context-Aware Conversations</h4>
                    <p className="text-gray-300 text-sm">Advanced AI understands context, idioms, and cultural nuances for natural, meaningful conversations across languages.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-green-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Cultural Nuance Preservation</h4>
                    <p className="text-gray-300 text-sm">Maintains emotional tone, cultural context, and meaning beyond literal translation for authentic communication.</p>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="flex items-start space-x-4">
                  <div className="text-green-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Seamless User Experience</h4>
                    <p className="text-gray-300 text-sm">Intuitive interface requires no learning curve - just speak naturally and experience instant, fluid communication.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-green-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Multi-Platform Accessibility</h4>
                    <p className="text-gray-300 text-sm">Available on web, mobile, and desktop - communicate anywhere, anytime without platform limitations.</p>
                  </div>
                </div>
                <div className="flex items-start space-x-4">
                  <div className="text-green-400 text-xl"></div>
                  <div>
                    <h4 className="text-white font-semibold">Privacy-Focused Design</h4>
                    <p className="text-gray-300 text-sm">End-to-end encryption ensures your conversations remain private while enabling breakthrough translation technology.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Revenue Projection */}
          <div className="bg-slate-800/30 backdrop-blur-md border border-yellow-500/30 rounded-3xl p-8 mb-12">
            <h2 className="text-3xl font-bold text-white text-center mb-8">Performance Metrics: The Technology</h2>
            <div className="grid md:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="text-4xl font-bold premium-text mb-2">&lt;3s</div>
                <div className="text-gray-400">Translation Latency</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold premium-text mb-2">&gt;95%</div>
                <div className="text-gray-400">Accuracy Rate</div>
              </div>
              <div className="text-center">
                <div className="text-4xl font-bold premium-text mb-2">50+</div>
                <div className="text-gray-400">Supported Languages</div>
              </div>
            </div>
            <div className="mt-8 p-6 bg-yellow-500/10 border border-yellow-500/30 rounded-2xl">
              <div className="text-center">
                <div className="text-5xl font-bold premium-text mb-2">Real-Time</div>
                <div className="text-gray-300 text-lg">Processing Speed</div>
                <div className="text-gray-400 text-sm mt-2">Instant communication without delays or interruptions</div>
              </div>
            </div>
          </div>

          {/* Our Offer */}
          <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 border border-yellow-500/30 rounded-3xl p-8 mb-12">
            <h2 className="text-3xl font-bold text-white text-center mb-8">What NASR APP Delivers</h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-6">
                <div className="premium-card p-6">
                  <h3 className="text-2xl font-bold text-white mb-4">Real-Time Translation Engine</h3>
                  <ul className="text-gray-300 space-y-2">
                    <li>• Neural machine translation technology</li>
                    <li>• Advanced speech recognition system</li>
                    <li>• Natural language processing algorithms</li>
                    <li>• Cloud-based processing infrastructure</li>
                  </ul>
                </div>
                <div className="premium-card p-6">
                  <h3 className="text-2xl font-bold text-white mb-4">Voice Communication Hub</h3>
                  <ul className="text-gray-300 space-y-2">
                    <li>• High-quality voice input processing</li>
                    <li>• Natural text-to-speech synthesis</li>
                    <li>• Noise cancellation and audio optimization</li>
                    <li>• Multiple accent and dialect support</li>
                  </ul>
                </div>
              </div>
              <div className="space-y-6">
                <div className="premium-card p-6">
                  <h3 className="text-2xl font-bold text-white mb-4">Text Chat Integration</h3>
                  <ul className="text-gray-300 space-y-2">
                    <li>• Real-time text translation</li>
                    <li>• Conversation history and context</li>
                    <li>• Emoji and media translation support</li>
                    <li>• Cross-platform synchronization</li>
                  </ul>
                </div>
                <div className="premium-card p-6">
                  <h3 className="text-2xl font-bold text-white mb-4">Multi-Language Support</h3>
                  <ul className="text-gray-300 space-y-2">
                    <li>• 50+ supported languages and growing</li>
                    <li>• Regional dialect recognition</li>
                    <li>• Cultural context adaptation</li>
                    <li>• Continuous learning and improvement</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>

          {/* Investment Section */}
          <div className="bg-slate-800/30 backdrop-blur-md border border-yellow-500/30 rounded-3xl p-8 mb-12">
            <h2 className="text-3xl font-bold text-white text-center mb-8">Join the Beta Program</h2>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="text-center">
                <h3 className="text-2xl font-bold text-white mb-4">Early Access</h3>
                <div className="text-5xl font-bold text-green-400 mb-2">FREE</div>
                <div className="text-gray-400">Beta testing phase</div>
                <div className="text-sm text-gray-500 mt-2">Limited spots available for founding users</div>
              </div>
              <div className="text-center">
                <h3 className="text-2xl font-bold text-white mb-4">Benefits</h3>
                <div className="text-5xl font-bold premium-text mb-2">Unlimited</div>
                <div className="text-gray-400">Communication potential</div>
                <div className="text-sm text-gray-500 mt-2">Connect with anyone, anywhere, in any language</div>
              </div>
            </div>
            <div className="mt-6 p-4 bg-green-500/10 border border-green-500/30 rounded-2xl">
              <div className="text-center">
                <div className="text-lg font-bold text-green-400 mb-2">Beta Tester Advantages</div>
                <div className="text-gray-300 text-sm">Shape the future of communication, get lifetime premium access, and join an exclusive community of early adopters.</div>
              </div>
            </div>
          </div>

          {/* Urgency Section */}
          <div className="bg-red-900/20 border border-red-500/30 rounded-3xl p-8 mb-12">
            <h2 className="text-3xl font-bold text-white text-center mb-6">Why Experience NASR APP Now?</h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-4xl mb-4"></div>
                <h4 className="text-white font-semibold mb-2">AI Translation Breakthrough</h4>
                <p className="text-gray-300 text-sm">We're at the perfect moment where AI technology finally makes real-time translation seamless and natural.</p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-4"></div>
                <h4 className="text-white font-semibold mb-2">Global Need Surge</h4>
                <p className="text-gray-300 text-sm">Remote work, global travel, and digital nomadism have created unprecedented demand for instant translation.</p>
              </div>
              <div className="text-center">
                <div className="text-4xl mb-4"></div>
                <h4 className="text-white font-semibold mb-2">Early Adopter Benefits</h4>
                <p className="text-gray-300 text-sm">Join now to influence development, get lifetime access, and be part of the communication revolution.</p>
              </div>
            </div>
          </div>

          {/* CTA Section */}
          <div className="text-center">
            <h3 className="text-3xl font-bold text-white mb-6">Ready to Break Language Barriers?</h3>
            <p className="text-xl text-gray-300 mb-8 max-w-3xl mx-auto">
              Experience the future of communication today. Join thousands who are already connecting 
              across languages with NASR APP's revolutionary technology.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a 
                href="#contact" 
                className="btn-primary text-lg px-8 py-4"
              >
                Try Live Demo
              </a>
              <a 
                href="#contact" 
                className="btn-secondary text-lg px-8 py-4"
              >
                <span className="mr-2"></span>
                Join Beta Waitlist
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default OfferForYou 