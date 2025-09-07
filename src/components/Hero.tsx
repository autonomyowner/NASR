import TypewriterEffect from './TypewriterEffect'

const Hero = () => {
  const typewriterWords = ['Translate', 'Transcribe', 'Connect Globally']

  return (
    <section id="home" className="min-h-screen flex items-center justify-center hero-grid-light">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="space-y-8">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-2 bg-aqua-section/20 border border-aqua-accent/30 rounded-full text-aqua-text text-sm font-medium">
            <span className="mr-2">🌐</span>
            WEBSITE / Early Access
          </div>

          {/* Main Heading */}
          <div className="space-y-4">
            <h1 className="display-font text-4xl sm:text-5xl md:text-6xl lg:text-7xl xl:text-8xl font-bold text-aqua-text leading-tight">
              Your end‑to‑end Language Partner
            </h1>
            
            {/* Typewriter Effect */}
            <div className="text-2xl sm:text-3xl md:text-4xl text-aqua-text-secondary font-medium">
              <TypewriterEffect 
                words={typewriterWords}
                speed={120}
                pauseTime={2500}
                className="text-aqua-accent"
              />
            </div>
          </div>

          {/* Subtitle */}
          <p className="text-lg sm:text-xl md:text-2xl text-aqua-text-secondary max-w-4xl mx-auto leading-relaxed">
            Real‑time voice and text translation that connects people instantly.
          </p>

          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-6">
            <div className="bg-white/40 backdrop-blur-sm border border-aqua-accent/20 rounded-xl p-6 min-w-[160px]">
              <div className="text-2xl md:text-3xl font-bold text-aqua-accent mb-2">&lt;5s</div>
              <div className="text-aqua-text text-sm">Translation Speed</div>
            </div>
            <div className="bg-white/40 backdrop-blur-sm border border-golden/30 rounded-xl p-6 min-w-[160px]">
              <div className="text-2xl md:text-3xl font-bold text-golden mb-2">Soon</div>
              <div className="text-aqua-text text-sm">50+ Languages</div>
              <div className="text-xs text-golden mt-1">In Development</div>
            </div>
            <div className="bg-white/40 backdrop-blur-sm border border-aqua-accent/20 rounded-xl p-6 min-w-[160px]">
              <div className="text-2xl md:text-3xl font-bold text-aqua-accent mb-2">Web</div>
              <div className="text-aqua-text text-sm">Based Platform</div>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
            <a 
              href="#contact" 
              className="btn-primary text-lg px-8 py-4"
            >
              Start Translating
            </a>
            <a 
              href="#about" 
              className="btn-secondary text-lg px-8 py-4"
            >
              See How It Works
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Hero