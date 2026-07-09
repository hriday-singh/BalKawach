import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Home, Users, CheckSquare } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import styles from './CCIs.module.css';
import CustomDatePicker from '../components/ui/CustomDatePicker';

import { formatRole } from '../utils/formatters';

export default function CCIs() {
  const [ccis, setCcis] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { token, user } = useAuth();
  const navigate = useNavigate();
  
  // Add CCI Modal
  const [isAddCciOpen, setIsAddCciOpen] = useState(false);
  const [newCciData, setNewCciData] = useState({
    name: '', district: 'Hyderabad', capacity: '', contact_person: '', contact_phone: ''
  });

  // Inspection Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedCci, setSelectedCci] = useState(null);
  
  // Details Modal
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [selectedCciDetails, setSelectedCciDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  const [inspectionData, setInspectionData] = useState({
    visit_date: new Date().toISOString().split('T')[0],
    findings: '',
    recommendations: ''
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchCCIs = async () => {
    try {
      setLoading(true);
      const res = await axios.get('/api/ccis', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setCcis(res.data.data || res.data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch CCIs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCCIs();
  }, [token]);

  const handleAddCciSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post('/api/ccis', { ...newCciData, capacity: parseInt(newCciData.capacity) || 0 }, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setIsAddCciOpen(false);
      setNewCciData({ name: '', district: 'Hyderabad', capacity: '', contact_person: '', contact_phone: '' });
      fetchCCIs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to add CCI');
    } finally {
      setSubmitting(false);
    }
  };

  const handleInspectionSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`/api/ccis/${selectedCci.id}/inspections`, inspectionData, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setIsModalOpen(false);
      setInspectionData({ visit_date: new Date().toISOString().split('T')[0], findings: '', recommendations: '' });
      fetchCCIs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to log inspection');
    } finally {
      setSubmitting(false);
    }
  };

  const handleViewDetails = async (cci) => {
    setSelectedCci(cci);
    setIsDetailsModalOpen(true);
    setLoadingDetails(true);
    try {
      const [detailsRes, inspectionsRes] = await Promise.all([
        axios.get(`/api/ccis/${cci.id}/details`, { headers: { 'Authorization': `Bearer ${token}` } }),
        axios.get(`/api/ccis/${cci.id}/inspections`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      const data = detailsRes.data;
      data.inspections = inspectionsRes.data;
      setSelectedCciDetails(data);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to fetch CCI details');
    } finally {
      setLoadingDetails(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner}></div>
        <p>Loading CCIs...</p>
      </div>
    );
  }
  if (error) return <div style={{ padding: '2rem', color: 'var(--red)' }}>Error: {error}</div>;

  return (
    <div className="page active" style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2rem' }}>
        <div>
          <h2 style={{ fontSize: '1.8rem', fontWeight: 600, margin: 0 }}>Child Care Institutions (CCIs)</h2>
          <p style={{ color: 'var(--muted)', marginTop: '0.5rem' }}>Monitor capacity and log inspections</p>
        </div>
        {user?.role === 'dcpu_officer' && (
          <button 
            onClick={() => setIsAddCciOpen(true)}
            style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer' }}
          >
            + Register New CCI
          </button>
        )}
      </div>

      <div className={styles.container}>
        {ccis.length === 0 ? (
          <div style={{ width: '100%', textAlign: 'center', padding: '4rem 2rem', background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)' }}>
            <Home size={32} style={{ color: 'var(--muted)', marginBottom: '1rem' }} />
            <h3 style={{ margin: '0 0 0.5rem 0' }}>No CCIs found</h3>
            <p style={{ color: 'var(--muted)' }}>
              There are currently no Child Care Institutions registered in your jurisdiction.
            </p>
          </div>
        ) : (
          <>
            <div className={styles.mobileCards}>
              {ccis.map(cci => {
                const occupancyRate = cci.capacity > 0 ? (cci.current_occupancy / cci.capacity) * 100 : 0;
                let occupancyColor = 'var(--green)';
                if (occupancyRate > 90) occupancyColor = 'var(--red)';
                else if (occupancyRate > 75) occupancyColor = 'var(--amber)';

                return (
                  <div key={cci.id} style={{ 
                    background: 'var(--surface)', padding: '1.5rem', borderRadius: '12px', 
                    border: '1px solid var(--border)', display: 'flex', flexDirection: 'column'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                      <div>
                        <h3 style={{ margin: '0 0 0.25rem 0', fontSize: '1.2rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Home size={18} /> {cci.name}
                        </h3>
                        <span style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>{cci.district}</span>
                      </div>
                    </div>
                    
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                        <span style={{ color: 'var(--muted)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <Users size={16} /> Occupancy
                        </span>
                        <span style={{ fontWeight: 600 }}>{cci.current_occupancy} / {cci.capacity}</span>
                      </div>
                      <div className={styles.occupancyBar}>
                        <div className={styles.occupancyFill} style={{ width: `${Math.min(occupancyRate, 100)}%`, background: occupancyColor }}></div>
                      </div>
                      
                      <div style={{ marginTop: '1.5rem', fontSize: '0.9rem' }}>
                        <p style={{ margin: '0 0 0.25rem 0', color: 'var(--muted)' }}>Contact Person</p>
                        <p style={{ margin: 0, fontWeight: 500 }}>{cci.contact_person || 'N/A'} {cci.contact_phone ? `(${cci.contact_phone})` : ''}</p>
                      </div>
                      
                      <div style={{ marginTop: '1rem', fontSize: '0.9rem' }}>
                        <p style={{ margin: '0 0 0.25rem 0', color: 'var(--muted)' }}>Last Inspection</p>
                        <p style={{ margin: 0, fontWeight: 500 }}>
                          {cci.last_inspection_date ? new Date(cci.last_inspection_date).toLocaleDateString() : 'Never'}
                        </p>
                      </div>
                    </div>
                    
                    <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)', display: 'flex', gap: '0.5rem', flexDirection: 'column' }}>
                      <button 
                        onClick={() => handleViewDetails(cci)}
                        className={styles.actionBtn}
                        style={{ justifyContent: 'center' }}
                      >
                        <Users size={16} /> View Details
                      </button>
                      {user?.role === 'dcpu_officer' && (
                        <button 
                          onClick={() => { setSelectedCci(cci); setIsModalOpen(true); }}
                          className={`${styles.actionBtn} ${styles.primaryBtn}`}
                          style={{ justifyContent: 'center' }}
                        >
                          <CheckSquare size={16} /> Log Inspection
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className={styles.desktopTable}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Institution Name</th>
                    <th>District</th>
                    <th>Occupancy</th>
                    <th>Contact</th>
                    <th>Last Inspection</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {ccis.map(cci => {
                    const occupancyRate = cci.capacity > 0 ? (cci.current_occupancy / cci.capacity) * 100 : 0;
                    let occupancyColor = 'var(--green)';
                    if (occupancyRate > 90) occupancyColor = 'var(--red)';
                    else if (occupancyRate > 75) occupancyColor = 'var(--amber)';

                    return (
                      <tr key={`tbl-${cci.id}`}>
                        <td style={{ fontWeight: 600, color: 'var(--text)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <Home size={16} style={{ color: 'var(--muted)' }} /> {cci.name}
                          </div>
                        </td>
                        <td>{cci.district}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span style={{ minWidth: '40px', fontWeight: 500 }}>{cci.current_occupancy}/{cci.capacity}</span>
                            <div className={styles.occupancyBar} style={{ width: '80px', marginTop: 0 }}>
                              <div className={styles.occupancyFill} style={{ width: `${Math.min(occupancyRate, 100)}%`, background: occupancyColor }}></div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div>{cci.contact_person || 'N/A'}</div>
                          <div style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>{cci.contact_phone}</div>
                        </td>
                        <td>{cci.last_inspection_date ? new Date(cci.last_inspection_date).toLocaleDateString() : 'Never'}</td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                            <button onClick={() => handleViewDetails(cci)} className={styles.actionBtn}>
                              View
                            </button>
                            {user?.role === 'dcpu_officer' && (
                              <button onClick={() => { setSelectedCci(cci); setIsModalOpen(true); }} className={`${styles.actionBtn} ${styles.primaryBtn}`}>
                                Inspect
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>

      {isModalOpen && selectedCci && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px'
        }}>
          <div style={{
            background: 'var(--surface)', width: '100%', maxWidth: '500px',
            borderRadius: '12px', border: '1px solid var(--border)', padding: '1.5rem',
            maxHeight: '90vh', overflowY: 'auto'
          }}>
            <h2 style={{ margin: '0 0 1.5rem 0', fontSize: '1.25rem' }}>Log Inspection for {selectedCci.name}</h2>
            <form onSubmit={handleInspectionSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Date of Visit</label>
                <CustomDatePicker 
                  value={inspectionData.visit_date} 
                  onChange={val => setInspectionData({...inspectionData, visit_date: val})} 
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Findings</label>
                <textarea required value={inspectionData.findings} onChange={e => setInspectionData({...inspectionData, findings: e.target.value})} rows={3}
                  style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Recommendations</label>
                <textarea value={inspectionData.recommendations} onChange={e => setInspectionData({...inspectionData, recommendations: e.target.value})} rows={2}
                  style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>Cancel</button>
                <button type="submit" disabled={submitting} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
                  {submitting ? 'Saving...' : 'Log Inspection'}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {isDetailsModalOpen && selectedCci && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '16px'
        }}>
          <div style={{
            background: 'var(--surface)', width: '100%', maxWidth: '800px',
            maxHeight: '90vh', overflowY: 'auto',
            borderRadius: '12px', border: '1px solid var(--border)', padding: '1.5rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{selectedCci.name} Details</h2>
              <button 
                onClick={() => setIsDetailsModalOpen(false)}
                style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '1.5rem' }}
              >
                &times;
              </button>
            </div>
            
            {loadingDetails ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>Loading details...</div>
            ) : selectedCciDetails ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', background: 'var(--bg)', padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border)' }}>

                  <div><strong style={{ color: 'var(--muted)', display: 'block' }}>District:</strong> {selectedCciDetails.district || selectedCci.district}</div>
                  <div><strong style={{ color: 'var(--muted)', display: 'block' }}>Capacity:</strong> {selectedCciDetails.capacity || selectedCci.capacity}</div>
                  <div><strong style={{ color: 'var(--muted)', display: 'block' }}>Occupancy:</strong> {selectedCciDetails.current_occupancy || selectedCci.current_occupancy}</div>
                </div>

                <div>
                  <h3 style={{ fontSize: '1.1rem', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Users size={18} /> Staff Members</h3>
                  {selectedCciDetails.staff && selectedCciDetails.staff.length > 0 ? (
                    <div style={{ background: 'var(--bg)', borderRadius: '8px', border: '1px solid var(--border)', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                        <thead>
                          <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid var(--border)' }}>
                            <th style={{ padding: '0.75rem 1rem', color: 'var(--muted)', fontWeight: 500 }}>Name</th>
                            <th style={{ padding: '0.75rem 1rem', color: 'var(--muted)', fontWeight: 500 }}>Role</th>
                            <th style={{ padding: '0.75rem 1rem', color: 'var(--muted)', fontWeight: 500 }}>Phone</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedCciDetails.staff.map((staff, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                              <td style={{ padding: '0.75rem 1rem' }}>{staff.name}</td>
                              <td style={{ padding: '0.75rem 1rem' }}>
                                <span style={{
                                  padding: '0.25rem 0.75rem',
                                  borderRadius: '99px',
                                  background: 'var(--accent-bg)',
                                  color: 'var(--accent)',
                                  fontSize: '0.85rem',
                                  fontWeight: 600
                                }}>
                                  {formatRole(staff.role)}
                                </span>
                              </td>
                              <td style={{ padding: '0.75rem 1rem' }}>{staff.phone || 'N/A'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ color: 'var(--muted)', fontSize: '0.9rem', padding: '1rem', background: 'var(--bg)', borderRadius: '8px', border: '1px dashed var(--border)' }}>No staff members listed.</div>
                  )}
                </div>

                <div>
                  <h3 style={{ fontSize: '1.1rem', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Users size={18} /> Children</h3>
                  {selectedCciDetails.children && selectedCciDetails.children.length > 0 ? (
                    <div style={{ background: 'var(--bg)', borderRadius: '8px', border: '1px solid var(--border)', overflow: 'hidden' }}>
                      <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
                        <thead>
                          <tr style={{ background: 'rgba(255,255,255,0.05)', borderBottom: '1px solid var(--border)' }}>
                            <th style={{ padding: '0.75rem 1rem', color: 'var(--muted)', fontWeight: 500 }}>Name</th>
                            <th style={{ padding: '0.75rem 1rem', color: 'var(--muted)', fontWeight: 500 }}>Age</th>
                            <th style={{ padding: '0.75rem 1rem', color: 'var(--muted)', fontWeight: 500 }}>Gender</th>
                          </tr>
                        </thead>
                        <tbody>
                          {selectedCciDetails.children.map((child, i) => (
                            <tr 
                              key={i} 
                              style={{ borderBottom: '1px solid var(--border)', cursor: 'pointer' }}
                              onClick={() => navigate(`/children?id=${child.id}`)}
                              className={styles.childRow}
                            >
                              <td style={{ padding: '0.75rem 1rem', color: 'var(--accent-light)' }}>{child.name}</td>
                              <td style={{ padding: '0.75rem 1rem' }}>{child.age || 'N/A'}</td>
                              <td style={{ padding: '0.75rem 1rem' }}>{child.gender || 'N/A'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ color: 'var(--muted)', fontSize: '0.9rem', padding: '1rem', background: 'var(--bg)', borderRadius: '8px', border: '1px dashed var(--border)' }}>No children listed.</div>
                  )}
                </div>

                <div>
                  <h3 style={{ fontSize: '1.1rem', margin: '0 0 1rem 0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}><CheckSquare size={18} /> Past Inspections</h3>
                  <div className={styles.timelineContainer}>
                    {selectedCciDetails.inspections && selectedCciDetails.inspections.length > 0 ? (
                      <div className={styles.timeline}>
                        {selectedCciDetails.inspections.map((insp, i) => (
                          <div key={insp.id} className={styles.timelineItem}>
                            <div className={styles.timelineIconWrapper}>
                              <div className={`${styles.timelineIcon} ${styles.iconTeal}`}></div>
                              {i !== selectedCciDetails.inspections.length - 1 && <div className={styles.timelineLine}></div>}
                            </div>
                            <div className={styles.timelineContent}>
                              <div className={styles.timelineDate}>{new Date(insp.visit_date).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}</div>
                              <h4 className={styles.timelineEventType}>Inspection</h4>
                              {insp.findings && <p className={styles.timelineDesc}><strong>Findings:</strong> {insp.findings}</p>}
                              {insp.recommendations && <p className={styles.timelineDesc}><strong>Recommendations:</strong> {insp.recommendations}</p>}
                              <p className={styles.timelineAuthor}>By: {insp.officer_name || 'Unknown Officer'}{insp.officer_district ? `, ${insp.officer_district}` : ''}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className={styles.noHistory} style={{ padding: '1rem', background: 'var(--bg)', borderRadius: '8px', border: '1px dashed var(--border)' }}>No past inspections recorded.</div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--muted)' }}>Could not load details.</div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
              <button 
                onClick={() => setIsDetailsModalOpen(false)} 
                style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer', fontWeight: 500 }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {isAddCciOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', zIndex: 1000,
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px'
        }}>
          <div style={{
            background: 'var(--surface)', width: '100%', maxWidth: '500px',
            borderRadius: '12px', border: '1px solid var(--border)', padding: '1.5rem',
            maxHeight: '90vh', overflowY: 'auto'
          }}>
            <h2 style={{ margin: '0 0 1.5rem 0', fontSize: '1.25rem' }}>Register New CCI</h2>
            <form onSubmit={handleAddCciSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Institution Name <span style={{ color: 'var(--danger, #ef4444)' }}>*</span></label>
                <input type="text" required value={newCciData.name} onChange={e => setNewCciData({...newCciData, name: e.target.value})} 
                  style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                />
              </div>

              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Capacity <span style={{ color: 'var(--danger, #ef4444)' }}>*</span></label>
                  <input type="number" required value={newCciData.capacity} onChange={e => setNewCciData({...newCciData, capacity: e.target.value})} 
                    style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                  />
                </div>
                <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>District</label>
                  <input type="text" required value={newCciData.district} onChange={e => setNewCciData({...newCciData, district: e.target.value})} 
                    style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Contact Person</label>
                  <input type="text" value={newCciData.contact_person} onChange={e => setNewCciData({...newCciData, contact_person: e.target.value})} 
                    style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                  />
                </div>
                <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Contact Phone</label>
                  <input type="text" value={newCciData.contact_phone} onChange={e => setNewCciData({...newCciData, contact_phone: e.target.value})} 
                    style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
                <button type="button" onClick={() => setIsAddCciOpen(false)} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>Cancel</button>
                <button type="submit" disabled={submitting} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
                  {submitting ? 'Registering...' : 'Register CCI'}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}
    </div>
  );
}
