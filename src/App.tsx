import './App.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Home from './components/Home'
import OfferForYou from './components/OfferForYou'
import EnhancedCall from './components/EnhancedCall'
import SimpleCall from './components/SimpleCall'
import Roadmap from './components/Roadmap'
import Footer from './components/Footer'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-cyan-900 to-slate-900">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/offer-for-you" element={<OfferForYou />} />
          <Route path="/call" element={<EnhancedCall />} />
          <Route path="/room/:roomId" element={<EnhancedCall />} />
          <Route path="/simple-call" element={<SimpleCall />} />
          <Route path="/simple-room/:roomId" element={<SimpleCall />} />
          <Route path="/roadmap" element={<Roadmap />} />
        </Routes>
        <Footer />
      </div>
    </Router>
  )
}

export default App
