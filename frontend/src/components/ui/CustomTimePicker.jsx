import React, { useState, useRef, useEffect } from 'react';
import { Clock } from 'lucide-react';
import styles from './CustomSelect.module.css';

export default function CustomTimePicker({ value, onChange, name, placeholder = "Select Time" }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Generate 30-minute intervals from 09:00 to 18:00
  const timeOptions = [];
  for (let h = 9; h <= 18; h++) {
    timeOptions.push(`${h.toString().padStart(2, '0')}:00`);
    if (h !== 18) {
      timeOptions.push(`${h.toString().padStart(2, '0')}:30`);
    }
  }

  useEffect(() => {
    function handleClickOutside(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (time) => {
    if (onChange) {
      onChange({ target: { name, value: time } });
    }
    setIsOpen(false);
  };

  return (
    <div className={styles.container} ref={containerRef}>
      <div 
        className={`${styles.selectBox} ${isOpen ? styles.open : ''}`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className={value ? styles.value : styles.placeholder}>
          {value || placeholder}
        </span>
        <Clock size={16} className={styles.icon} />
      </div>

      {isOpen && (
        <div className={styles.dropdown}>
          {timeOptions.map((time) => (
            <div 
              key={time} 
              className={`${styles.option} ${value === time ? styles.selected : ''}`}
              onClick={() => handleSelect(time)}
            >
              {time}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
