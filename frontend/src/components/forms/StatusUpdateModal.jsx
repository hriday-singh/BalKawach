import React, { useState } from 'react';
import { X } from 'lucide-react';
import axios from 'axios';

export default function StatusUpdateModal({ child, onClose, onStatusUpdated, token }) {
  const [status, setStatus] = useState(child.legal_status || 'Under Inquiry');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const statusOptions = [
    'Under Inquiry', 'Legally Free for Adoption', 
    'In Adoption Pool', 'Restored to Family', 'Placed in Foster Care', 
    'Placed in Sponsorship', 'Aged Out', 'Under Review'
  ];

  const [confirming, setConfirming] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError('Please provide notes explaining this status change.');
      return;
    }
    setConfirming(true);
  };

  const confirmSubmit = async () => {
    setSubmitting(true);
    setError('');

    try {
      const res = await fetch(`/api/children/${child.id}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ legal_status: status, notes })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to update status.');
      }
      
      onStatusUpdated(status);
    } catch (err) {
      setError(err.message);
      setConfirming(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.8)', zIndex: 1000,
      display: 'flex', alignItems: 'center', justifyContent: 'center'
    }}>
      <div style={{
        background: 'var(--surface)', width: '100%', maxWidth: '400px',
        borderRadius: '12px', border: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column'
      }}>
        <div style={{ padding: '1.25rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem' }}>{confirming ? 'Confirm Update' : 'Update Legal Status'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>
        
        {!confirming ? (
          <form onSubmit={handleSubmit} style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {error && <div style={{ color: 'var(--red)', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '6px' }}>{error}</div>}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>New Status</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }}>
                {statusOptions.map(opt => <option key={opt} value={opt}>{opt}</option>)}
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Notes / Justification <span style={{ color: 'var(--danger, #ef4444)' }}>*</span></label>
              <textarea required value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} placeholder="Why is the status changing?" />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
              <button type="button" onClick={onClose} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>Cancel</button>
              <button type="submit" disabled={submitting} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
                Update Status
              </button>
            </div>
          </form>
        ) : (
          <div style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <p style={{ color: 'var(--text)', margin: 0, lineHeight: '1.5' }}>
              Are you sure you want to change the legal status to <strong>{status}</strong>? This action will be logged in the case history.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
              <button type="button" onClick={() => setConfirming(false)} disabled={submitting} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
                Go Back
              </button>
              <button type="button" onClick={confirmSubmit} disabled={submitting} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
                {submitting ? 'Confirming...' : 'Yes, Confirm'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
