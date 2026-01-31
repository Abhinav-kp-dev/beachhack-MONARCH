/**
 * Main App Component - Enhanced UI/UX
 * Features: Smooth transitions, responsive design, loading states
 */

import React, { useState, useEffect } from 'react';
import AgentDashboard from './components/AgentDashboard';
import CustomerInteraction from './components/CustomerInteraction';
import ContextIntelligence from './components/ContextIntelligence';
import './App.css';

function App() {
  const [activeView, setActiveView] = useState('dashboard');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleViewChange = (view) => {
    if (view === activeView) return;
    
    setIsTransitioning(true);
    setTimeout(() => {
      setActiveView(view);
      setIsTransitioning(false);
      setIsMobileMenuOpen(false);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 150);
  };

  const navItems = [
    { id: 'dashboard', label: 'Agent Dashboard', icon: '🎯' },
    { id: 'interaction', label: 'New Interaction', icon: '✍️' },
    { id: 'intelligence', label: 'Context Intelligence', icon: '🧠' }
  ];

  return (
    <div className="App">
      {/* Enhanced Navbar */}
      <nav className="navbar">
        <div className="navbar-brand">
          <div className="brand-icon">🧠</div>
          <div className="brand-text">
            <h1>Customer Intelligence</h1>
            <p className="brand-subtitle">AI-Powered Context System</p>
          </div>
        </div>

        {/* Mobile Menu Toggle */}
        <button 
          className="mobile-menu-toggle"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          aria-label="Toggle menu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>

        {/* Navigation Links */}
        <div className={`nav-links ${isMobileMenuOpen ? 'mobile-open' : ''}`}>
          {navItems.map(item => (
            <button
              key={item.id}
              className={`nav-button ${activeView === item.id ? 'active' : ''}`}
              onClick={() => handleViewChange(item.id)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Main Content with Transition */}
      <main className={`main-content ${isTransitioning ? 'transitioning' : ''}`}>
        <div className="content-wrapper">
          {activeView === 'dashboard' && <AgentDashboard />}
          {activeView === 'interaction' && <CustomerInteraction />}
          {activeView === 'intelligence' && <ContextIntelligence />}
        </div>
      </main>

      {/* Enhanced Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-left">
            <p className="footer-title">Context-Aware Customer Intelligence</p>
            <p className="footer-subtitle">BeachHack 2026 | Powered by AI</p>
          </div>
          <div className="footer-right">
            <span className="status-indicator">●</span>
            <span className="status-text">System Online</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
