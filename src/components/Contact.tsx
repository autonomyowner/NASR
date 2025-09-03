const Contact = () => {
  const socialLinks = [
    {
      name: "GitHub",
      url: "https://github.com/nasrapp",
      icon: "",
      followers: "Source Code",
      description: "Check out our open-source contributions and development progress"
    },
    {
      name: "Email Contact",
      url: "mailto:info@nasrapp.com",
      icon: "",
      followers: "Get in Touch",
      description: "Contact our development team for questions and feedback"
    }
  ]

  return (
    <section id="contact" className="section-padding">
      <div className="container-custom">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Get in <span className="premium-text">Touch</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto">
            Ready to experience NASR APP? Connect with us and be part of breaking down language barriers.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-12">
          {/* Contact Info */}
          <div className="space-y-8">
            <div className="premium-card p-8">
              <h3 className="text-2xl font-bold text-white mb-6">Project Information</h3>
              
              <div className="space-y-4">
                <div className="flex items-start">
                  <div className="w-10 h-10 premium-gradient rounded-full flex items-center justify-center mr-4 flex-shrink-0 shadow-lg">
                    <span className="text-slate-900 text-lg"></span>
                  </div>
                  <div>
                    <h4 className="text-white font-semibold mb-1">Current Phase</h4>
                    <p className="text-gray-300 text-sm">
                      Phase 1: Test and Research
                    </p>
                  </div>
                </div>

                <div className="flex items-start">
                  <div className="w-10 h-10 premium-gradient rounded-full flex items-center justify-center mr-4 flex-shrink-0 shadow-lg">
                    <span className="text-slate-900 text-lg"></span>
                  </div>
                  <div>
                    <h4 className="text-white font-semibold mb-1">Platform</h4>
                    <p className="text-gray-300 text-sm">
                      Web-based application (Mobile coming soon)
                    </p>
                  </div>
                </div>

                <div className="flex items-start">
                  <div className="w-10 h-10 premium-gradient rounded-full flex items-center justify-center mr-4 flex-shrink-0 shadow-lg">
                    <span className="text-slate-900 text-lg"></span>
                  </div>
                  <div>
                    <h4 className="text-white font-semibold mb-1">Focus</h4>
                    <p className="text-gray-300 text-sm">
                      Real-time translation and communication
                    </p>
                  </div>
                </div>

                <div className="flex items-start">
                  <div className="w-10 h-10 premium-gradient rounded-full flex items-center justify-center mr-4 flex-shrink-0 shadow-lg">
                    <span className="text-slate-900 text-lg"></span>
                  </div>
                  <div>
                    <h4 className="text-white font-semibold mb-1">Status</h4>
                    <p className="text-gray-300 text-sm">
                      Active development and testing
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="premium-gradient p-8 rounded-2xl shadow-2xl">
              <h3 className="text-2xl font-bold text-slate-900 mb-4">Why Choose NASR APP?</h3>
              <ul className="space-y-3 text-slate-900">
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Break down language barriers
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Real-time communication
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Advanced AI technology
                </li>
                <li className="flex items-center">
                  <span className="mr-3">✓</span>
                  Global accessibility
                </li>
              </ul>
            </div>
          </div>

          {/* Social Links */}
          <div className="space-y-6">
            {socialLinks.map((social, index) => (
              <a
                key={index}
                href={social.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block premium-card p-6 hover:transform hover:scale-105"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="text-3xl mr-4"></div>
                    <div>
                      <h3 className="text-xl font-bold text-white mb-1">{social.name}</h3>
                      <p className="text-gray-300 text-sm">{social.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="premium-text font-bold text-lg">{social.followers}</div>
                    <div className="text-gray-400 text-sm">followers</div>
                  </div>
                </div>
              </a>
            ))}

            <div className="premium-card p-6">
              <h3 className="text-xl font-bold text-white mb-4">Join the Waitlist</h3>
              <p className="text-gray-300 mb-4">
                Be among the first to experience NASR APP when it launches. Sign up for early access and updates.
              </p>
              <a 
                href="#waitlist" 
                className="btn-primary w-full text-center"
              >
                Join Waitlist
              </a>
            </div>
          </div>
        </div>

        {/* CTA Section */}
        <div className="mt-16 premium-card p-8 text-center">
          <h3 className="text-3xl font-bold text-white mb-4">Ready to Break Language Barriers?</h3>
          <p className="text-gray-300 mb-8 max-w-2xl mx-auto">
            Join us in building the future of global communication. NASR APP will revolutionize how people connect across languages and cultures.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <a 
              href="#waitlist" 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn-primary text-lg px-8 py-4"
            >
              Join Waitlist
            </a>
            <a 
              href="#about" 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn-secondary text-lg px-8 py-4"
            >
              Learn More
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

export default Contact 