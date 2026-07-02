import React from 'react';

/**
 * StatCard component
 * @param {Object} props
 * @param {string} props.icon - The icon to display (emoji or icon component)
 * @param {number|string} props.value - The main statistical value
 * @param {string} props.label - The label for the stat
 * @param {'red' | 'amber' | 'green'} [props.urgency] - Optional urgency color
 */
export function StatCard({ icon, value, label, urgency }) {
  let cardClass = 'stat-card';
  if (urgency === 'red') cardClass += ' urgency-red';
  else if (urgency === 'amber') cardClass += ' urgency-amber';
  else if (urgency === 'green') cardClass += ' urgency-green';

  return (
    <div className={cardClass}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
