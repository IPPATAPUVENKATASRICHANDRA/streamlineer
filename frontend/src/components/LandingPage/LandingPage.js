import React from 'react';
import { Link } from 'react-router-dom';
import '../SignUp/SignUp.css';
import './LandingPage.css';

function LandingPage() {
  return (
    <div className="landing-container" style={{ minHeight: '100vh', width: '100vw', background: '#fff', position: 'relative' }}>
      {/* Top-left App Name */}
      <div style={{ position: 'fixed', top: 32, left: 32, zIndex: 10 }}>
        <span style={{ fontFamily: 'National Park, sans-serif', fontSize: '2rem', fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#000' }}>
          Streamlineer
        </span>
      </div>
      {/* Top-right Login/Sign Up */}
      <div style={{ position: 'fixed', top: 32, right: 32, display: 'flex', gap: 16, zIndex: 10 }}>
        <Link to="/login" className="login-btn" style={{ width: 110, padding: '10px 0', fontSize: '1rem', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          Login
        </Link>
        <Link to="/signup" className="create-account-btn" style={{ width: 110, padding: '10px 0', fontSize: '1rem', textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          Sign Up
        </Link>
      </div>
      {/* Centered Welcome Text with fade-in and Get Started button */}
      <main className="landing-fadein" style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center' }}>
        <h2 className="signup-title" style={{ fontSize: '2.5rem', marginBottom: '1.5rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#000', fontWeight: 800 }}>
          Welcome to Streamlineer
        </h2>
        <Link to="/signup" className="create-account-btn" style={{ width: 220, margin: '0 auto' }}>
          Get Started
        </Link>
      </main>
    </div>
  );
}

export default LandingPage;