import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import styles from './Users.module.css';

import { formatRole } from '../utils/formatters';
import { Users as UsersIcon } from 'lucide-react';

export default function Users() {
  const { token, user } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    full_name: '',
    role: 'cci_staff',
    district: 'Hyderabad',
    location: '',
    email: '',
    phone: '',
    is_active: true
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch users');
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(formData)
      });
      
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to create user');
      }
      
      setIsModalOpen(false);
      setFormData({
        username: '', password: '', full_name: '', role: 'cci_staff', 
        district: 'Hyderabad', location: '', email: '', phone: '', is_active: true
      });
      fetchUsers();
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div style={{ padding: '2rem', color: 'var(--muted)' }}>Loading users...</div>;
  if (error) return <div style={{ padding: '2rem', color: 'var(--red)' }}>Error: {error}</div>;

  return (
    <div className={styles.pageContainer}>
      <div className={styles.headerContainer}>
        <h1 className={styles.title}>User Management</h1>
        <button 
          onClick={() => setIsModalOpen(true)}
          className={styles.addBtn}
        >
          Add User
        </button>
      </div>
      
      {users.length === 0 ? (
        <div style={{ width: '100%', textAlign: 'center', padding: '4rem 2rem', background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)', marginTop: '2rem' }}>
          <UsersIcon size={32} style={{ color: 'var(--muted)', marginBottom: '1rem' }} />
          <h3 style={{ margin: '0 0 0.5rem 0' }}>No users found</h3>
          <p style={{ color: 'var(--muted)' }}>
            There are currently no users registered in the system.
          </p>
        </div>
      ) : (
        <>
          {/* Desktop Table View */}
      <div className={styles.desktopTable}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Username</th>
              <th>Role</th>
              <th>District</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td style={{ color: 'var(--muted)' }}>{u.username}</td>
                <td>
                  <span style={{ 
                    background: 'var(--accent-bg)', color: 'var(--accent)',
                    padding: '0.35rem 0.85rem', borderRadius: '999px', fontSize: '0.8rem', fontWeight: 600
                  }}>
                    {formatRole(u.role)}
                  </span>
                </td>
                <td>{u.district}</td>
                <td>
                  {u.is_active ? 
                    <span style={{ color: 'var(--green)' }}>Active</span> : 
                    <span style={{ color: 'var(--red)' }}>Inactive</span>
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards View */}
      <div className={styles.mobileCards}>
        {users.map(u => (
          <div key={u.id} className={styles.userCard}>
            <div className={styles.cardHeader}>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span className={styles.cardName}>{u.full_name}</span>
                <span className={styles.cardUsername}>{u.username}</span>
              </div>
              <span style={{ 
                background: 'var(--accent-bg)', color: 'var(--accent)',
                padding: '0.25rem 0.65rem', borderRadius: '999px', fontSize: '0.75rem', fontWeight: 600
              }}>
                {formatRole(u.role)}
              </span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem', borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
              <div className={styles.cardRow}>
                <span style={{ color: 'var(--muted)' }}>District:</span>
                <span>{u.district}</span>
              </div>
              <div className={styles.cardRow}>
                <span style={{ color: 'var(--muted)' }}>Status:</span>
                <span>
                  {u.is_active ? 
                    <span style={{ color: 'var(--green)', fontWeight: 500 }}>Active</span> : 
                    <span style={{ color: 'var(--red)', fontWeight: 500 }}>Inactive</span>
                  }
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
      </>
      )}

      {isModalOpen && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: 'var(--surface)', padding: '2rem', borderRadius: '12px', 
            width: '100%', maxWidth: '500px', border: '1px solid var(--border)'
          }}>
            <h2 style={{ marginTop: 0, marginBottom: '1.5rem', fontSize: '1.4rem' }}>Add New User</h2>
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              
              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Full Name</label>
                  <input required name="full_name" value={formData.full_name} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Username</label>
                  <input required name="username" value={formData.username} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Password</label>
                <input required type="password" name="password" value={formData.password} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
              </div>

              <div style={{ display: 'flex', gap: '1rem' }}>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Role</label>
                  <select name="role" value={formData.role} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }}>
                    <option value="cci_staff">CCI Staff</option>
                    <option value="cwc_member">CWC Member</option>
                    <option value="cwc_chairperson">CWC Chairperson</option>
                    <option value="dcpu_officer">DCPU Officer</option>
                    <option value="wcd_official">WCD Official</option>
                    <option value="system_admin">System Admin</option>
                  </select>
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>District</label>
                  <input required name="district" value={formData.district} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }} />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <button type="button" onClick={() => setIsModalOpen(false)} style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer' }}>Cancel</button>
                <button type="submit" disabled={submitting} style={{ padding: '0.75rem 1.5rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', opacity: submitting ? 0.7 : 1 }}>
                  {submitting ? 'Creating...' : 'Create User'}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}
