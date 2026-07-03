import React, { useState, useRef, useEffect } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from 'lucide-react';
import styles from './CustomDatePicker.module.css';

const daysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
const startDayOfMonth = (year, month) => new Date(year, month, 1).getDay();

const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const DAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export default function CustomDatePicker({ value, onChange, name, placeholder = "dd - mm - yyyy" }) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);
  
  const initialDate = value ? new Date(value) : new Date();
  
  const [inputValue, setInputValue] = useState(value ? value.split('-').reverse().join('-') : '');

  const [currentMonth, setCurrentMonth] = useState(initialDate.getMonth());
  const [currentYear, setCurrentYear] = useState(initialDate.getFullYear());

  useEffect(() => {
    if (value) {
      setInputValue(value.split('-').reverse().join('-'));
      const d = new Date(value);
      if (!isNaN(d.getTime())) {
        setCurrentMonth(d.getMonth());
        setCurrentYear(d.getFullYear());
      }
    }
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(prev => prev - 1);
    } else {
      setCurrentMonth(prev => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(prev => prev + 1);
    } else {
      setCurrentMonth(prev => prev + 1);
    }
  };

  const handleDateClick = (day) => {
    const formattedMonth = String(currentMonth + 1).padStart(2, '0');
    const formattedDay = String(day).padStart(2, '0');
    const newValue = `${currentYear}-${formattedMonth}-${formattedDay}`;
    onChange({ target: { name, value: newValue } });
    setIsOpen(false);
  };

  const handleInputChange = (e) => {
    const val = e.target.value;
    setInputValue(val);
    
    // basic regex for DD-MM-YYYY
    const match = val.match(/^(\d{2})[-/]?(\d{2})[-/]?(\d{4})$/);
    if (match) {
      const d = parseInt(match[1], 10);
      const m = parseInt(match[2], 10) - 1;
      const y = parseInt(match[3], 10);
      const dateObj = new Date(y, m, d);
      
      if (dateObj.getFullYear() === y && dateObj.getMonth() === m && dateObj.getDate() === d) {
        setCurrentMonth(m);
        setCurrentYear(y);
        const formattedMonth = String(m + 1).padStart(2, '0');
        const formattedDay = String(d).padStart(2, '0');
        onChange({ target: { name, value: `${y}-${formattedMonth}-${formattedDay}` } });
      }
    } else if (val === '') {
      onChange({ target: { name, value: '' } });
    }
  };

  const renderCalendar = () => {
    const days = [];
    const totalDays = daysInMonth(currentYear, currentMonth);
    const startDay = startDayOfMonth(currentYear, currentMonth);
    
    for (let i = 0; i < startDay; i++) {
      days.push(<div key={`empty-${i}`} className={styles.emptyDay}></div>);
    }
    
    for (let i = 1; i <= totalDays; i++) {
      const isSelected = value && 
        new Date(value).getDate() === i && 
        new Date(value).getMonth() === currentMonth && 
        new Date(value).getFullYear() === currentYear;
        
      days.push(
        <button 
          key={i} 
          type="button"
          className={`${styles.dayButton} ${isSelected ? styles.selected : ''}`}
          onClick={() => handleDateClick(i)}
        >
          {i}
        </button>
      );
    }
    return days;
  };

  return (
    <div className={styles.container} ref={containerRef}>
      <div 
        className={`${styles.inputBox} ${isOpen ? styles.open : ''}`}
        onClick={() => setIsOpen(true)}
      >
        <input 
          type="text" 
          value={inputValue} 
          onChange={handleInputChange} 
          placeholder="DD-MM-YYYY"
          className={styles.realInput}
        />
        <CalendarIcon size={16} className={styles.icon} />
      </div>
      
      {isOpen && (
        <div className={styles.calendarDropdown}>
          <div className={styles.calendarHeader}>
            <button type="button" className={styles.navButton} onClick={handlePrevMonth}><ChevronLeft size={16}/></button>
            <div className={styles.monthYear}>
              <select value={currentMonth} onChange={e => setCurrentMonth(Number(e.target.value))} className={styles.nativeSelect}>
                {MONTH_NAMES.map((m, i) => <option key={m} value={i}>{m}</option>)}
              </select>
              <select value={currentYear} onChange={e => setCurrentYear(Number(e.target.value))} className={styles.nativeSelect}>
                {Array.from({length: 100}, (_, i) => new Date().getFullYear() - 80 + i).map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <button type="button" className={styles.navButton} onClick={handleNextMonth}><ChevronRight size={16}/></button>
          </div>
          
          <div className={styles.daysGrid}>
            {DAYS.map(d => <div key={d} className={styles.dayLabel}>{d}</div>)}
            {renderCalendar()}
          </div>
        </div>
      )}
    </div>
  );
}
