import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { List, TrendingUp, AlertTriangle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import styles from './Dashboard.module.css';

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, alertsRes] = await Promise.all([
          axios.get('/api/dashboard/stats'),
          axios.get('/api/dashboard/alerts')
        ]);
        
        setStats(statsRes.data);
        setAlerts(alertsRes.data);
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner}></div>
        <p>Loading dashboard metrics...</p>
      </div>
    );
  }

  const getStatusColor = (status) => {
    const map = {
      'Under Inquiry': '#E4720C',
      'Under Review': '#E4A11B',
      'Restored to Family': '#5C9165',
      'Placed in Foster Care': '#468798',
      'Legally Free for Adoption': '#8E44AD',
      'Aged Out': '#9A9188'
    };
    return map[status] || '#C24A3A'; // Conflict with Law / Fallback
  };

  const totalChildren = stats?.total_children || 0;
  
  // Calculate SVG circles
  let cumulativeOffset = 0;
  const circles = [];
  const legend = [];
  
  if (stats?.by_status && totalChildren > 0) {
    Object.entries(stats.by_status).forEach(([status, count]) => {
      if (count === 0) return;
      const percentage = (count / totalChildren) * 100;
      const color = getStatusColor(status);
      circles.push(
        <circle 
          key={status}
          cx="21" cy="21" r="15.9155" 
          fill="transparent" 
          stroke={color} 
          strokeWidth="6" 
          strokeDasharray={`${percentage} ${100 - percentage}`} 
          strokeDashoffset={-cumulativeOffset} 
        />
      );
      legend.push({ label: status, count, color });
      cumulativeOffset += percentage;
    });
  } else {
    // Empty state
    circles.push(
      <circle 
        key="empty" cx="21" cy="21" r="15.9155" 
        fill="transparent" stroke="#eee" strokeWidth="6"
      />
    );
  }

  return (
    <div className={styles.dashboardPage}>
      {/* Custom Header */}
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h2>Dashboard</h2>
          <p style={{ textTransform: 'capitalize' }}>{user?.location || 'Location not set'}</p>
        </div>
      </header>
      
      {/* Hero Card */}
      <div className={styles.heroCard} onClick={() => navigate('/children')} style={{ cursor: 'pointer' }}>
        <div className={styles.heroGlow}></div>
        <div className={styles.heroSubtitle}>
          {user?.location?.toUpperCase()} · {user?.role?.replace(/_/g, ' ').toUpperCase()}
        </div>
        <div className={styles.heroTitle}>
          <span className={styles.heroNumber}>{totalChildren}</span>
          <span className={styles.heroText}>children under care</span>
        </div>
        <div className={styles.heroPills}>
          {stats?.overdue_deadlines > 0 && (
            <div className={`${styles.heroPill} ${styles.red}`}>
              <span className={styles.pillDot}></span>
              {stats.overdue_deadlines} reviews overdue
            </div>
          )}
          {stats?.lfa_eligible_count > 0 && (
            <div className={`${styles.heroPill} ${styles.gold}`}>
              <span className={styles.pillDot}></span>
              {stats.lfa_eligible_count} LFA to file
            </div>
          )}
        </div>
      </div>

      {/* Stats Row */}
      <div className={styles.statsRow}>
        <div className={styles.statCard} onClick={() => navigate('/alerts')}>
          <div className={styles.statHeader}>
            <List size={18} />
            <span>Pending deadlines</span>
          </div>
          <div className={styles.statValue}>{stats?.approaching_deadlines || 0}</div>
        </div>
        <div className={styles.statCard} onClick={() => navigate('/hearings')}>
          <div className={`${styles.statHeader} ${styles.green}`}>
            <TrendingUp size={18} />
            <span>Hearings</span>
          </div>
          <div className={styles.statValue}>{stats?.total_hearings || 0}</div>
        </div>
      </div>

      {/* Chart Card */}
      <div className={styles.chartCard}>
        <h3 className={styles.chartTitle}>Case status breakdown</h3>
        <div className={styles.chartLayout}>
          <div className={styles.chartContainer}>
            <svg viewBox="0 0 42 42" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)', overflow: 'visible' }}>
              <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#eee" strokeWidth="6"></circle>
              {circles}
            </svg>
            <div className={styles.chartCenter}>
              <span className={styles.chartCenterNumber}>{totalChildren}</span>
              <span className={styles.chartCenterLabel}>TOTAL</span>
            </div>
          </div>
          
          <div className={styles.legendList}>
            {legend.map(item => (
              <div key={item.label} className={styles.legendItem}>
                <div className={styles.legendLeft}>
                  <div className={styles.legendDot} style={{ background: item.color }}></div>
                  <span className={styles.legendLabelText} title={item.label}>{item.label}</span>
                </div>
                <div className={styles.legendRight}>{item.count}</div>
              </div>
            ))}
            {legend.length === 0 && (
              <div style={{ color: '#6B6259', fontSize: '0.85rem' }}>No case data available.</div>
            )}
          </div>
        </div>
      </div>

      {/* Needs Attention Section */}
      <div className={styles.sectionHeader}>
        <h3 className={styles.sectionTitle}>Needs attention</h3>
      </div>
      
      {alerts.slice(0, 3).map((alert, i) => (
        <div 
          key={i} 
          className={styles.alertCard}
          onClick={() => alert.child_id ? navigate(`/children?id=${alert.child_id}`) : navigate('/alerts')}
        >
          <div className={styles.alertIcon}>
            <AlertTriangle size={20} color={alert.severity === 'high' ? '#C24A3A' : '#E4A11B'} />
          </div>
          <div className={styles.alertContent}>
            <div className={styles.alertTitleRow}>
              <span className={styles.alertTitle}>{alert.type.replace(/_/g, ' ')}</span>
              {alert.severity === 'high' && <span className={styles.alertBadge}>URGENT</span>}
            </div>
            <p className={styles.alertDesc}>{alert.message}</p>
          </div>
        </div>
      ))}
      {alerts.length === 0 && (
        <div style={{ color: '#6B6259', fontSize: '0.9rem', padding: '16px 0' }}>No pending alerts. You're all caught up!</div>
      )}
      
      

    </div>
  );
};

export default Dashboard;
