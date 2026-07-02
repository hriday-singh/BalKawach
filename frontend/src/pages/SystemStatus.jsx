import React, { useState, useEffect } from 'react';
import { Database, Activity, Server, Cpu } from 'lucide-react';

const SystemStatus = () => {
  const [stats, setStats] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate API fetch for system status
    const timer = setTimeout(() => {
      setStats([
        { label: 'ASR Model', value: 'Online', icon: <Activity size={24} />, urgencyClass: 'status-green' },
        { label: 'Database', value: 'Connected', icon: <Database size={24} />, urgencyClass: 'status-green' },
        { label: 'API Server', value: '99.9% Uptime', icon: <Server size={24} />, urgencyClass: 'status-green' },
        { label: 'Processing Load', value: 'Low', icon: <Cpu size={24} />, urgencyClass: 'status-green' },
      ]);
      setIsLoading(false);
    }, 800);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="page active" id="page-system">
      <div className="page-header">
        <h2>System Status</h2>
        <p>ASR model and database status</p>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '200px' }}>
          <div className="loading-state">
            <span className="spinner-sm" style={{ width: '24px', height: '24px', borderWidth: '3px' }}></span>
            <span style={{ marginLeft: '12px', fontSize: '0.9rem', fontWeight: '500' }}>Loading system status...</span>
          </div>
        </div>
      ) : (
        <div className="stats-grid" id="system-stats">
          {stats.length > 0 ? (
            stats.map((stat, idx) => (
              <div key={idx} className={`stat-card ${stat.urgencyClass || ''}`}>
                <div className="stat-icon">{stat.icon}</div>
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))
          ) : (
            <div className="empty-state" style={{ gridColumn: '1 / -1', padding: '40px', textAlign: 'center' }}>
              <div className="empty-icon" style={{ marginBottom: '16px' }}>
                <i data-lucide="server" className="icon-sm"></i>
              </div>
              <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--text)' }}>No Status Data Available</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--muted)', marginTop: '8px' }}>
                System metrics are currently unavailable.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SystemStatus;
