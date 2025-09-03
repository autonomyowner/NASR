const Services = () => {
  const services = [
    {
      icon: "",
      title: "Speech-to-Text",
      description: "Convert spoken words into text in real-time with high accuracy and low latency.",
      features: ["Real-time processing", "High accuracy", "Multiple languages"]
    },
    {
      icon: "",
      title: "Language Translation",
      description: "Instant translation between languages, breaking down communication barriers.",
      features: ["Real-time translation", "Multiple language pairs", "Context awareness"]
    },
    {
      icon: "",
      title: "Text-to-Speech",
      description: "Convert translated text back to natural-sounding speech in the target language.",
      features: ["Natural voice synthesis", "Multiple accents", "Customizable speed"]
    }
  ]

  return (
    <section id="services" className="section-padding">
      <div className="container-custom">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Our <span className="premium-text">Technology</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Cutting-edge AI-powered translation technology that enables seamless communication across language barriers.
          </p>
        </div>

        {/* Services Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {services.map((service, index) => (
            <div key={index} className="premium-card p-8 hover:transform hover:scale-105">
              <div className="text-4xl mb-4"></div>
              <h3 className="text-2xl font-bold text-white mb-4">{service.title}</h3>
              <p className="text-gray-300 mb-6 leading-relaxed">{service.description}</p>
              <ul className="space-y-2">
                {service.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center text-gray-300">
                    <span className="premium-text mr-2">✓</span>
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Pricing Section */}
        <div className="premium-card p-8">
          <div className="text-center mb-8">
            <h3 className="text-3xl font-bold text-white mb-4">Technology Overview</h3>
            <p className="text-gray-300">Advanced AI and machine learning algorithms powering real-time communication</p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 items-center">
            {/* Pricing Card */}
            <div className="premium-gradient p-8 rounded-2xl text-center shadow-2xl">
              <div className="text-4xl font-bold text-slate-900 mb-2">Core Innovation</div>
              <div className="text-slate-900 text-lg mb-6">Real-time, low-latency processing</div>
              <ul className="space-y-3 text-slate-900 text-left">
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Neural machine translation
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Advanced speech recognition
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Natural language processing
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Cloud-based infrastructure
                </li>
              </ul>
            </div>

            {/* Requirements */}
            <div className="space-y-6">
              <div className="premium-card p-6">
                <h4 className="text-xl font-bold text-white mb-4">Current Phase</h4>
                <div className="space-y-3">
                  <div className="flex items-center text-gray-300">
                    <span className="premium-text mr-3"></span>
                    Phase 1: Test and Research
                  </div>
                  <div className="flex items-center text-gray-300">
                    <span className="premium-text mr-3"></span>
                    Web-based platform
                  </div>
                  <div className="flex items-center text-gray-300">
                    <span className="premium-text mr-3"></span>
                    Mobile app in development
                  </div>
                </div>
              </div>

              <div className="premium-card p-6">
                <h4 className="text-xl font-bold text-white mb-4">Future Roadmap</h4>
                <div className="space-y-3">
                  <div className="flex items-center text-gray-300">
                    <span className="premium-text mr-3"></span>
                    Mobile applications
                  </div>
                  <div className="flex items-center text-gray-300">
                    <span className="premium-text mr-3"></span>
                    Enterprise solutions
                  </div>
                  <div className="flex items-center text-gray-300">
                    <span className="premium-text mr-3"></span>
                    Global expansion
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Services 