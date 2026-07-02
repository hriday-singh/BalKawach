import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Calendar, LineChart } from 'lucide-react';
import styles from './ChildProfile.module.css';

const ChildProfile = ({ id }) => {
  const [child, setChild] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchChild = async () => {
      try {
        const response = await axios.get(`/api/children/${id}`);
        setChild(response.data.data || response.data);
      } catch (err) {
        console.error('Error fetching child details:', err);
        setError(err.message || 'Failed to fetch child details');
      } finally {
        setLoading(false);
      }
    };
    
    if (id) {
      fetchChild();
    }
  }, [id]);

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner}></div>
        <p>Loading case file...</p>
      </div>
    );
  }

  if (error || !child) {
    return (
      <div className={styles.errorState}>
        <p>Failed to load child details. Please try again.</p>
        <button onClick={() => navigate('/children')} className={styles.backButton}>Back to Children</button>
      </div>
    );
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const getInitials = (name) => {
    if (!name) return '??';
    return name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
  };

  const formatEnum = (str) => {
    if (!str) return '';
    return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <button onClick={() => navigate('/children')} className={styles.backLink}>
          <ChevronLeft size={20} /> Case file
        </button>
      </header>

      <div className={styles.mainCard}>
        <div className={styles.cardHeader}>
          <div className={styles.avatarLarge}>
            {getInitials(child.name)}
          </div>
          <div className={styles.headerInfo}>
            <h1 className={styles.childName}>{child.name || 'Unknown'}</h1>
            <div className={styles.badges}>
              <span className={styles.childCode}>{child.child_code || 'N/A'}</span>
              <span className={styles.statusBadge}>{child.legal_status || 'Unknown'}</span>
            </div>
          </div>
        </div>

        <div className={styles.infoGrid}>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>AGE</span>
            <span className={styles.infoValue}>{child.estimated_age ? `${child.estimated_age} years` : 'N/A'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>GENDER</span>
            <span className={styles.infoValue}>{child.gender || 'N/A'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>CATEGORY</span>
            <span className={styles.infoValue}>{child.admission_category || 'N/A'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>ADMITTED</span>
            <span className={styles.infoValue}>{formatDate(child.admission_date)}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>CURRENT CCI</span>
            <span className={styles.infoValue}>{child.cci_name || child.cci_id || 'Not assigned'}</span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>LEGAL STATUS</span>
            <span className={styles.infoValue}>{child.legal_status || 'N/A'}</span>
          </div>
        </div>
      </div>

      <div className={styles.actions}>
        <button className={styles.btnPrimary} onClick={() => navigate(`/hearings?child_id=${child.id}`)}>
          <Calendar size={18} />
          Schedule hearing
        </button>
        <button className={styles.btnSecondary} onClick={() => alert("Update status feature coming soon!")}>
          <LineChart size={18} />
          Update status
        </button>
      </div>

      <div className={styles.timelineSection}>
        <h2 className={styles.timelineTitle}>Case timeline</h2>
        
        <div className={styles.timeline}>
          {child.case_history && child.case_history.length > 0 ? (
            child.case_history.map((entry, index) => (
              <div key={index} className={styles.timelineItem}>
                <div className={styles.timelineIconWrapper}>
                  <div className={`${styles.timelineIcon} ${index % 2 === 0 ? styles.iconOrange : styles.iconTeal}`}></div>
                  {index < child.case_history.length - 1 && <div className={styles.timelineLine}></div>}
                </div>
                <div className={styles.timelineContent}>
                  <div className={styles.timelineDate}>{formatDate(entry.event_date)}</div>
                  <h3 className={styles.timelineEventType}>{formatEnum(entry.event_type)}</h3>
                  <p className={styles.timelineDesc}>{entry.description}</p>
                  <p className={styles.timelineAuthor}>
                    {formatEnum(entry.performed_by_role)} {entry.performed_by_name}
                    {entry.performed_by_location ? ` • ${entry.performed_by_location}` : ''}
                  </p>
                </div>
              </div>
            ))
          ) : (
            <p className={styles.noHistory}>No case history available.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChildProfile;
