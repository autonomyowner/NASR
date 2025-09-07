const Locations = () => {
  const platforms = [
    {
      platform: "Web Application",
      status: "Active",
      features: [
        { feature: "Real-time translation", available: true },
        { feature: "Voice communication", available: true },
        { feature: "Text chat", available: true }
      ],
      url: "#",
      description: "Our primary web-based platform accessible from any modern browser."
    },
    {
      platform: "Mobile App",
      status: "In Development",
      features: [
        { feature: "iOS version", available: false },
        { feature: "Android version", available: false },
        { feature: "Offline capabilities", available: false }
      ],
      url: "#",
      description: "Native mobile applications for iOS and Android platforms."
    }
  ]

  return (
    <section id="locations" className="section-padding glass-effect">
      <div className="container-custom">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Platform <span className="premium-text">Availability</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Travoice is designed to be accessible across multiple platforms, ensuring you can communicate from anywhere, anytime.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {platforms.map((platform, index) => (
            <div key={index} className="premium-card p-8 hover:transform hover:scale-105">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-2xl font-bold text-white">{platform.platform}</h3>
                <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                  platform.status === "Active" 
                    ? "bg-green-500/20 text-green-400 border border-green-400/30"
                    : "bg-yellow-500/20 text-yellow-400 border border-yellow-400/30"
                }`}>
                  {platform.status}
                </span>
              </div>

              {/* Description */}
              <p className="text-gray-300 mb-6 leading-relaxed">
                {platform.description}
              </p>

              {/* Schedules */}
              <div className="mb-6">
                <h4 className="text-lg font-semibold text-white mb-3">Features:</h4>
                <div className="space-y-2">
                  {platform.features.map((feature, featureIndex) => (
                    <div key={featureIndex} className={`flex items-center justify-between p-3 rounded-lg ${
                      feature.available 
                        ? "bg-green-500/10 border border-green-400/20" 
                        : "bg-gray-500/10 border border-gray-400/20"
                    }`}>
                      <span className={`text-sm ${
                        feature.available ? "text-green-400" : "text-gray-400"
                      }`}>
                        {feature.feature}
                      </span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        feature.available 
                          ? "bg-green-500/20 text-green-400" 
                          : "bg-gray-500/20 text-gray-400"
                      }`}>
                        {feature.available ? "Available" : "Coming Soon"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Map Link */}
              <a 
                href={platform.url}
                className="inline-flex items-center premium-text hover:text-cyan-300 transition-colors"
              >
                <span className="mr-2"></span>
                {platform.status === "Active" ? "Access Platform" : "Learn More"}
                <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          ))}
        </div>

        {/* Additional Info */}
        <div className="mt-12 premium-card p-8">
          <div className="text-center">
            <h3 className="text-2xl font-bold text-white mb-4">Future Platforms</h3>
            <p className="text-gray-300 mb-6">
              We're working on expanding Travoice to more platforms and devices to ensure maximum accessibility.
            </p>
            <a 
              href="#contact" 
              className="btn-primary"
            >
              Stay Updated
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Locations 