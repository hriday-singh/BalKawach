import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import axios from 'axios';
import CustomSelect from '../ui/CustomSelect';
import CustomDatePicker from '../ui/CustomDatePicker';

export default function ChildRegistrationForm({ onClose, onChildAdded, token }) {
  const [formData, setFormData] = useState({
    name: '',
    date_of_birth: '',
    age: '',
    gender: 'Other',
    admission_date: (() => {
      const d = new Date();
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    })(),
    admission_category: 'other',
    physical_description: '',
    district: 'Hyderabad',
    cci_id: 'none' // Should ideally default from the logged-in user's CCI
  });
  
  const [ccis, setCcis] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchCcis = async () => {
      try {
        const res = await axios.get('/api/ccis', { headers: { Authorization: `Bearer ${token}` } });
        setCcis(res.data.data || res.data || []);
      } catch (err) {
        console.error("Failed to fetch CCIs", err);
      }
    };
    fetchCcis();
  }, [token]);

  useEffect(() => {
    if (formData.date_of_birth) {
      const dob = new Date(formData.date_of_birth);
      if (!isNaN(dob.getTime())) {
        const today = new Date();
        let calculatedAge = today.getFullYear() - dob.getFullYear();
        const m = today.getMonth() - dob.getMonth();
        if (m < 0 || (m === 0 && today.getDate() < dob.getDate())) {
          calculatedAge--;
        }
        setFormData(prev => ({ ...prev, age: calculatedAge >= 0 ? String(calculatedAge) : '' }));
      }
    } else {
      setFormData(prev => ({ ...prev, age: '' }));
    }
  }, [formData.date_of_birth]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    
    // Quick validation: must have dob or age
    if (!formData.date_of_birth && !formData.age) {
      setError('Please provide either Date of Birth or Estimated Age.');
      setSubmitting(false);
      return;
    }

    if (formData.cci_id === 'none') {
      setError('Please select an Assigned CCI.');
      setSubmitting(false);
      return;
    }

    try {
      // Clean up empty strings for numbers
      const payload = { ...formData };
      if (!payload.date_of_birth) payload.date_of_birth = null;
      
      if (payload.age !== '' && payload.age !== null && payload.age !== undefined) {
        payload.age = parseInt(payload.age, 10);
      } else {
        payload.age = null;
      }

      const res = await fetch('/api/children', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to register child.');
      }
      
      const newChild = await res.json();
      onChildAdded(newChild);
      
    } catch (err) {
      setError(err.message);
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
        background: 'var(--surface)',
        width: '100%',
        maxWidth: '600px',
        borderRadius: '12px',
        border: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        maxHeight: '90vh'
      }}>
        <div style={{ 
          padding: '1.5rem', 
          borderBottom: '1px solid var(--border)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center' 
        }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Register New Child</h2>
          <button 
            onClick={onClose} 
            style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>
        
        <div style={{ padding: '1.5rem', overflowY: 'auto', scrollbarGutter: 'stable' }}>
          {error && <div style={{ color: 'var(--red)', marginBottom: '1rem', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '6px' }}>{error}</div>}
          
          <form id="child-reg-form" onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Full Name <span style={{ color: 'var(--danger, #ef4444)' }}>*</span></label>
              <input required name="name" value={formData.name} onChange={handleChange} 
                style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} 
                placeholder="Child's full name"
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Date of Birth</label>
                <CustomDatePicker name="date_of_birth" value={formData.date_of_birth} onChange={handleChange} />
              </div>
              <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Estimated Age</label>
                <input type="number" name="age" value={formData.age} onChange={handleChange} placeholder="If DOB unknown"
                  disabled={!!formData.date_of_birth}
                  style={{ 
                    padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', 
                    background: 'var(--bg)', color: 'var(--text)', 
                    opacity: formData.date_of_birth ? 0.6 : 1, 
                    cursor: formData.date_of_birth ? 'not-allowed' : 'auto' 
                  }} 
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Gender</label>
                <CustomSelect 
                  name="gender" 
                  value={formData.gender} 
                  onChange={handleChange} 
                  options={[
                    { value: 'Male', label: 'Male' },
                    { value: 'Female', label: 'Female' },
                    { value: 'Other', label: 'Other' }
                  ]} 
                />
              </div>
              <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Admission Date</label>
                <CustomDatePicker name="admission_date" value={formData.admission_date} onChange={handleChange} />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Admission Category</label>
                <CustomSelect 
                  name="admission_category" 
                  value={formData.admission_category} 
                  onChange={handleChange} 
                  options={[
                    { value: 'abandoned', label: 'Abandoned' },
                    { value: 'orphaned', label: 'Orphaned' },
                    { value: 'surrendered', label: 'Surrendered' },
                    { value: 'missing', label: 'Missing' },
                    { value: 'abused', label: 'Abused / Rescued' },
                    { value: 'other', label: 'Other' }
                  ]} 
                />
              </div>
              <div style={{ flex: '1 1 200px', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>
                  Assigned CCI <span style={{ color: 'var(--danger, #ef4444)' }}>*</span>
                </label>
                <CustomSelect 
                  name="cci_id" 
                  value={formData.cci_id} 
                  onChange={handleChange} 
                  options={[
                    { value: 'none', label: 'Select a CCI...' },
                    ...ccis.map(cci => ({ value: cci.id, label: `${cci.name} (${cci.district})` }))
                  ]} 
                />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 500 }}>Physical Description</label>
              <textarea name="physical_description" value={formData.physical_description} onChange={handleChange} rows={3}
                style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)', resize: 'vertical' }} 
                placeholder="Identifying marks, physical condition at admission, etc."
              />
            </div>
            
          </form>
        </div>
        
        <div style={{ 
          padding: '1.5rem', 
          borderTop: '1px solid var(--border)', 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '1rem' 
        }}>
          <button 
            type="button" 
            onClick={onClose} 
            style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer', fontWeight: 500 }}
          >
            Cancel
          </button>
          <button 
            type="submit" 
            form="child-reg-form" 
            disabled={submitting} 
            style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}
          >
            {submitting ? 'Registering...' : 'Register Child'}
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
