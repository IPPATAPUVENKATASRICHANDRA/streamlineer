import React from 'react';
import { Link } from 'react-router-dom';
import './Dashboard.css';

function Dashboard() {
  const userName = "Name"; // Replace with dynamic name if available
  return (
    <div className="dashboard-sketch-layout" style={{ minHeight: '100vh', width: '100vw', background: '#fff', display: 'flex' }}>
      {/* Sidebar */}
      <aside className="dashboard-sidebar-sketch">
        <div className="dashboard-sidebar-title">Streamlineer</div>
        <div className="dashboard-sidebar-buttons">
          <Link to="/inspection" className="dashboard-sketch-btn"><span className="sidebar-emoji-icon">🔍</span>Inspection</Link>
          <Link to="/template" className="dashboard-sketch-btn"><span className="sidebar-emoji-icon">📄</span>Template</Link>
          <Link to="/schedule" className="dashboard-sketch-btn"><span className="sidebar-emoji-icon">📅</span>Schedule</Link>
        </div>
      </aside>
      {/* Main Content */}
      <main className="dashboard-main-sketch">
        <div className="dashboard-main-header">Dashboard</div>
      </main>
    </div>
  );
}

export default Dashboard; 
