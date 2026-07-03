import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, User, Filter } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ChildProfile from './ChildProfile';
import ChildRegistrationForm from '../components/forms/ChildRegistrationForm';
import styles from './Children.module.css';

const Children = () => {
  const [children, setChildren] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isRegModalOpen, setIsRegModalOpen] = useState(false);
  const filterRef = React.useRef(null);
  const { user, token } = useAuth();
  
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const childId = searchParams.get('id');

  useEffect(() => {
    const fetchChildren = async () => {
      try {
        const response = await axios.get('/api/children');
        setChildren(response.data.data || response.data || []);
      } catch (err) {
        console.error('Error fetching children:', err);
        setError(err.message || 'Failed to fetch children');
      } finally {
        setLoading(false);
      }
    };
    
    // Only fetch if not looking at a specific child to save unnecessary calls
    if (!childId) {
      fetchChildren();
    }
  }, [childId]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (filterRef.current && !filterRef.current.contains(event.target)) {
        setIsFilterOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (childId) {
    return <ChildProfile id={childId} />;
  }

  const filteredChildren = children.filter(child => {
    const searchLower = search.toLowerCase();
    const matchesSearch = 
      (child.name && child.name.toLowerCase().includes(searchLower)) || 
      (child.child_code && child.child_code.toLowerCase().includes(searchLower));
    
    const matchesFilter = filter === 'All' || child.legal_status === filter;
    
    return matchesSearch && matchesFilter;
  });

  const getStatusClass = (status) => {
    switch(status?.toLowerCase()) {
      case 'under inquiry': 
      case 'under review':
        return styles.statusAmber;
      case 'legally free for adoption':
      case 'in adoption pool':
        return styles.statusRed;
      case 'restored to family':
      case 'placed in foster care':
      case 'placed in sponsorship':
        return styles.statusGreen;
      case 'aged out':
        return styles.statusMuted;
      default: 
        return styles.statusMuted;
    }
  };

  const filterOptions = [
    'All', 'Under Inquiry', 'Legally Free for Adoption', 
    'In Adoption Pool', 'Restored to Family', 'Placed in Foster Care', 
    'Placed in Sponsorship', 'Aged Out', 'Under Review'
  ];

  return (
    <div className={`page active ${styles.container}`} id="page-children">
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Children</h2>
          <p className={styles.subtitle}>Manage children under care</p>
        </div>
        {['cci_staff', 'dcpu_officer', 'system_admin'].includes(user?.role) && (
          <button 
            onClick={() => setIsRegModalOpen(true)}
            style={{ 
              background: 'var(--accent)', color: 'var(--bg)', border: 'none', 
              padding: '0.6rem 1.2rem', borderRadius: '6px', fontWeight: 600, cursor: 'pointer' 
            }}
          >
            + Add Child
          </button>
        )}
      </div>

      <div className={styles.controls}>
        <div className={styles.searchBox}>
          <Search className={styles.searchIcon} size={18} />
          <input 
            type="text" 
            placeholder="Search by name or code..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={styles.searchInput}
          />
        </div>
        
        <div className={styles.filterWrapper} ref={filterRef}>
          <div 
            className={styles.filterButton} 
            onClick={() => setIsFilterOpen(!isFilterOpen)}
          >
            <Filter className={styles.filterIcon} size={16} />
            <span>{filter}</span>
          </div>
          
          {isFilterOpen && (
            <div className={styles.filterDropdown}>
              {filterOptions.map(opt => (
                <div 
                  key={opt} 
                  className={`${styles.filterOption} ${filter === opt ? styles.filterOptionActive : ''}`}
                  onClick={() => {
                    setFilter(opt);
                    setIsFilterOpen(false);
                  }}
                >
                  {opt}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {loading ? (
        <div className={styles.loadingState}>
          <div className={styles.spinner}></div>
          <p>Loading children records...</p>
        </div>
      ) : filteredChildren.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>
            <User size={24} />
          </div>
          <h3>No children found</h3>
          <p>Try adjusting your search or filters.</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {filteredChildren.map(child => (
            <div 
              key={child.id || child.child_code} 
              className={styles.card}
              onClick={() => navigate(`/children?id=${child.id || child.child_code}`)}
              style={{ cursor: 'pointer' }}
            >
              <div className={styles.cardHeader}>
                <span className={styles.childCode}>{child.child_code}</span>
                <span className={`${styles.statusBadge} ${getStatusClass(child.legal_status)}`}>
                  {child.legal_status}
                </span>
              </div>
              <div className={styles.cardBody}>
                <h3 className={styles.childName}>{child.name}</h3>
                <div className={styles.detailsGrid}>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Age</span>
                    <span className={styles.detailValue}>
                      {child.estimated_age ? `${child.estimated_age} yrs` : 'N/A'}
                    </span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Gender</span>
                    <span className={styles.detailValue}>{child.gender || 'N/A'}</span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Admission</span>
                    <span className={styles.detailValue}>
                      {child.admission_date 
                        ? new Date(child.admission_date).toLocaleDateString('en-GB') 
                        : 'N/A'}
                    </span>
                  </div>
                  <div className={styles.detailItem}>
                    <span className={styles.detailLabel}>Location</span>
                    <span className={styles.detailValue}>{child.district || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {isRegModalOpen && (
        <ChildRegistrationForm 
          token={token} 
          onClose={() => setIsRegModalOpen(false)} 
          onChildAdded={(newChild) => {
            setChildren(prev => [newChild, ...prev]);
            setIsRegModalOpen(false);
          }} 
        />
      )}
    </div>
  );
};

export default Children;
