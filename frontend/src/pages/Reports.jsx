import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Download, FileText, AlertCircle, Clock, RefreshCw, Construction, Activity } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [requesting, setRequesting] = useState(false);
  const { token, user } = useAuth();

  const fetchReports = async () => {
    try {
      const res = await axios.get('/api/reports', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = res.data.data || res.data;
      if (data && data.reports !== undefined) {
        setReports(data.reports || []);
        setStats(data.statistics || null);
      } else {
        setReports(Array.isArray(data) ? data : []);
      }
      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
    // Poll every 5 seconds if any report is processing
    const interval = setInterval(() => {
      setReports(prev => {
        if (prev.some(r => r.status === 'processing' || r.status === 'pending')) {
          fetchReports();
        }
        return prev;
      });
    }, 5000);
    return () => clearInterval(interval);
  }, [token]);

  const requestReport = async (type) => {
    setRequesting(true);
    try {
      await axios.post(`/api/reports?report_type=${type}`, {}, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchReports();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to request report');
    } finally {
      setRequesting(false);
    }
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'completed': return <Download size={18} style={{ color: 'var(--green)' }} />;
      case 'processing': 
      case 'pending': return <RefreshCw size={18} className="spin" style={{ color: 'var(--accent)' }} />;
      case 'failed': return <AlertCircle size={18} style={{ color: 'var(--red)' }} />;
      default: return <FileText size={18} style={{ color: 'var(--muted)' }} />;
    }
  };

  const getStatusBadge = (status) => {
    switch(status) {
      case 'completed': return { bg: 'rgba(34,197,94,0.1)', color: 'var(--green)', text: 'Ready' };
      case 'processing': 
      case 'pending': return { bg: 'rgba(59,130,246,0.1)', color: 'var(--accent)', text: 'Processing' };
      case 'failed': return { bg: 'rgba(239,68,68,0.1)', color: 'var(--red)', text: 'Failed' };
      default: return { bg: 'var(--surface)', color: 'var(--muted)', text: status };
    }
  };

  if (loading && reports.length === 0) return <div style={{ padding: '2rem', color: 'var(--muted)' }}>Loading reports...</div>;

  return (
    <div className="page active" style={{ width: '100%', padding: '2rem', maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', textAlign: 'center' }}>
      <div style={{ background: 'var(--surface)', padding: '3rem', borderRadius: '16px', border: '1px solid var(--border)', maxWidth: '600px', width: '100%' }}>
        <Construction size={64} style={{ color: 'var(--accent)', marginBottom: '1.5rem', opacity: 0.8 }} />
        <h2 style={{ fontSize: '2rem', fontWeight: 600, margin: '0 0 1rem 0' }}>Under Construction</h2>
        <p style={{ color: 'var(--muted)', fontSize: '1.1rem', lineHeight: '1.6', margin: 0 }}>
          We are currently building out the new Reports & Analytics dashboard. 
          Soon, you will be able to generate deep insights, custom cross-district metrics, and automated PDF exports right from this page.
        </p>
        
        <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
          <div style={{ padding: '0.75rem 1.5rem', background: 'var(--bg)', borderRadius: '8px', border: '1px solid var(--border)', color: 'var(--muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText size={16} /> District Reports
          </div>
          <div style={{ padding: '0.75rem 1.5rem', background: 'var(--bg)', borderRadius: '8px', border: '1px solid var(--border)', color: 'var(--muted)', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={16} /> CCI Analytics
          </div>
        </div>
      </div>
    </div>
  );
}
