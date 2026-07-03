import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { ChevronLeft, Calendar, LineChart, Users, FileText } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import StatusUpdateModal from '../components/forms/StatusUpdateModal';
import FamilyVisitModal from '../components/forms/FamilyVisitModal';
import styles from './ChildProfile.module.css';

const ChildProfile = ({ id }) => {
  const [child, setChild] = useState(null);
  const [visits, setVisits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isStatusModalOpen, setIsStatusModalOpen] = useState(false);
  const [isVisitModalOpen, setIsVisitModalOpen] = useState(false);
  const [activeHearing, setActiveHearing] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const navigate = useNavigate();
  const { token, user } = useAuth();
  
  const canViewOrders = ['cwc_member', 'cwc_chairperson', 'dcpu_officer', 'system_admin', 'wcd_official'].includes(user?.role);

  const fetchChildAndVisits = async () => {
    try {
      setLoading(true);
      const [childRes, visitsRes, hearingsRes] = await Promise.all([
        axios.get(`/api/children/${id}`),
        axios.get(`/api/children/${id}/visits`, { headers: { 'Authorization': `Bearer ${token}` } }).catch(() => ({ data: [] })),
        axios.get(`/api/hearings`).catch(() => ({ data: [] }))
      ]);
      setChild(childRes.data.data || childRes.data);
      setVisits(visitsRes.data || []);

      const allHearings = hearingsRes.data || [];
      const childHearings = allHearings.filter(h => h.child_id == id);
      setActiveHearing(childHearings.some(h => h.status === 'scheduled' || h.status === 'in_progress'));
    } catch (err) {
      console.error('Error fetching child details:', err);
      setError(err.message || 'Failed to fetch child details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchChildAndVisits();
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
    return str.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()).join(' ');
  };

  const handleHearingClick = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      navigate(`/hearings?child_id=${child.id}`);
    }, 500);
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
            <span className={styles.infoValue}>
              {child.cci_name 
                ? `${child.cci_name}${child.cci_district ? `, ${child.cci_district}` : ''}` 
                : (child.cci_id || 'Not assigned')}
            </span>
          </div>
          <div className={styles.infoItem}>
            <span className={styles.infoLabel}>LEGAL STATUS</span>
            <span className={styles.infoValue}>{child.legal_status || 'N/A'}</span>
          </div>
        </div>
      </div>

      <div className={styles.actions}>
        <button className={styles.btnPrimary} onClick={handleHearingClick}>
          <Calendar size={18} />
          {activeHearing ? 'Go to hearing' : 'Schedule hearing'}
        </button>
        <button className={styles.btnSecondary} onClick={() => setIsStatusModalOpen(true)}>
          <LineChart size={18} />
          Update status
        </button>
        <button className={styles.btnSecondary} onClick={() => setIsVisitModalOpen(true)}>
          <Users size={18} />
          Log Visit
        </button>
        {canViewOrders && (
          <button className={styles.btnSecondary} onClick={() => navigate(`/orders?search=${encodeURIComponent(child.child_code || child.name)}`)}>
            <FileText size={18} />
            CWC Orders
          </button>
        )}
      </div>

      <div className={styles.timelineContainer}>
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
      <div className={styles.timelineSection} style={{ marginTop: '2rem' }}>
        <h2 className={styles.timelineTitle}>Family Visits</h2>
        <div className={styles.timeline}>
          {visits.length > 0 ? (
            visits.map((visit, index) => (
              <div key={index} className={styles.timelineItem}>
                <div className={styles.timelineIconWrapper}>
                  <div className={`${styles.timelineIcon} ${styles.iconTeal}`}></div>
                  {index < visits.length - 1 && <div className={styles.timelineLine}></div>}
                </div>
                <div className={styles.timelineContent}>
                  <div className={styles.timelineDate}>{formatDate(visit.visit_date)}</div>
                  <h3 className={styles.timelineEventType}>{visit.visitor_name} ({visit.relationship})</h3>
                  <p className={styles.timelineDesc}>Duration: {visit.duration_minutes} mins</p>
                  {visit.notes && <p className={styles.timelineAuthor}>Notes: {visit.notes}</p>}
                </div>
              </div>
            ))
          ) : (
            <p className={styles.noHistory}>No visits logged yet.</p>
          )}
        </div>
      </div>
      </div>

      {isStatusModalOpen && (
        <StatusUpdateModal 
          child={child} 
          token={token} 
          onClose={() => setIsStatusModalOpen(false)} 
          onStatusUpdated={() => {
            setIsStatusModalOpen(false);
            fetchChildAndVisits();
          }} 
        />
      )}

      {isVisitModalOpen && (
        <FamilyVisitModal 
          childId={child.id} 
          token={token} 
          onClose={() => setIsVisitModalOpen(false)} 
          onVisitLogged={() => {
            setIsVisitModalOpen(false);
            fetchChildAndVisits();
          }} 
        />
      )}

      {isTransitioning && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.7)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column', color: 'white'
        }}>
          <div style={{ 
            marginBottom: '1rem', width: '40px', height: '40px', 
            border: '4px solid rgba(255,255,255,0.3)', borderTopColor: 'white', 
            borderRadius: '50%', animation: 'spin 1s linear infinite' 
          }}>
            <style>
              {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
            </style>
          </div>
          <p style={{ fontWeight: 600 }}>Preparing hearing console...</p>
        </div>
      )}
    </div>
  );
};

export default ChildProfile;
