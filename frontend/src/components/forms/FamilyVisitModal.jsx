import React, { useState } from 'react';
import { X } from 'lucide-react';

export default function FamilyVisitModal({ childId, onClose, onVisitLogged, token }) {
  const [formData, setFormData] = useState({
    visit_date: new Date().toISOString().split('T')[0],
    visitor_name: '',
    relationship: '',
    duration_minutes: 60,
    notes: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');

    try {
      const payload = { ...formData };
      payload.duration_minutes = parseInt(payload.duration_minutes, 10);

      const res = await fetch(`/api/children/${childId}/visits`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to log visit.');
      }
      
      onVisitLogged();
    } catch (err) {
      setError(err.message);
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
          <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Log Family Visit</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}>
            <X size={20} />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {error && <div style={{ color: 'var(--red)', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '6px' }}>{error}</div>}
          
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Date</label>
              <input type="date" required name="visit_date" value={formData.visit_date} onChange={handleChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
            </div>
            <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Duration (mins)</label>
              <input type="number" required name="duration_minutes" value={formData.duration_minutes} onChange={handleChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Visitor Name</label>
            <input required name="visitor_name" value={formData.visitor_name} onChange={handleChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Relationship</label>
            <input required name="relationship" value={formData.relationship} onChange={handleChange} placeholder="e.g. Mother, Uncle" style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Notes</label>
            <textarea name="notes" value={formData.notes} onChange={handleChange} rows={2} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '0.5rem' }}>
            <button type="button" onClick={onClose} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>Cancel</button>
            <button type="submit" disabled={submitting} style={{ padding: '0.75rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
              {submitting ? 'Saving...' : 'Log Visit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
