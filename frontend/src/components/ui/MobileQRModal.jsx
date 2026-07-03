import React, { useState, useEffect } from 'react';
import QRCode from 'react-qr-code';
import { X, Smartphone, Loader2 } from 'lucide-react';
import axios from 'axios';

export default function MobileQRModal({ onClose }) {
  const [qrUrl, setQrUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchIp = async () => {
      try {
        const res = await axios.get('/api/system/network-info');
        const ip = res.data.lan_ip;
        // Construct the URL using the frontend port (9122)
        const url = `http://${ip}:9122/`;
        setQrUrl(url);
      } catch (err) {
        console.error("Failed to fetch network info", err);
        setError("Could not generate QR Code. Make sure the backend is running.");
      } finally {
        setLoading(false);
      }
    };
    fetchIp();
  }, []);

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.7)', zIndex: 9999,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '1rem', backdropFilter: 'blur(4px)'
    }}>
      <div style={{
        background: 'var(--surface, #ffffff)',
        width: '100%',
        maxWidth: '400px',
        borderRadius: '16px',
        border: '1px solid var(--border)',
        boxShadow: '0 20px 40px rgba(0,0,0,0.15)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        animation: 'fadeIn 0.2s ease-out'
      }}>
        <div style={{ 
          padding: '1.25rem 1.5rem', 
          borderBottom: '1px solid var(--border)', 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          background: 'var(--bg, #FBF8F2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text)' }}>
            <Smartphone size={20} color="var(--accent)" />
            <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 600 }}>Mobile Access</h2>
          </div>
          <button 
            onClick={onClose} 
            style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', display: 'flex', padding: '4px', borderRadius: '50%' }}
            onMouseOver={(e) => e.currentTarget.style.background = 'var(--surface)'}
            onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <X size={18} />
          </button>
        </div>
        
        <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
          
          {loading ? (
            <div style={{ padding: '3rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', color: 'var(--muted)' }}>
              <Loader2 size={32} style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)' }} />
              <p>Generating QR Code...</p>
            </div>
          ) : error ? (
            <div style={{ padding: '2rem 1rem', color: 'var(--danger, #ef4444)' }}>
              <p>{error}</p>
            </div>
          ) : (
            <>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.95rem' }}>
                Scan this QR code with your phone's camera to instantly open BalKawach.
              </p>
              
              <div style={{ 
                background: 'white', 
                padding: '1.5rem', 
                borderRadius: '12px', 
                border: '1px solid #EEE6D8',
                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                marginBottom: '1.5rem'
              }}>
                <QRCode 
                  value={qrUrl} 
                  size={200}
                  level="H"
                  fgColor="#2B2622"
                />
              </div>

              <div style={{ background: 'var(--bg, #FBF8F2)', padding: '0.75rem 1rem', borderRadius: '8px', border: '1px dashed var(--border)', width: '100%', wordBreak: 'break-all' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>Network URL</span>
                <a href={qrUrl} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', fontWeight: 500, textDecoration: 'none', fontSize: '0.9rem' }}>
                  {qrUrl}
                </a>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
