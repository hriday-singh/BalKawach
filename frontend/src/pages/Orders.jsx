import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FileText, CheckCircle, Clock, Loader2, Plus, Edit2, Search } from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import styles from './Orders.module.css';
import CustomSelect from '../components/ui/CustomSelect';

const ORDER_TYPES = [
  'placement',
  'inquiry_extension',
  'restoration',
  'lfa_declaration',
  'foster_care',
  'repatriation',
  'other'
];

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [childrenList, setChildrenList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  
  const [formData, setFormData] = useState({
    child_id: '',
    order_type: 'placement',
    findings: '',
    order_body: ''
  });
  const [formSaving, setFormSaving] = useState(false);

  const { token, user } = useAuth();
  
  const canEdit = user?.role === 'cwc_member' || user?.role === 'cwc_chairperson';

  const formatType = (type) => {
    if (!type) return '';
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getStatusStyle = (status) => {
    switch (status) {
      case 'approved': return { color: 'var(--green)', bg: 'rgba(34,197,94,0.1)' };
      case 'draft': return { color: 'var(--muted)', bg: 'var(--surface)' };
      case 'pending_approval': return { color: 'var(--amber)', bg: 'rgba(245,158,11,0.1)' };
      default: return { color: 'var(--text)', bg: 'var(--surface)' };
    }
  };

  const fetchOrdersAndChildren = async () => {
    try {
      setLoading(true);
      const [ordersRes, childrenRes] = await Promise.all([
        axios.get('/api/orders', { headers: { 'Authorization': `Bearer ${token}` } }),
        axios.get('/api/children', { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      setOrders(ordersRes.data.data || ordersRes.data || []);
      setChildrenList(childrenRes.data.data || childrenRes.data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrdersAndChildren();
  }, [token]);

  const handleApprove = async (orderId) => {
    try {
      await axios.put(`/api/orders/${orderId}/approve`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchOrdersAndChildren();
      if (selectedOrder && selectedOrder.id === orderId) {
        setIsViewModalOpen(false);
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to approve order');
    }
  };

  const handleGeneratePdf = (orderId) => {
    window.open(`/print/order/${orderId}`, '_blank');
  };

  const openCreateModal = () => {
    setFormData({
      child_id: '',
      order_type: 'placement',
      findings: '',
      order_body: ''
    });
    setIsEditMode(false);
    setIsFormModalOpen(true);
  };

  const openEditModal = (order) => {
    setFormData({
      child_id: order.child_id || '',
      order_type: order.order_type || 'other',
      findings: order.findings || '',
      order_body: order.order_body || ''
    });
    setSelectedOrder(order);
    setIsEditMode(true);
    setIsFormModalOpen(true);
    setIsViewModalOpen(false);
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setFormSaving(true);
    try {
      if (isEditMode && selectedOrder) {
        await axios.put(`/api/orders/${selectedOrder.id}`, formData, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } else {
        await axios.post('/api/orders', formData, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
      setIsFormModalOpen(false);
      fetchOrdersAndChildren();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to save order');
    } finally {
      setFormSaving(false);
    }
  };

  const filteredOrders = orders.filter(order => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const childName = (order.child?.name || '').toLowerCase();
    const childId = (order.child_id || '').toLowerCase();
    const childCode = (order.child?.child_code || '').toLowerCase();
    const orderNumber = (order.order_number || '').toLowerCase();
    const type = formatType(order.order_type).toLowerCase();
    return childName.includes(q) || childId.includes(q) || childCode.includes(q) || orderNumber.includes(q) || type.includes(q);
  });

  if (loading) return (
    <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', color: 'var(--muted)' }}>
      <Loader2 size={32} style={{ animation: 'spin 1s linear infinite' }} />
      <p>Loading orders...</p>
    </div>
  );
  if (error) return <div style={{ padding: '2rem', color: 'var(--red)' }}>Error: {error}</div>;

  return (
    <div className={`page active ${styles.pageContainer}`}>
      <div className={styles.headerContainer}>
        <div className={styles.headerLeft}>
          <h2 style={{ fontSize: '1.8rem', fontWeight: 600, margin: 0 }}>CWC Orders</h2>
          <p>Review, draft, and approve legal orders</p>
        </div>
        {canEdit && (
          <button onClick={openCreateModal} className={styles.createBtn}>
            <Plus size={18} /> New Order
          </button>
        )}
      </div>

      <div style={{ marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
          <Search size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--muted)' }} />
          <input 
            type="text" 
            placeholder="Search by order number, child name, or type..." 
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setSearchParams(e.target.value ? { search: e.target.value } : {});
            }}
            style={{ width: '100%', padding: '0.75rem 1rem 0.75rem 2.5rem', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '0.95rem' }}
          />
        </div>
      </div>

      {filteredOrders.length === 0 ? (
        <div style={{ width: '100%', textAlign: 'center', padding: '4rem 2rem', background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <FileText size={32} style={{ color: 'var(--muted)', marginBottom: '1rem' }} />
          <h3 style={{ margin: '0 0 0.5rem 0' }}>No orders found</h3>
          <p style={{ color: 'var(--muted)' }}>
            {searchQuery ? 'No orders match your current search.' : 'There are currently no orders requiring your attention.'}
          </p>
        </div>
      ) : (
        <div className={styles.container}>
          {/* Mobile Cards */}
          <div className={styles.mobileCards}>
            {filteredOrders.map(order => {
              const statusStyle = getStatusStyle(order.status);
              return (
                <div key={order.id} style={{ 
                  display: 'flex', flexDirection: 'column', gap: '1rem',
                  background: 'var(--surface)', padding: '1.5rem', borderRadius: '12px', border: '1px solid var(--border)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{order.order_number}</span>
                    <span style={{ 
                      fontSize: '0.8rem', fontWeight: 600, padding: '0.25rem 0.75rem', borderRadius: '999px',
                      color: statusStyle.color, backgroundColor: statusStyle.bg, border: `1px solid ${statusStyle.color}`
                    }}>
                      {order.status.replace('_', ' ').toUpperCase()}
                    </span>
                  </div>
                  
                  <div style={{ color: 'var(--muted)', fontSize: '0.9rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Child:</span>
                      <span style={{ fontWeight: 500, color: 'var(--text)' }}>{order.child?.name || order.child_id}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Type:</span>
                      <span style={{ fontWeight: 500, color: 'var(--text)' }}>{formatType(order.order_type)}</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Created:</span>
                      <span style={{ fontWeight: 500, color: 'var(--text)' }}>{new Date(order.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)', flexWrap: 'wrap' }}>
                    <button 
                      onClick={() => { setSelectedOrder(order); setIsViewModalOpen(true); }}
                      className={styles.actionBtn} style={{ flex: 1, justifyContent: 'center' }}
                    >
                      View Details
                    </button>
                    {canEdit && (order.status === 'draft' || order.status === 'pending_approval') && (
                      <button 
                        onClick={() => openEditModal(order)}
                        className={styles.actionBtn} style={{ flex: 1, justifyContent: 'center' }}
                      >
                        <Edit2 size={16} /> Edit
                      </button>
                    )}
                    <button 
                      onClick={() => handleGeneratePdf(order.id)}
                      className={styles.actionBtn} style={{ flex: 1, justifyContent: 'center', borderColor: 'var(--accent)', color: 'var(--accent)' }}
                    >
                      <FileText size={16} /> {order.status === 'approved' ? 'Print PDF' : 'Preview'}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Desktop Table */}
          <div className={styles.desktopTable}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Order #</th>
                  <th>Child</th>
                  <th>Type</th>
                  <th>Date</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'center' }}>View</th>
                  <th style={{ textAlign: 'center' }}>Edit</th>
                  <th style={{ textAlign: 'center' }}>Document</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map(order => {
                  const statusStyle = getStatusStyle(order.status);
                  const isDraftOrPending = order.status === 'draft' || order.status === 'pending_approval';
                  return (
                    <tr key={`tbl-${order.id}`}>
                      <td style={{ fontWeight: 600, color: 'var(--text)' }}>{order.order_number}</td>
                      <td>{order.child?.name || order.child_id}</td>
                      <td>{formatType(order.order_type)}</td>
                      <td>{new Date(order.created_at).toLocaleDateString()}</td>
                      <td>
                        <span style={{ 
                          fontSize: '0.8rem', fontWeight: 600, padding: '0.25rem 0.75rem', borderRadius: '999px',
                          color: statusStyle.color, backgroundColor: statusStyle.bg, border: `1px solid ${statusStyle.color}`
                        }}>
                          {order.status.replace('_', ' ').toUpperCase()}
                        </span>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button onClick={() => { setSelectedOrder(order); setIsViewModalOpen(true); }} className={styles.actionBtn}>
                          View
                        </button>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button 
                          onClick={() => openEditModal(order)} 
                          className={styles.actionBtn}
                          disabled={!canEdit || !isDraftOrPending}
                          style={{ opacity: (!canEdit || !isDraftOrPending) ? 0.5 : 1, cursor: (!canEdit || !isDraftOrPending) ? 'not-allowed' : 'pointer' }}
                        >
                          Edit
                        </button>
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button onClick={() => handleGeneratePdf(order.id)} className={styles.actionBtn} style={{ borderColor: 'var(--accent)', color: 'var(--accent)', padding: '0.4rem 0.8rem' }}>
                          <FileText size={14} style={{ marginRight: '4px' }} /> {order.status === 'approved' ? 'Print' : 'Preview'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* View Details Modal */}
      {isViewModalOpen && selectedOrder && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.4rem' }}>Order Details: {selectedOrder.order_number}</h2>
              <button onClick={() => setIsViewModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '1.5rem' }}>
                &times;
              </button>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', background: 'var(--bg)', padding: '1.5rem', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '1.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.95rem' }}>
                <div><strong style={{ color: 'var(--muted)' }}>Child:</strong> {selectedOrder.child?.name || selectedOrder.child_id}</div>
                <div><strong style={{ color: 'var(--muted)' }}>Type:</strong> {formatType(selectedOrder.order_type)}</div>
                <div><strong style={{ color: 'var(--muted)' }}>Status:</strong> {selectedOrder.status.replace('_', ' ').toUpperCase()}</div>
                <div><strong style={{ color: 'var(--muted)' }}>Created:</strong> {new Date(selectedOrder.created_at).toLocaleDateString()}</div>
                {selectedOrder.updated_by && (
                  <>
                    <div><strong style={{ color: 'var(--muted)' }}>Last Edited By:</strong> {selectedOrder.updated_by}</div>
                    <div><strong style={{ color: 'var(--muted)' }}>Last Edited On:</strong> {new Date(selectedOrder.updated_at).toLocaleDateString()}</div>
                  </>
                )}
              </div>
              
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '0.5rem 0' }} />
              
              <div>
                <strong style={{ color: 'var(--muted)', display: 'block', marginBottom: '0.5rem' }}>Findings:</strong>
                <p style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'var(--text)', lineHeight: 1.6 }}>
                  {selectedOrder.findings || "No findings recorded."}
                </p>
              </div>

              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '0.5rem 0' }} />
              
              <div>
                <strong style={{ color: 'var(--muted)', display: 'block', marginBottom: '0.5rem' }}>Order Directives:</strong>
                <p style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'var(--text)', lineHeight: 1.6 }}>
                  {selectedOrder.order_body || "No directives provided."}
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
              <button onClick={() => setIsViewModalOpen(false)} className={styles.actionBtn}>
                Close
              </button>
              
              {selectedOrder.status !== 'approved' && (
                <button onClick={() => handleGeneratePdf(selectedOrder.id)} className={styles.actionBtn} style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
                  <FileText size={16} /> Preview
                </button>
              )}

              {selectedOrder.status === 'approved' && (
                <button onClick={() => handleGeneratePdf(selectedOrder.id)} className={styles.actionBtn} style={{ borderColor: 'var(--accent)', color: 'var(--accent)' }}>
                  <FileText size={16} /> Print PDF
                </button>
              )}

              {selectedOrder.status === 'pending_approval' && user?.role === 'cwc_chairperson' && (
                <button onClick={() => handleApprove(selectedOrder.id)} className={`${styles.actionBtn} ${styles.primaryBtn}`}>
                  <CheckCircle size={16} /> Approve Order
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Create / Edit Form Modal */}
      {isFormModalOpen && (
        <div className={styles.modalOverlay}>
          <div className={styles.modalContent}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{isEditMode ? 'Edit Order' : 'Create New Order'}</h2>
              <button onClick={() => setIsFormModalOpen(false)} style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '1.5rem' }}>
                &times;
              </button>
            </div>

            <form onSubmit={handleFormSubmit}>
              <div className={styles.formGroup}>
                <label>Select Child</label>
                {isEditMode ? (
                  <input
                    type="text"
                    disabled
                    className={styles.formInput}
                    value={
                      childrenList.find(c => c.id === formData.child_id)
                        ? `${childrenList.find(c => c.id === formData.child_id).name}${childrenList.find(c => c.id === formData.child_id).case_number ? ` (${childrenList.find(c => c.id === formData.child_id).case_number})` : ''}`
                        : formData.child_id
                    }
                  />
                ) : (
                  <CustomSelect
                    name="child_id"
                    value={formData.child_id}
                    onChange={(e) => setFormData({...formData, child_id: e.target.value})}
                    placeholder="Select a child..."
                    options={childrenList.map(child => ({
                      value: child.id,
                      label: `${child.name}${child.case_number ? ` (${child.case_number})` : ''}`
                    }))}
                  />
                )}
              </div>

              <div className={styles.formGroup}>
                <label>Order Type</label>
                <CustomSelect
                  name="order_type"
                  value={formData.order_type}
                  onChange={(e) => setFormData({...formData, order_type: e.target.value})}
                  options={ORDER_TYPES.map(type => ({ value: type, label: formatType(type) }))}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Findings</label>
                <textarea 
                  className={styles.formTextarea} 
                  placeholder="Record the observations and findings..."
                  value={formData.findings}
                  onChange={(e) => setFormData({...formData, findings: e.target.value})}
                />
              </div>

              <div className={styles.formGroup}>
                <label>Directives (Order Body)</label>
                <textarea 
                  className={styles.formTextarea} 
                  placeholder="Record the specific directives and directions..."
                  required
                  value={formData.order_body}
                  onChange={(e) => setFormData({...formData, order_body: e.target.value})}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '2rem' }}>
                <button type="button" onClick={() => setIsFormModalOpen(false)} className={styles.actionBtn}>
                  Cancel
                </button>
                <button type="submit" disabled={formSaving} className={`${styles.actionBtn} ${styles.primaryBtn}`}>
                  {formSaving ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> : (isEditMode ? 'Save Changes' : 'Create Draft')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
