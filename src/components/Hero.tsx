const Hero = () => {
  return (
    <section id="home" className="min-h-screen flex items-center justify-center relative overflow-hidden glass-effect">

      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10 z-5">
        <div className="absolute top-20 left-20 w-32 h-32 bg-yellow-500 rounded-full blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-40 h-40 bg-yellow-500 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-60 h-60 bg-yellow-500 rounded-full blur-3xl"></div>
      </div>

      <div className="container-custom text-center relative z-10">
        <div className="max-w-4xl mx-auto">
          {/* Badge */}
          <div className="inline-flex items-center px-4 py-2 glass-effect border border-yellow-500/30 rounded-full premium-text text-sm font-medium mb-8">
            <span className="mr-2"></span>
            Phase 1: Test and Research
          </div>

          {/* Main Heading */}
          <h1 className="text-5xl md:text-7xl font-bold text-white mb-6 leading-tight">
            Break Language
            <span className="block premium-text">Barriers</span>
          </h1>

          {/* Subtitle */}
          <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto leading-relaxed">
            NASR APP enables real-time voice and text translation between languages. 
            Experience seamless communication that fosters deeper human connection globally.
          </p>

          {/* Stats */}
          <div className="flex flex-wrap justify-center gap-8 mb-12">
            <div className="text-center premium-card p-6">
              <div className="text-3xl font-bold premium-text">&lt;5s</div>
              <div className="text-gray-400">Translation Speed</div>
            </div>
            <div className="text-center premium-card p-6">
              <div className="text-3xl font-bold premium-text">50+</div>
              <div className="text-gray-400">Languages</div>
            </div>
            <div className="text-center premium-card p-6">
              <div className="text-3xl font-bold premium-text">Web</div>
              <div className="text-gray-400">Based Platform</div>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a 
              href="#contact" 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn-primary text-lg px-8 py-4"
            >
              Try NASR APP
            </a>
            <a 
              href="#about" 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn-secondary text-lg px-8 py-4"
            >
              <span className="mr-2"></span>
              Learn More
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Hero 