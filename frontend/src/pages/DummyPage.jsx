import React from 'react';
import styles from './DummyPage.module.css';

export default function DummyPage({ title }) {
  const getContent = () => {
    switch (title) {
      case 'Privacy Policy':
        return (
          <>
            <p>Your privacy is important to us. It is BalKawach's policy to respect your privacy regarding any information we may collect from you across our website and applications.</p>
            <p>We only ask for personal information when we truly need it to provide a service to you. We collect it by fair and lawful means, with your knowledge and consent. We also let you know why we’re collecting it and how it will be used.</p>
            <p>We only retain collected information for as long as necessary to provide you with your requested service. What data we store, we’ll protect within commercially acceptable means to prevent loss and theft, as well as unauthorized access, disclosure, copying, use or modification.</p>
          </>
        );
      case 'Terms of Service':
        return (
          <>
            <p>By accessing the website at BalKawach, you are agreeing to be bound by these terms of service, all applicable laws and regulations, and agree that you are responsible for compliance with any applicable local laws.</p>
            <p>If you do not agree with any of these terms, you are prohibited from using or accessing this site. The materials contained in this website are protected by applicable copyright and trademark law.</p>
            <p>Permission is granted to temporarily download one copy of the materials (information or software) on BalKawach's website for personal, non-commercial transitory viewing only.</p>
          </>
        );
      case 'About Us':
        return (
          <>
            <p>BalKawach is a comprehensive digital initiative aimed at streamlining and digitizing the child welfare system. Our mission is to provide transparency, efficiency, and real-time monitoring for children under care.</p>
            <p>We work closely with Child Welfare Committees (CWC), District Child Protection Units (DCPU), and Child Care Institutions (CCI) to ensure every child's safety and timely legal progression.</p>
            <p>Our platform aggregates data, monitors pending deadlines, tracks legal status, and facilitates secure transcription and auditing to maintain the highest standards of accountability.</p>
          </>
        );
      case 'Help Center':
        return (
          <>
            <p>Welcome to the BalKawach Help Center. If you are experiencing technical difficulties or have questions about the platform, you've come to the right place.</p>
            <p><strong>Common Issues:</strong></p>
            <ul style={{ textAlign: 'left', margin: '16px auto', maxWidth: '400px' }}>
              <li>How to schedule a new hearing</li>
              <li>Updating a child's legal status</li>
              <li>Resetting your administrator password</li>
              <li>Reviewing transcription logs</li>
            </ul>
            <p>If you need further assistance, please contact your system administrator or support liaison.</p>
          </>
        );
      default:
        return <p>Content for {title} is currently being updated. Please check back soon.</p>;
    }
  };

  return (
    <div className={`page active ${styles.container}`}>
      <div className={styles.content}>
        <h1 className={styles.title}>{title}</h1>
        <div className={styles.description}>
          {getContent()}
        </div>
      </div>
    </div>
  );
}
