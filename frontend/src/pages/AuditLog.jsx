import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AuditLog = () => {
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        setIsLoading(true);
        const res = await axios.get('/api/audit');
        const data = res.data || [];
        setLogs(data);
        setFilteredLogs(data);
      } catch (err) {
        console.error("Failed to load audit logs", err);
        setError("Could not load audit logs. You might need admin privileges.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchLogs();
  }, []);

  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredLogs(logs);
      return;
    }
    const term = searchTerm.toLowerCase();
    const filtered = logs.filter(log => 
      (log.user_name && log.user_name.toLowerCase().includes(term)) ||
      (log.user_id && log.user_id.toLowerCase().includes(term)) ||
      (log.action && log.action.toLowerCase().includes(term)) ||
      (log.entity_type && log.entity_type.toLowerCase().includes(term)) ||
      (log.details && log.details.toLowerCase().includes(term))
    );
    setFilteredLogs(filtered);
  }, [searchTerm, logs]);

  return (
    <div className="page active" id="page-audit">
      <div className="page-header">
        <h2>Audit Log</h2>
        <p>System activity and change history</p>
      </div>
      
      {error && (
        <div style={{ padding: '20px', color: 'red', background: '#ffebee', borderRadius: '8px', marginBottom: '24px' }}>
          {error}
        </div>
      )}

      <div className="table-controls" style={{ marginBottom: '24px', display: 'flex', gap: '16px' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <input 
            type="text" 
            className="search-input" 
            placeholder="Search audit log…" 
            id="audit-search" 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ 
              width: '100%',
              padding: '12px 16px', 
              paddingLeft: '40px',
              borderRadius: 'var(--radius-lg)', 
              border: '1px solid var(--border)',
              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.02)',
              fontSize: '0.9rem',
              transition: 'all 0.2s ease'
            }}
          />
          <svg 
            style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }}
            xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>
      </div>
      
      <div id="audit-table-area">
        {isLoading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '60px', background: 'var(--surface)', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border)' }}>
            <div className="loading-state">
              <span className="spinner-sm" style={{ width: '20px', height: '20px', borderWidth: '2px' }}></span>
              <span style={{ marginLeft: '12px', fontSize: '0.9rem' }}>Loading audit log…</span>
            </div>
          </div>
        ) : (
          <div className="table-wrap" style={{ 
            border: '1px solid var(--border)', 
            borderRadius: 'var(--radius-lg)', 
            boxShadow: '0 2px 8px rgba(43, 38, 34, 0.04)',
            background: 'var(--input-bg)'
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontWeight: '700', letterSpacing: '0.5px', color: 'var(--muted)', textTransform: 'uppercase', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>Timestamp</th>
                  <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontWeight: '700', letterSpacing: '0.5px', color: 'var(--muted)', textTransform: 'uppercase', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>User ID</th>
                  <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontWeight: '700', letterSpacing: '0.5px', color: 'var(--muted)', textTransform: 'uppercase', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>Action</th>
                  <th style={{ padding: '16px 20px', fontSize: '0.75rem', fontWeight: '700', letterSpacing: '0.5px', color: 'var(--muted)', textTransform: 'uppercase', borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.length > 0 ? (
                  filteredLogs.map((log, index) => (
                    <tr key={index} style={{ borderBottom: index !== filteredLogs.length - 1 ? '1px solid var(--border)' : 'none', transition: 'background-color 0.2s ease' }}>
                      <td style={{ padding: '16px 20px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{new Date(log.created_at).toLocaleString()}</td>
                      <td style={{ padding: '16px 20px', fontSize: '0.85rem', fontWeight: '500', color: 'var(--text)' }}>
                        {log.user_name || log.user_id || 'System'}
                      </td>
                      <td style={{ padding: '16px 20px' }}>
                        <span className={`tag ${log.action.includes('CREATE') || log.action.includes('REGISTER') ? 'tag-green' : log.action.includes('DELETE') ? 'tag-red' : 'tag-accent'}`} style={{ padding: '4px 10px', borderRadius: '6px' }}>
                          {log.action}
                        </span>
                      </td>
                      <td style={{ padding: '16px 20px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{log.details}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" style={{ padding: '60px 20px', textAlign: 'center', color: 'var(--muted)' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--muted)', opacity: 0.5 }}>
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                          <line x1="16" y1="13" x2="8" y2="13"></line>
                          <line x1="16" y1="17" x2="8" y2="17"></line>
                          <polyline points="10 9 9 9 8 9"></polyline>
                        </svg>
                        <span style={{ fontSize: '0.95rem', fontWeight: '500' }}>No audit entries found</span>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AuditLog;
