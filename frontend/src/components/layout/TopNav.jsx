import React, { useState, useRef, useEffect } from 'react';
import { Shield, LayoutDashboard, Users, Scale, Bell, Settings, ChevronDown, Layers } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import styles from './TopNav.module.css';

export function TopNav() {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [adminDropdownOpen, setAdminDropdownOpen] = useState(false);
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const adminDropdownRef = useRef(null);
  const workspaceDropdownRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
      if (adminDropdownRef.current && !adminDropdownRef.current.contains(event.target)) {
        setAdminDropdownOpen(false);
      }
      if (workspaceDropdownRef.current && !workspaceDropdownRef.current.contains(event.target)) {
        setWorkspaceDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const initials = user?.full_name 
    ? user.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() 
    : 'U';

  return (
    <header className={styles.topNav}>
      <div className={styles.leftArea}>
        <div className={styles.brand}>
          <div className={styles.brandIcon}>
            <Shield size={18} />
          </div>
          <span style={{ fontFamily: '"Bricolage Grotesque", sans-serif', fontWeight: 700, fontSize: '1.2rem', letterSpacing: '-0.01em', color: 'var(--text, #2B2622)' }}>BalKawach</span>
        </div>
      </div>

      <div className={styles.desktopNav}>
        {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
          <NavLink to="/dashboard" className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
            <LayoutDashboard size={16} /> Dashboard
          </NavLink>
        )}
        
        {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'cci_staff'].includes(user?.role) && (
          <NavLink to="/children" className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
            <Users size={16} /> Children
          </NavLink>
        )}
        
        {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
          <NavLink to="/alerts" className={({ isActive }) => isActive ? `${styles.navLink} ${styles.active}` : styles.navLink}>
            <Bell size={16} /> Alerts
          </NavLink>
        )}

        {/* Workspace Dropdown for nested items */}
        {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
          <div className={styles.adminDropdown} ref={workspaceDropdownRef}>
            <button 
              className={`${styles.navLink} ${styles.adminBtn} ${workspaceDropdownOpen ? styles.active : ''}`}
              onClick={() => setWorkspaceDropdownOpen(!workspaceDropdownOpen)}
            >
              <Layers size={16} /> Workspace <ChevronDown size={14} />
            </button>
            {workspaceDropdownOpen && (
              <div className={styles.adminDropdownMenu}>
                {['system_admin', 'cwc_chairperson', 'cwc_member'].includes(user?.role) && (
                  <NavLink to="/hearings" className={styles.adminDropdownItem} onClick={() => setWorkspaceDropdownOpen(false)}>Hearings</NavLink>
                )}
                {['system_admin', 'cwc_chairperson', 'cwc_member'].includes(user?.role) && (
                  <NavLink to="/orders" className={styles.adminDropdownItem} onClick={() => setWorkspaceDropdownOpen(false)}>CWC Orders</NavLink>
                )}
                {['system_admin', 'dcpu_officer'].includes(user?.role) && (
                  <NavLink to="/ccis" className={styles.adminDropdownItem} onClick={() => setWorkspaceDropdownOpen(false)}>CCI Monitoring</NavLink>
                )}
                {['system_admin', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
                  <NavLink to="/reports" className={styles.adminDropdownItem} onClick={() => setWorkspaceDropdownOpen(false)}>Reports</NavLink>
                )}
              </div>
            )}
          </div>
        )}

        {user?.role === 'system_admin' && (
          <div className={styles.adminDropdown} ref={adminDropdownRef}>
            <button 
              className={`${styles.navLink} ${styles.adminBtn} ${adminDropdownOpen ? styles.active : ''}`}
              onClick={() => setAdminDropdownOpen(!adminDropdownOpen)}
            >
              <Settings size={16} /> Admin <ChevronDown size={14} />
            </button>
            {adminDropdownOpen && (
              <div className={styles.adminDropdownMenu}>
                <NavLink to="/users" className={styles.adminDropdownItem} onClick={() => setAdminDropdownOpen(false)}>Users</NavLink>
                <NavLink to="/system" className={styles.adminDropdownItem} onClick={() => setAdminDropdownOpen(false)}>System Status</NavLink>
                <NavLink to="/audit" className={styles.adminDropdownItem} onClick={() => setAdminDropdownOpen(false)}>Audit Logs</NavLink>
                <NavLink to="/transcription-logs" className={styles.adminDropdownItem} onClick={() => setAdminDropdownOpen(false)}>Transcription Logs</NavLink>
              </div>
            )}
          </div>
        )}
      </div>

      <div className={styles.rightArea}>
        <div className={styles.userInfo}>
          <div className={styles.avatarDropdown} ref={dropdownRef}>
            <div 
              className={styles.avatar} 
              onClick={() => setDropdownOpen(!dropdownOpen)}
            >
              {initials}
            </div>
            {dropdownOpen && (
              <div className={styles.dropdownMenu}>
                <div className={styles.dropdownUserInfo}>
                  <strong>{user?.full_name}</strong>
                  {user?.location && <div className={styles.userLocation}>{user.location}</div>}
                </div>
                <hr className={styles.dropdownDivider} />
                <div className={styles.dropdownItem} onClick={logout}>
                  Logout
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
