import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const location = useLocation()

  return (
    <nav className="fixed w-full z-50 glass-effect border-b border-cyan-500/30">
      <div className="container-custom">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-2">
            <div>
              <h1 className="text-white font-bold text-xl">Travoice</h1>
              <p className="premium-text text-xs">Real-time Translation</p>
            </div>
          </div>

          {/* Desktop Menu */}
          <div className="hidden md:flex items-center space-x-8">
            <Link 
              to="/" 
              className={`transition-colors ${location.pathname === '/' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
            >
              Home
            </Link>
            <Link 
              to="/offer-for-you" 
              className={`transition-colors ${location.pathname === '/offer-for-you' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
            >
              About Us
            </Link>
            <Link 
              to="/call" 
              className={`transition-colors ${location.pathname === '/call' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
            >
              Call
            </Link>
            <Link 
              to="/roadmap" 
              className={`transition-colors ${location.pathname === '/roadmap' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
            >
              Roadmap
            </Link>
            <a 
              href="#contact" 
              className="btn-primary"
            >
              Try Travoice
            </a>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="md:hidden text-white hover:text-cyan-400 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden glass-effect border-t border-cyan-500/30">
            <div className="px-2 pt-2 pb-3 space-y-1">
              <Link 
                to="/" 
                className={`block px-3 py-2 transition-colors ${location.pathname === '/' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
                onClick={() => setIsMenuOpen(false)}
              >
                Home
              </Link>
              <Link 
                to="/offer-for-you" 
                className={`block px-3 py-2 transition-colors ${location.pathname === '/offer-for-you' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
                onClick={() => setIsMenuOpen(false)}
              >
                About Us
              </Link>
              <Link 
                to="/call" 
                className={`block px-3 py-2 transition-colors ${location.pathname === '/call' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
                onClick={() => setIsMenuOpen(false)}
              >
                Call
              </Link>
              <Link 
                to="/roadmap" 
                className={`block px-3 py-2 transition-colors ${location.pathname === '/roadmap' ? 'text-cyan-400' : 'text-white hover:text-cyan-400'}`}
                onClick={() => setIsMenuOpen(false)}
              >
                Roadmap
              </Link>
              <a 
                href="#contact" 
                className="block px-3 py-2 btn-primary text-center"
              >
                Try Travoice
              </a>
            </div>
          </div>
        )}
      </div>
    </nav>
  )
}

export default Navbar 