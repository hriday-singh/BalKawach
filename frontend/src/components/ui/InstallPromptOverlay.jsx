import React, { useState, useEffect } from 'react';
import { Smartphone } from 'lucide-react';

export default function InstallPromptOverlay() {
  const [show, setShow] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    
    if (params.get('install') === 'true' && !isStandalone) {
      setShow(true);
    }
    
    const handleBeforeInstallPrompt = (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setDeferredPrompt(null);
        setInstalled(true);
      }
    } else {
      alert("To install the app, tap 'Add to Home Screen' in your browser menu (usually three dots in the top right or the share button at the bottom).");
    }
  };
  
  const handleContinue = () => {
    const newUrl = window.location.pathname;
    window.history.replaceState({}, '', newUrl);
    setShow(false);
  };

  if (!show) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
      backgroundColor: 'var(--bg, #F3EDE3)', zIndex: 99999, display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyItems: 'center', justifyContent: 'center', padding: '24px'
    }}>
      <div style={{ maxWidth: '400px', width: '100%', background: 'white', padding: '32px 24px', borderRadius: '16px', boxShadow: '0 12px 32px rgba(43,38,34,0.08)', textAlign: 'center' }}>
        <div style={{ marginBottom: '24px', background: 'var(--surface, #FBF8F2)', padding: '24px', borderRadius: '12px' }}>
          <Smartphone size={56} color="var(--accent)" style={{ marginBottom: '16px' }} />
          <h2 style={{ fontSize: '1.5rem', marginBottom: '8px', color: 'var(--text)', fontFamily: 'Bricolage Grotesque, sans-serif' }}>Install BalKawach</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: 1.5 }}>
            Add this app to your home screen for the best mobile experience, offline capabilities, and quick access.
          </p>
        </div>
        
        {installed ? (
          <div style={{ marginBottom: '24px', padding: '16px', background: 'rgba(92,145,101,0.1)', color: '#5C9165', borderRadius: '8px', fontWeight: 600 }}>
            App Installed successfully! Please open the app from your home screen and enjoy!
          </div>
        ) : (
          <button onClick={handleInstallClick} style={{
            background: 'var(--accent)', color: 'white', border: 'none', padding: '14px 24px',
            borderRadius: '8px', fontWeight: 600, cursor: 'pointer', fontSize: '1rem', width: '100%', marginBottom: '16px'
          }}>
            Install App Now
          </button>
        )}
        
        <button onClick={handleContinue} style={{
          background: 'transparent', color: 'var(--text-secondary)', border: 'none',
          fontWeight: 500, cursor: 'pointer', fontSize: '0.95rem', padding: '8px'
        }}>
          Continue to App
        </button>
      </div>
    </div>
  );
}
