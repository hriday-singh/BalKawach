import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Users, Scale, Bell, Settings, Layers } from 'lucide-react';
import styles from './BottomNav.module.css';
import { useAuth } from '../../contexts/AuthContext';

export function BottomNav() {
  const { user } = useAuth();
  const [showAdminSheet, setShowAdminSheet] = useState(false);
  const [showWorkspaceSheet, setShowWorkspaceSheet] = useState(false);

  return (
    <nav className={styles.bottomNav}>
      {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
        <NavLink to="/dashboard" className={({ isActive }) => isActive ? `${styles.navItem} ${styles.active}` : styles.navItem}>
          <LayoutDashboard size={24} />
          <span className={styles.label}>Dashboard</span>
        </NavLink>
      )}
      
      {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'cci_staff'].includes(user?.role) && (
        <NavLink to="/children" className={({ isActive }) => isActive ? `${styles.navItem} ${styles.active}` : styles.navItem}>
          <Users size={24} />
          <span className={styles.label}>Children</span>
        </NavLink>
      )}
      
      {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
        <button 
          className={showWorkspaceSheet ? `${styles.navItem} ${styles.active}` : styles.navItem}
          onClick={() => setShowWorkspaceSheet(true)}
        >
          <Layers size={24} />
          <span className={styles.label}>Workspace</span>
        </button>
      )}
      
      {['system_admin', 'cwc_chairperson', 'cwc_member', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
        <NavLink to="/alerts" className={({ isActive }) => isActive ? `${styles.navItem} ${styles.active}` : styles.navItem}>
          <Bell size={24} />
          <span className={styles.label}>Alerts</span>
        </NavLink>
      )}

      {user?.role === 'system_admin' && (
        <button 
          className={showAdminSheet ? `${styles.navItem} ${styles.active}` : styles.navItem}
          onClick={() => setShowAdminSheet(true)}
        >
          <Settings size={24} />
          <span className={styles.label}>Admin</span>
        </button>
      )}

      {showAdminSheet && (
        <div className={styles.bottomSheetOverlay} onClick={() => setShowAdminSheet(false)}>
          <div className={styles.bottomSheet} onClick={e => e.stopPropagation()}>
            <div className={styles.sheetHeader}>
              <span className={styles.sheetTitle}>Admin Menu</span>
              <button className={styles.closeSheetBtn} onClick={() => setShowAdminSheet(false)}>×</button>
            </div>
            <div className={styles.sheetOptions}>
              <NavLink to="/users" className={styles.sheetOption} onClick={() => setShowAdminSheet(false)}>
                Users
              </NavLink>
              <NavLink to="/system" className={styles.sheetOption} onClick={() => setShowAdminSheet(false)}>
                System Status
              </NavLink>
              <NavLink to="/audit" className={styles.sheetOption} onClick={() => setShowAdminSheet(false)}>
                Audit Logs
              </NavLink>
              <NavLink to="/transcription-logs" className={styles.sheetOption} onClick={() => setShowAdminSheet(false)}>
                Transcription Logs
              </NavLink>
            </div>
          </div>
        </div>
      )}

      {showWorkspaceSheet && (
        <div className={styles.bottomSheetOverlay} onClick={() => setShowWorkspaceSheet(false)}>
          <div className={styles.bottomSheet} onClick={e => e.stopPropagation()}>
            <div className={styles.sheetHeader}>
              <span className={styles.sheetTitle}>Workspace Menu</span>
              <button className={styles.closeSheetBtn} onClick={() => setShowWorkspaceSheet(false)}>×</button>
            </div>
            <div className={styles.sheetOptions}>
              {['system_admin', 'cwc_chairperson', 'cwc_member'].includes(user?.role) && (
                <NavLink to="/hearings" className={styles.sheetOption} onClick={() => setShowWorkspaceSheet(false)}>
                  Hearings
                </NavLink>
              )}
              {['system_admin', 'cwc_chairperson', 'cwc_member'].includes(user?.role) && (
                <NavLink to="/orders" className={styles.sheetOption} onClick={() => setShowWorkspaceSheet(false)}>
                  CWC Orders
                </NavLink>
              )}
              {['system_admin', 'dcpu_officer'].includes(user?.role) && (
                <NavLink to="/ccis" className={styles.sheetOption} onClick={() => setShowWorkspaceSheet(false)}>
                  CCI Monitoring
                </NavLink>
              )}
              {['system_admin', 'dcpu_officer', 'wcd_official'].includes(user?.role) && (
                <NavLink to="/reports" className={styles.sheetOption} onClick={() => setShowWorkspaceSheet(false)}>
                  Reports
                </NavLink>
              )}
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
