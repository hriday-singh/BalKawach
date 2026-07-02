import React from 'react';
import { Outlet } from 'react-router-dom';
import { BottomNav } from './BottomNav';
import { TopNav } from './TopNav';
import { Footer } from './Footer';
import styles from './PageShell.module.css';

export default function PageShell() {
  return (
    <div className={styles.pageShell}>
      <TopNav />
      <main className={styles.mainContent}>
        <div className={styles.contentWrapper}>
          <Outlet />
          <Footer />
        </div>
      </main>
      <BottomNav />
    </div>
  );
}
