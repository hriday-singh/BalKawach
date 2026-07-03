import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import styles from './CustomSelect.module.css';

export default function CustomSelect({ options, value, onChange, placeholder = "Select...", name }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const selectedOption = options.find(opt => opt.value === value);

  return (
    <div className={styles.container} ref={containerRef}>
      <div 
        className={`${styles.selectBox} ${isOpen ? styles.open : ''}`} 
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className={selectedOption ? styles.value : styles.placeholder}>
          {selectedOption ? selectedOption.label : placeholder}
        </span>
        <ChevronDown size={16} className={styles.icon} />
      </div>
      {isOpen && (
        <div className={styles.dropdown}>
          {options.map(opt => (
            <div 
              key={opt.value} 
              className={`${styles.option} ${value === opt.value ? styles.selected : ''}`}
              onClick={() => {
                onChange({ target: { name, value: opt.value } });
                setIsOpen(false);
              }}
            >
              {opt.label}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
