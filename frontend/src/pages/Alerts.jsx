import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertCircle, AlertTriangle, Info, FileText, ChevronRight, Bell } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import styles from './Alerts.module.css';

const Alerts = () => {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        setLoading(true);
        const [alertsRes] = await Promise.all([
          axios.get('/api/dashboard/alerts')
        ]);
        
        const combined = alertsRes.data.map(a => ({
            ...a,
            sortScore: a.severity === 'high' ? 100 : a.severity === 'medium' ? 50 : 10
        })).sort((a, b) => b.sortScore - a.sortScore);
        
        setAlerts(combined);
        setError(null);
      } catch (err) {
        console.error("Failed to fetch alerts", err);
        setError("Unable to load alerts at this time.");
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
  }, []);

  const getSeverityIcon = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return <AlertCircle size={22} />;
      case 'medium':
        return <AlertTriangle size={22} />;
      default:
        return <Info size={22} />;
    }
  };

  const getSeverityClass = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return styles.high;
      case 'medium':
        return styles.medium;
      default:
        return styles.low;
    }
  };

  const formatType = (type) => {
    if (!type) return 'System Alert';
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  return (
    <div className={`page active ${styles.pageWrapper}`} id="page-alerts">
      <div className={styles.alertContainer}>
        <div className={styles.header}>
          <h2>Alerts</h2>
          <p>System alerts and notifications</p>
        </div>
        
        {loading && <div className={styles.loading}>Loading alerts...</div>}
        
        {error && <div className={styles.error}>{error}</div>}
        
        {!loading && !error && alerts.length === 0 && (
          <div style={{ width: '100%', textAlign: 'center', padding: '4rem 2rem', background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)', marginTop: '2rem' }}>
            <Bell size={32} style={{ color: 'var(--muted)', marginBottom: '1rem' }} />
            <h3 style={{ margin: '0 0 0.5rem 0' }}>No active alerts</h3>
            <p style={{ color: 'var(--muted)' }}>
              There are currently no system alerts or notifications at this time.
            </p>
          </div>
        )}
        
        {!loading && !error && alerts.length > 0 && (
          <div className={styles.alertList}>
            {alerts.map((alert, index) => (
              <div 
                key={`${alert.child_id || 'sys'}-${alert.type}-${index}`} 
                className={styles.alertCard}
                onClick={() => alert.child_id && navigate(`/children?id=${alert.child_id}`)}
              >
                <div className={`${styles.alertIcon} ${getSeverityClass(alert.severity)}`}>
                  {getSeverityIcon(alert.severity)}
                </div>
                
                <div className={styles.alertContent}>
                  <div className={styles.alertHeader}>
                    <h3 className={styles.alertTitle}>{formatType(alert.type)}</h3>
                  </div>
                  
                  <p className={styles.alertMessage}>{alert.message}</p>
                  
                  <div className={styles.alertMeta}>
                    {alert.child_code && (
                      <div className={styles.metaItem}>
                        <FileText size={14} className={styles.metaIcon} />
                        <span className={styles.metaLabel}>Child Code:</span>
                        <span className={styles.metaValue}>{alert.child_code}</span>
                      </div>
                    )}
                    {alert.time_metric && (
                      <div className={styles.metaItem}>
                        <span className={styles.metaLabel} style={{ color: alert.severity === 'high' ? '#C24A3A' : '#E4A11B', fontWeight: 600 }}>
                          {alert.time_metric}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
                
                {alert.child_id && (
                  <button 
                    className={styles.viewAction} 
                    onClick={() => navigate(`/children?id=${alert.child_id}`)}
                    title="View Case"
                  >
                    <ChevronRight size={20} />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Alerts;
