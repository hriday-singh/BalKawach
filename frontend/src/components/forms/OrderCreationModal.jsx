import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import axios from 'axios';
import { X, FileText } from 'lucide-react';
import CustomSelect from '../ui/CustomSelect';

export default function OrderCreationModal({ hearing, token, onClose, onOrderCreated }) {
  const [formData, setFormData] = useState({
    child_id: hearing?.child_id || '',
    hearing_id: hearing?.id || '',
    order_type: 'interim_custody',
    district: hearing?.district || 'Hyderabad',
    order_body: '',
    findings: '',
    transcript: hearing?.transcript_edited || hearing?.transcript_raw || ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const orderTypeOptions = [
    { label: 'Placement Order', value: 'placement' },
    { label: 'Inquiry Extension', value: 'inquiry_extension' },
    { label: 'Restoration Order', value: 'restoration' },
    { label: 'LFA Declaration', value: 'lfa_declaration' },
    { label: 'Foster Care Order', value: 'foster_care' },
    { label: 'Repatriation Order', value: 'repatriation' },
    { label: 'Other', value: 'other' }
  ];

  const getOrderTemplate = (type) => {
    const today = new Date().toLocaleDateString();
    switch (type) {
      case 'placement': return `ORDER FOR PLACEMENT\n\nDate: ${today}\nThe CWC hereby orders the placement of the child (ID: ${hearing?.child_id || ''}) at the designated Child Care Institution. The CCI is directed to provide necessary care and submit a report within 30 days.`;
      case 'inquiry_extension': return `ORDER FOR EXTENSION OF INQUIRY\n\nDate: ${today}\nThe CWC extends the inquiry period for the child (ID: ${hearing?.child_id || ''}) by an additional 30 days to allow for the completion of family tracing and social investigation.`;
      case 'restoration': return `ORDER FOR RESTORATION\n\nDate: ${today}\nAfter satisfactory home study and verification, the CWC orders the restoration of the child (ID: ${hearing?.child_id || ''}) to their biological family/guardian.`;
      case 'lfa_declaration': return `DECLARATION OF LEGALLY FREE FOR ADOPTION\n\nDate: ${today}\nHaving completed the inquiry under Section 36 of the JJ Act and finding no family, the CWC declares the child (ID: ${hearing?.child_id || ''}) Legally Free for Adoption (LFA).`;
      case 'foster_care': return `ORDER FOR FOSTER CARE PLACEMENT\n\nDate: ${today}\nThe CWC orders the placement of the child (ID: ${hearing?.child_id || ''}) into foster care. The DCPU shall monitor the placement and submit periodic reports.`;
      case 'repatriation': return `ORDER FOR REPATRIATION\n\nDate: ${today}\nThe CWC orders the repatriation of the child (ID: ${hearing?.child_id || ''}) to their home district/state, coordinating with the respective CWC and DCPU.`;
      default: return '';
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => {
      const updated = { ...prev, [name]: value };
      if (name === 'order_type') {
        updated.order_body = getOrderTemplate(value);
      }
      return updated;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      await axios.post('/api/orders', formData, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      onOrderCreated();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create order');
    } finally {
      setSubmitting(false);
    }
  };

  const modal = (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.8)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '1rem'
    }}>
      <div style={{
        background: 'var(--surface)', width: '100%', maxWidth: '600px',
        borderRadius: '12px', border: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column', maxHeight: '90vh'
      }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={20} /> Draft Order
          </h2>
          <button onClick={onClose} style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>
        
        <div style={{ padding: '1.5rem', overflowY: 'auto' }}>
          {error && <div style={{ color: 'var(--red)', marginBottom: '1rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '6px' }}>{error}</div>}
          
          <form id="order-form" onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            
            {/* Hidden Inputs for IDs */}
            <input type="hidden" name="child_id" value={formData.child_id} />
            <input type="hidden" name="hearing_id" value={formData.hearing_id} />

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Order Type</label>
              <CustomSelect 
                name="order_type" 
                value={formData.order_type} 
                onChange={handleChange} 
                options={orderTypeOptions}
              />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Findings (Summary of facts)</label>
              <textarea name="findings" value={formData.findings} onChange={handleChange} rows={3} required
                style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'inherit', resize: 'vertical' }} 
              />
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Order Body (Directives)</label>
              <textarea name="order_body" value={formData.order_body} onChange={handleChange} rows={5} required
                style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', fontFamily: 'inherit', resize: 'vertical' }} 
              />
            </div>

          </form>
        </div>
        
        <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
          <button type="button" onClick={onClose} style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>Cancel</button>
          <button type="submit" form="order-form" disabled={submitting} style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
            {submitting ? 'Saving...' : 'Create Draft Order'}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
