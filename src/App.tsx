import './App.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './components/Home'
import OfferForYou from './components/OfferForYou'
import Call from './components/Call'
import Footer from './components/Footer'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-cyan-900 to-slate-900">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/offer-for-you" element={<OfferForYou />} />
          <Route path="/call" element={<Call />} />
        </Routes>
        <Footer />
      </div>
    </Router>
  )
}

export default App
