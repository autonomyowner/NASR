const Footer = () => {
  return (
    <footer className="glass-effect border-t border-cyan-500/30">
      <div className="container-custom py-12">
        <div className="grid md:grid-cols-4 gap-8">
          {/* Brand */}
          <div className="md:col-span-2">
            <div className="flex items-center space-x-2 mb-4">
              <div>
                <h3 className="text-white font-bold text-xl">Travoice</h3>
                <p className="premium-text text-sm">Real-time Translation</p>
                <p className="text-gray-300 text-sm mt-1">نــاصـر آل خازم</p>
              </div>
            </div>
            <p className="text-gray-300 mb-6 max-w-md">
              Breaking down language barriers through advanced AI translation technology, 
              connecting people across cultures and enabling seamless global communication.
            </p>
            <div className="flex space-x-4">
              <a 
                href="https://github.com/nasrapp" 
                target="_blank" 
                rel="noopener noreferrer"
                className="premium-text hover:text-cyan-300 transition-colors"
              >
                <span className="text-2xl">💻</span>
              </a>
              <a 
                href="mailto:info@nasrapp.com" 
                className="premium-text hover:text-cyan-300 transition-colors"
              >
                <span className="text-2xl">📧</span>
              </a>
              <a 
                href="https://wa.me/966535523013" 
                target="_blank" 
                rel="noopener noreferrer"
                className="premium-text hover:text-cyan-300 transition-colors"
              >
                <span className="text-2xl">📱</span>
              </a>
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-white font-semibold mb-4">Quick Links</h4>
            <ul className="space-y-2">
              <li>
                <a href="#home" className="text-gray-300 hover:text-cyan-400 transition-colors">Home</a>
              </li>
              <li>
                <a href="#about" className="text-gray-300 hover:text-cyan-400 transition-colors">About</a>
              </li>
              <li>
                <a href="#services" className="text-gray-300 hover:text-cyan-400 transition-colors">Technology</a>
              </li>
              <li>
                <a href="#locations" className="text-gray-300 hover:text-cyan-400 transition-colors">Platforms</a>
              </li>
              <li>
                <a href="#contact" className="text-gray-300 hover:text-cyan-400 transition-colors">Contact</a>
              </li>
            </ul>
          </div>

          {/* Contact Info */}
          <div>
            <h4 className="text-white font-semibold mb-4">Contact</h4>
            <ul className="space-y-2 text-gray-300">
              <li className="flex items-center">
                <span className="mr-2"></span>
                Saudi Arabia
              </li>
              <li className="flex items-center">
                <span className="mr-2"></span>
                Web Platform
              </li>
              <li className="flex items-center">
                <span className="mr-2"></span>
                Phase 1: Beta
              </li>
              <li className="flex items-center">
                <span className="mr-2"></span>
                50+ Languages
              </li>
              <li className="flex items-center">
                <span className="mr-2"></span>
                <a href="https://wa.me/966535523013" target="_blank" rel="noopener noreferrer" className="premium-text hover:text-yellow-300 transition-colors">+966 53 552 3013</a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-cyan-500/30 mt-8 pt-8 flex flex-col md:flex-row justify-between items-center">
          <div className="text-gray-400 text-sm mb-4 md:mb-0">
            © 2024 Travoice. All rights reserved. Built in Saudi Arabia.
          </div>
          <div className="flex space-x-6">
            <a 
              href="#contact" 
              className="premium-text hover:text-yellow-300 transition-colors text-sm"
            >
              Join Beta
            </a>
            <a 
              href="#about" 
              className="premium-text hover:text-yellow-300 transition-colors text-sm"
            >
              Learn More
            </a>
            <a 
              href="https://github.com/nasrapp" 
              target="_blank" 
              rel="noopener noreferrer"
              className="premium-text hover:text-yellow-300 transition-colors text-sm"
            >
              GitHub
            </a>
            <a 
              href="https://wa.me/966535523013" 
              target="_blank" 
              rel="noopener noreferrer"
              className="premium-text hover:text-yellow-300 transition-colors text-sm"
            >
              WhatsApp
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}

export default Footer 