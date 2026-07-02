import React from 'react';
import { Link } from 'react-router-dom';
import styles from './Footer.module.css';

export function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.footerContent}>
        <div className={styles.footerLinks}>
          <Link to="/privacy" className={styles.footerLink}>Privacy Policy</Link>
          <Link to="/terms" className={styles.footerLink}>Terms of Service</Link>
          <Link to="/about" className={styles.footerLink}>About Us</Link>
          <Link to="/help" className={styles.footerLink}>Help Center</Link>
        </div>
        <div className={styles.footerCopyright}>
          © {new Date().getFullYear()} BalKawach Initiative. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
