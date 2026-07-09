import React, { useState, useRef, useEffect } from 'react';
import { Shield, Lock, User, LogIn, ChevronRight, MessageSquare, ArrowLeft, ChevronDown, QrCode } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import MobileQR from '../components/ui/MobileQR';
import styles from './Login.module.css';

const QUICK_ACCESS_GROUPS = [
  {
    name: 'Global / State Overseers',
    users: [
      { username: 'admin', name: 'System Administrator', role: 'System Admin (Global)' },
      { username: 'wcd.official', name: 'State Director', role: 'WCD Official (State)' },
    ]
  },
  {
    name: 'Hyderabad (Sishu Vihar)',
    users: [
      { username: 'hyd.dcpu', name: 'Meera Patel', role: 'DCPU Officer (Hyderabad)' },
      { username: 'hyd.chair', name: 'Deepak Joshi', role: 'CWC Chairperson (Hyderabad)' },
      { username: 'hyd.cwc', name: 'Priya Sharma', role: 'CWC Member (Hyderabad)' },
      { username: 'hyd.staff', name: 'Lakshmi Devi', role: 'CCI Staff (Hyderabad)' },
    ]
  },
  {
    name: 'Visakhapatnam (Visakha Home)',
    users: [
      { username: 'vizag.dcpu', name: 'Arjun Kumar', role: 'DCPU Officer (Visakhapatnam)' },
      { username: 'vizag.chair', name: 'Srinivas Reddy', role: 'CWC Chairperson (Visakhapatnam)' },
      { username: 'vizag.cwc', name: 'Kavitha Nair', role: 'CWC Member (Visakhapatnam)' },
      { username: 'vizag.staff', name: 'Rao Garu', role: 'CCI Staff (Visakhapatnam)' },
    ]
  },
  {
    name: 'Noida (Rainbow Home)',
    users: [
      { username: 'noida.dcpu', name: 'Ramesh Prasad', role: 'DCPU Officer (Noida)' },
      { username: 'noida.chair', name: 'Ananya Sharma', role: 'CWC Chairperson (Noida)' },
      { username: 'noida.cwc', name: 'Vikram Singh', role: 'CWC Member (Noida)' },
      { username: 'noida.staff', name: 'Suresh Rao', role: 'CCI Staff (Noida)' },
    ]
  }
];

export default function Login() {
  const { login, setUserDirect } = useAuth();
  
  // State machine: 'login' | 'otp'
  const [screen, setScreen] = useState('login');
  
  // Login screen state
  const [activeTab, setActiveTab] = useState('signin');
  const [expandedGroup, setExpandedGroup] = useState('Global / State Overseers');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  
  // OTP screen state
  const [pendingUser, setPendingUser] = useState(null);
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [isVerifying, setIsVerifying] = useState(false);
  const [toastVisible, setToastVisible] = useState(false);
  const otpRefs = useRef([]);

  // Form submission
  const handleSubmit = async (e) => {
    e?.preventDefault();
    setError('');
    setIsLoading(true);
    
    try {
      const user = await login(username, password);
      setPendingUser(user);
      setScreen('otp');
      setOtp(['', '', '', '', '', '']);
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Login failed. Please check your credentials.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickAccess = (user) => {
    setUsername(user.username);
    setPassword('password123'); // Demo password
    
    // Simulate slight delay for effect
    setIsLoading(true);
    setTimeout(() => {
      // Direct call since state updates are async
      login(user.username, 'password123')
        .then(u => {
          setPendingUser(u);
          setScreen('otp');
          setOtp(['', '', '', '', '', '']);
        })
        .catch(() => setError('Quick access login failed'))
        .finally(() => setIsLoading(false));
    }, 400);
  };

  // OTP Handlers
  const handleOtpChange = (index, value) => {
    if (value.length > 1) value = value.slice(-1);
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // Auto-advance focus
    if (value && index < 5) {
      otpRefs.current[index + 1]?.focus();
    }
  };

  const handleOtpKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      otpRefs.current[index - 1]?.focus();
    } else if (e.key === 'Enter') {
      if (!isVerifying && !otp.some(d => d === '')) {
        handleVerify();
      }
    }
  };

  const handleVerify = () => {
    setIsVerifying(true);
    setTimeout(() => {
      if (pendingUser) {
        setUserDirect(pendingUser);
      }
    }, 800); // Simulate network latency
  };

  const handleResend = () => {
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 3000);
  };

  if (screen === 'otp') {
    return (
      <div className={styles.container}>
        <div className={`${styles.card} ${styles.screenEnter}`}>
          <div className={styles.otpHeader}>
            <div className={styles.otpIconWrap}>
              <MessageSquare size={32} />
            </div>
            <h2>Verify Your Identity</h2>
            <p className={styles.otpSubtitle}>
              We sent a 6-digit SMS OTP to your registered phone
            </p>
            <p className={styles.otpPhone}>••••••7890</p>
          </div>

          <div className={styles.otpInputs}>
            {otp.map((digit, index) => (
              <input
                key={index}
                ref={(el) => (otpRefs.current[index] = el)}
                type="tel"
                inputMode="numeric"
                pattern="[0-9]*"
                className={styles.otpDigit}
                value={digit}
                onChange={(e) => handleOtpChange(index, e.target.value)}
                onKeyDown={(e) => handleOtpKeyDown(index, e)}
                autoFocus={index === 0}
                placeholder={index + 1}
                maxLength={1}
              />
            ))}
          </div>

          <div className={styles.otpActions}>
            <button 
              className={styles.verifyBtn} 
              onClick={handleVerify}
              disabled={isVerifying || otp.some(d => d === '')}
            >
              {isVerifying ? 'Verifying...' : 'Verify & Continue'}
            </button>
            <p className={styles.otpDemoNote}>Demo mode: any 6-digit code works</p>
            
            <button className={styles.resendLink} onClick={handleResend}>
              Resend OTP
            </button>

            <button className={styles.backLink} onClick={() => setScreen('login')}>
              <ArrowLeft size={14} /> Back to login
            </button>
          </div>
        </div>
        
        <div className={`${styles.toast} ${toastVisible ? styles.toastVisible : ''}`}>
          OTP Resent!
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={`${styles.card} ${styles.screenEnter}`}>
        <div className={styles.brand}>
          <div className={styles.shield}><Shield size={32} /></div>
          <h1>BalKawach</h1>
          <p>Child Protection Management System</p>
        </div>

        <div className={styles.tabs}>
          <button 
            className={`${styles.tab} ${activeTab === 'signin' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('signin')}
          >
            Sign In
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'quickaccess' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('quickaccess')}
          >
            Quick Access
          </button>
          <button 
            className={`${styles.tab} ${activeTab === 'mobileqr' ? styles.tabActive : ''}`}
            onClick={() => setActiveTab('mobileqr')}
            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <QrCode size={14} /> Mobile App
          </button>
        </div>

        {error && <div className={styles.error}>{error}</div>}

        {activeTab === 'signin' ? (
          <form onSubmit={handleSubmit} className={styles.form}>
            <div className={styles.inputGroup}>
              <label>Username</label>
              <div className={styles.inputWrapper}>
                <User size={18} className={styles.inputIcon} />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your username"
                  required
                />
              </div>
            </div>

            <div className={styles.inputGroup}>
              <label>Password</label>
              <div className={styles.inputWrapper}>
                <Lock size={18} className={styles.inputIcon} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
              </div>
            </div>

            <button type="submit" className={styles.submitBtn} disabled={isLoading}>
              {isLoading ? 'Processing...' : (
                <>Sign In <LogIn size={18} /></>
              )}
            </button>
          </form>
        ) : activeTab === 'quickaccess' ? (
          <div className={styles.quickAccessList}>
            {QUICK_ACCESS_GROUPS.map((group) => (
              <div key={group.name} className={styles.groupContainer}>
                <div 
                  className={styles.groupHeader}
                  onClick={() => setExpandedGroup(expandedGroup === group.name ? null : group.name)}
                >
                  <span className={styles.groupTitle}>{group.name}</span>
                  <ChevronDown 
                    size={16} 
                    className={`${styles.groupIcon} ${expandedGroup === group.name ? styles.groupIconOpen : ''}`} 
                  />
                </div>
                
                {expandedGroup === group.name && (
                  <div className={styles.groupContent}>
                    {group.users.map((u) => (
                      <div 
                        key={u.username} 
                        className={`${styles.userCard} ${isLoading ? styles.userCardLoading : ''}`}
                        onClick={() => !isLoading && handleQuickAccess(u)}
                      >
                        <div className={styles.userAvatar}>
                          {u.name.charAt(0)}
                        </div>
                        <div className={styles.userInfo}>
                          <div className={styles.userName}>{u.name}</div>
                          <div className={styles.userRole}>{u.role}</div>
                        </div>
                        <ChevronRight size={18} className={styles.userChevron} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <p className={styles.quickAccessHint}>Click a profile to login automatically</p>
          </div>
        ) : (
          <MobileQR />
        )}
      </div>
    </div>
  );
}
