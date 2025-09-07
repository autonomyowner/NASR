const About = () => {
  return (
    <section id="about" className="section-padding glass-effect">
      <div className="container-custom">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            About <span className="premium-text">Travoice</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            We're building the future of global communication - eliminating language barriers through 
            real-time translation technology that connects people across cultures.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-12 items-center">
          {/* Left Content */}
          <div className="space-y-8">
            <div className="premium-card p-8">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 premium-gradient rounded-full flex items-center justify-center mr-4 shadow-lg">
                </div>
                <h3 className="text-2xl font-bold text-white">Our Mission</h3>
              </div>
              <p className="text-gray-300 leading-relaxed">
                To break down language barriers in real-time, enabling seamless and natural voice and text 
                conversations between people anywhere in the world, fostering deeper human connection.
              </p>
            </div>

            <div className="premium-card p-8">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 premium-gradient rounded-full flex items-center justify-center mr-4 shadow-lg">
                </div>
                <h3 className="text-2xl font-bold text-white">Our Vision</h3>
              </div>
              <p className="text-gray-300 leading-relaxed">
                To become the world's leading real-time translation platform, connecting people 
                regardless of their native language through advanced AI technology.
              </p>
            </div>
          </div>

          {/* Right Content */}
          <div className="space-y-6">
            <div className="premium-gradient p-8 rounded-2xl shadow-2xl">
              <h3 className="text-2xl font-bold text-slate-900 mb-4">Why Choose Travoice?</h3>
              <ul className="space-y-3 text-slate-900">
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Real-time speech-to-text conversion
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Instant language translation
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Natural text-to-speech synthesis
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Low-latency processing (&lt;5 seconds)
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Web-based platform (mobile coming soon)
                </li>
              </ul>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="premium-card p-6 text-center">
                <div className="text-3xl font-bold premium-text mb-2">Phase 1</div>
                <div className="text-gray-400 text-sm">Test & Research</div>
              </div>
              <div className="premium-card p-6 text-center">
                <div className="text-3xl font-bold premium-text mb-2">2+ Users</div>
                <div className="text-gray-400 text-sm">Conversations</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default About 