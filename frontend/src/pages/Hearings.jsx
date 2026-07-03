import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Calendar, Clock, ChevronRight, FileAudio, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import OrderCreationModal from '../components/forms/OrderCreationModal';
import AudioRecorder from '../components/recorder/AudioRecorder';
import CustomAudioPlayer from '../components/recorder/CustomAudioPlayer';
import styles from './Hearings.module.css';
import CustomSelect from '../components/ui/CustomSelect';
import CustomDatePicker from '../components/ui/CustomDatePicker';
import CustomTimePicker from '../components/ui/CustomTimePicker';


const formatStatus = (status) => {
  switch (status) {
    case 'scheduled': return 'Scheduled';
    case 'in_progress': return 'In Progress';
    case 'completed': return 'Completed';
    default: return status;
  }
};

const formatTime = (isoString) => {
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const formatDate = (dateString) => {
  if (!dateString) return '';
  // Backend sends a plain YYYY-MM-DD; slice off any legacy time component.
  // Built as local-time components (not `new Date(str)`) to avoid a UTC-parse day shift.
  const [year, month, day] = dateString.slice(0, 10).split('-').map(Number);
  const date = new Date(year, (month || 1) - 1, day || 1);
  if (isNaN(date.getTime())) return dateString;
  return date.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' });
};

export default function Hearings() {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const [view, setView] = useState('list'); // 'list' | 'console'
  const [activeTab, setActiveTab] = useState('All');
  const [hearings, setHearings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedHearing, setSelectedHearing] = useState(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [childrenList, setChildrenList] = useState([]);
  const [selectedChildId, setSelectedChildId] = useState(null);
  const [isCreating, setIsCreating] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [selectedLang, setSelectedLang] = useState('hi');
  const [supportedLanguages, setSupportedLanguages] = useState([
    { id: 'hi', label: 'Hindi' },
    { id: 'te', label: 'Telugu' },
    { id: 'en', label: 'English' },
    { id: 'mr', label: 'Marathi' },
    { id: 'kn', label: 'Kannada' }
  ]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [cwcMembers, setCwcMembers] = useState([]);
  
  const QUICK_LANGS = ['hi', 'te', 'en'];
  
  const threadEndRef = useRef(null);
  const dropdownRef = useRef(null);
  const childDropdownRef = useRef(null);
  const [childSearchQuery, setChildSearchQuery] = useState('');
  const [isChildDropdownOpen, setIsChildDropdownOpen] = useState(false);
  const [isOrderModalOpen, setIsOrderModalOpen] = useState(false);

  const [isEditHearingModalOpen, setIsEditHearingModalOpen] = useState(false);
  const [editHearingData, setEditHearingData] = useState({ hearing_date: '', scheduled_time: '', hearing_type: '', status: '', reschedule_reason: '', attendees: [] });
  const [manualText, setManualText] = useState('');
  const [recorderState, setRecorderState] = useState('idle');
  const [inputMode, setInputMode] = useState('audio'); // 'audio' or 'text'

  // When selectedHearing changes, update edit form
  useEffect(() => {
    if (selectedHearing) {
      let initialAttendees = [];
      try {
        if (typeof selectedHearing.attendees === 'string') {
          initialAttendees = JSON.parse(selectedHearing.attendees);
        } else if (Array.isArray(selectedHearing.attendees)) {
          initialAttendees = selectedHearing.attendees;
        }
      } catch(e) {}
      
      setEditHearingData({
        hearing_date: selectedHearing.hearing_date || '',
        scheduled_time: selectedHearing.scheduled_time || '',
        hearing_type: selectedHearing.hearing_type || '',
        status: selectedHearing.status || 'scheduled',
        reschedule_reason: selectedHearing.reschedule_reason || '',
        attendees: initialAttendees.map(a => typeof a === 'object' ? a.id : a)
      });
    }
  }, [selectedHearing]);

  const handleEditHearingSubmit = async () => {
    try {
      const payload = {
        ...editHearingData,
        attendees: JSON.stringify(editHearingData.attendees)
      };
      const res = await axios.put(`/api/hearings/${selectedHearing.id}`, payload);
      setSelectedHearing(res.data);
      setHearings(prev => prev.map(h => h.id === selectedHearing.id ? res.data : h));
      setIsEditHearingModalOpen(false);
    } catch (err) {
      console.error("Failed to update hearing", err);
      // fallback to optimistic update
      const updated = { ...selectedHearing, ...editHearingData };
      setSelectedHearing(updated);
      setHearings(prev => prev.map(h => h.id === selectedHearing.id ? updated : h));
      setIsEditHearingModalOpen(false);
    }
  };

  const handleManualSubmit = () => {
    if (!manualText.trim()) return;
    
    const newRecording = {
      id: `r${Date.now()}`,
      user: { 
        id: user?.id || 'current', 
        full_name: user?.full_name || user?.username || 'Me', 
        role: user?.role || 'user' 
      },
      timestamp: new Date().toISOString(),
      language: selectedLang,
      transcript: manualText,
      transcripts: [],
      selectedTranscriptIndex: 0,
      audioUrl: null,
      duration: 0,
      amplitudeHistory: [],
      status: 'completed'
    };

    setRecordings(prev => [...prev, newRecording]);
    
    const formData = new FormData();
    formData.append('final_transcript', manualText);
    formData.append('language', selectedLang);
    formData.append('user_id', user?.id || 'current');
    if (selectedHearing) {
      formData.append('hearing_id', selectedHearing.id);
    }
    axios.post('/api/transcribe/submit_text', formData).catch(e => console.error(e));
    
    setManualText('');
  };


  useEffect(() => {
    const fetchHearings = async () => {
      try {
        const response = await axios.get('/api/hearings');
        setHearings(response.data);
      } catch (err) {
        console.error("Error fetching hearings:", err);
      } finally {
        setLoading(false);
      }
    };
    const fetchLanguages = async () => {
      try {
        const response = await axios.get('/api/languages');
        const langArray = Object.entries(response.data).map(([code, name]) => ({ id: code, label: name }));
        if (langArray.length > 0) {
          const merged = [...langArray];
          if (!merged.find(l => l.id === 'mr')) merged.push({ id: 'mr', label: 'Marathi' });
          if (!merged.find(l => l.id === 'kn')) merged.push({ id: 'kn', label: 'Kannada' });
          setSupportedLanguages(merged);
        }
      } catch (err) {
        console.error("Error fetching languages:", err);
      }
    };
    const fetchUsers = async () => {
      try {
        const response = await axios.get('/api/users');
        const members = response.data.filter(u => u.role === 'cwc_member' || u.role === 'cwc_chairperson');
        setCwcMembers(members);
      } catch (err) {
        console.error("Error fetching users for attendees:", err);
      }
    };
    fetchHearings();
    fetchLanguages();
    fetchUsers();
  }, []);

  // Sync state with URL params
  useEffect(() => {
    if (hearings.length > 0) {
      const hId = searchParams.get('hearingId');
      const cId = searchParams.get('child_id');
      
      if (hId) {
        const matched = hearings.find(h => h.id === hId || h.id == hId);
        if (matched) {
          setSelectedHearing(matched);
          setView('console');
          // Fetch historical recordings for this hearing
          const fetchRecordings = async () => {
            try {
              const res = await axios.get(`/api/hearings/${hId}/recordings`);
              setRecordings(res.data);
            } catch (err) {
              console.error("Error fetching recordings:", err);
            }
          };
          fetchRecordings();
        }
      } else if (cId) {
        const childHearings = hearings.filter(h => h.child_id === cId || h.child_id == cId);
        if (childHearings.length > 0) {
          // Redirect to the first hearing for this child
          setSearchParams({ hearingId: childHearings[0].id });
        } else {
          // If no hearings exist yet, auto-create one
          const createNewHearing = async () => {
             try {
               const res = await axios.post('/api/hearings', { child_id: cId, district: user?.district || 'Unknown' });
               const newHearings = await axios.get('/api/hearings');
               setHearings(newHearings.data);
               setSearchParams({ hearingId: res.data.id });
             } catch (e) {
               console.error("Error auto-creating hearing", e);
               setView('list');
               setSelectedHearing(null);
             }
          }
          createNewHearing();
        }
      } else {
        setView('list');
        setSelectedHearing(null);
        setRecordings([]);
      }
    }
  }, [searchParams, hearings]);

  // Fetch children for dropdown
  useEffect(() => {
    if (isAddModalOpen && childrenList.length === 0) {
      axios.get('/api/children').then(res => {
        setChildrenList(res.data.data || res.data);
      }).catch(err => console.error(err));
    }
  }, [isAddModalOpen, childrenList.length]);

  const handleCreateHearing = async () => {
    if (!selectedChildId) return;

    setIsCreating(true);
    try {
      const response = await axios.post('/api/hearings', { child_id: selectedChildId, district: user?.district || 'Unknown' });
      const newHearings = await axios.get('/api/hearings');
      setHearings(newHearings.data);
      setIsAddModalOpen(false);
      setSelectedChildId(null);
      setChildSearchQuery('');
      setSearchParams({ hearingId: response.data.id });
    } catch (e) {
      if (e.response && e.response.status === 400) {
        alert(e.response.data.detail || "An active hearing already exists.");
      } else {
        console.error(e);
      }
    } finally {
      setIsCreating(false);
    }
  };

  // Scroll to bottom of chat when recordings change or console opens
  useEffect(() => {
    if (view === 'console' && threadEndRef.current) {
      threadEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [view, recordings]);

  // Click outside to close dropdowns
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDropdownOpen(false);
      }
      if (childDropdownRef.current && !childDropdownRef.current.contains(event.target)) {
        setIsChildDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleOpenConsole = (hearing) => {
    setSearchParams({ hearingId: hearing.id });
  };

  const handleCloseConsole = () => {
    setSearchParams({});
  };

  const handleSelectTranscript = async (id, idx) => {
    const recording = recordings.find(r => r.id === id);
    if (!recording) return;

    const chosenTranscript = recording.transcripts[idx];
    
    // Optimistically update UI
    setRecordings(prev => prev.map(rec => {
      if (rec.id === id) {
        return { 
          ...rec, 
          selectedTranscriptIndex: idx, 
          transcript: chosenTranscript,
          transcripts: [] // Clear options once selected
        };
      }
      return rec;
    }));

    // Save to backend
    try {
      const formData = new FormData();
      formData.append('final_transcript', chosenTranscript);
      await axios.post(`/api/transcribe/save/${id}`, formData);
    } catch (err) {
      console.error("Error saving transcript:", err);
      // Revert if failed (optional, keeping it simple for now)
    }
  };

  const handleRecordingComplete = async (blob, duration, amplitudeHistory) => {
    // Optimistic UI update
    const newRecording = {
      id: `r${Date.now()}`,
      user: { 
        id: user?.id || 'current', 
        full_name: user?.full_name || user?.username || 'Me', 
        role: user?.role || 'user' 
      },
      timestamp: new Date().toISOString(),
      language: selectedLang,
      transcript: 'Transcribing in background...',
      transcripts: [],
      selectedTranscriptIndex: null,
      audioUrl: URL.createObjectURL(blob),
      duration: duration || Math.floor(Math.random() * 30) + 5,
      amplitudeHistory: amplitudeHistory || [],
      status: 'pending'
    };

    setRecordings(prev => [...prev, newRecording]);

    try {
      const formData = new FormData();
      formData.append('audio', blob, 'hearing_audio.wav');
      formData.append('language', selectedLang);
      formData.append('user_id', user?.id || 'current');
      if (selectedHearing) {
        formData.append('hearing_id', selectedHearing.id);
      }

      const response = await axios.post('/api/transcribe/submit', formData);
      const jobId = response.data.job_id;

      pollJobStatus(newRecording.id, jobId);
    } catch (err) {
      console.error("Error submitting job:", err);
      setRecordings(prev => prev.map(rec => {
        if (rec.id === newRecording.id) {
          return { ...rec, transcript: 'Failed to start transcription.' };
        }
        return rec;
      }));
    }
  };

  const pollJobStatus = (recordingId, jobId) => {
    const poll = async () => {
      try {
        const res = await axios.get(`/api/transcribe/status/${jobId}`);
        const status = res.data.status;
        if (status === 'completed') {
          setRecordings(prev => prev.map(rec => {
            if (rec.id === recordingId) {
              if (res.data.final_transcript) {
                return {
                  ...rec,
                  transcript: res.data.final_transcript,
                  transcripts: [],
                  selectedTranscriptIndex: 0,
                  status: 'completed'
                };
              } else {
                // Auto-select RNN-T (best quality) to remove user friction
                const chosen = res.data.rnnt_transcript || res.data.ctc_transcript || "No transcription available";
                
                // Automatically save it to the backend
                const formData = new FormData();
                formData.append('final_transcript', chosen);
                axios.post(`/api/transcribe/save/${jobId}`, formData).catch(e => console.error(e));

                return {
                  ...rec,
                  transcript: chosen,
                  transcripts: [],
                  selectedTranscriptIndex: 0,
                  status: 'completed'
                };
              }
            }
            return rec;
          }));
        } else if (status === 'error' || status === 'failed') {
          setRecordings(prev => prev.map(rec => {
            if (rec.id === recordingId) {
              return { ...rec, transcript: 'Transcription failed.' };
            }
            return rec;
          }));
        } else {
          setTimeout(poll, 3000);
        }
      } catch (err) {
        console.error("Error polling status:", err);
        setTimeout(poll, 3000);
      }
    };
    
    setTimeout(poll, 3000);
  };

  // View A: Hearings List
  if (view === 'list') {
    const filteredHearings = activeTab === 'All' 
      ? hearings 
      : hearings.filter(h => formatStatus(h.status) === activeTab);

    return (
      <div className={styles.container}>
        <header className={styles.listHeader}>
          <div className={styles.listHeaderLeft}>
            <h2>Hearings</h2>
            <p>Manage CWC hearings and proceedings</p>
          </div>
          <button className={styles.btnSubmit} onClick={() => setIsAddModalOpen(true)}>+ Add Hearing</button>
        </header>
        
        <div className={styles.filterTabs}>
          {['All', 'Scheduled', 'In Progress', 'Completed'].map(tab => (
            <button 
              key={tab}
              className={`${styles.filterTab} ${activeTab === tab ? styles.filterTabActive : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', color: 'var(--muted)' }}>
            <Loader2 className={styles.spinner} size={32} />
            <p>Loading hearings...</p>
          </div>
        ) : filteredHearings.length === 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 20px', textAlign: 'center', color: 'var(--text-secondary, #6B6259)', background: 'rgba(255, 255, 255, 0.4)', borderRadius: '16px', border: '1px dashed var(--border, #EEE6D8)', marginTop: '2rem', width: '100%', flex: 1 }}>
            <Calendar size={48} style={{ opacity: 0.3, marginBottom: '16px', color: 'var(--accent, #E4720C)' }} />
            <h3 style={{ fontFamily: '"Bricolage Grotesque", sans-serif', fontSize: '1.25rem', color: 'var(--text, #2B2622)', marginBottom: '8px' }}>No hearings found</h3>
            <p style={{ fontSize: '0.9rem', maxWidth: '400px', margin: '0 auto' }}>There are currently no hearings matching your criteria. You can create a new hearing using the button above.</p>
          </div>
        ) : (
          <div className={styles.listContent}>
            {filteredHearings.map(hearing => (
              <div key={hearing.id} className={styles.hearingCard}>
                <div className={styles.cardHeader}>
                  <div className={styles.childInfo}>
                    <span className={styles.childName}>{hearing.child_name}</span>
                    <span className={styles.childCode}>{hearing.child_code}</span>
                  </div>
                  <span className={`${styles.statusBadge} ${styles[hearing.status]}`}>
                    {formatStatus(hearing.status)}
                  </span>
                </div>
                
                <div className={styles.dateTime}>
                  <span><Calendar size={14} /> {formatDate(hearing.hearing_date)}</span>
                  <span><Clock size={14} /> {hearing.scheduled_time || "TBD"}</span>
                </div>
                
                <p className={styles.notes}>
                  {hearing.notes || 'No notes available.'}
                </p>
                
                <button 
                  className={styles.openConsoleBtn}
                  onClick={() => handleOpenConsole(hearing)}
                >
                  Open Console <ChevronRight size={16} />
                </button>
              </div>
            ))}
          </div>
        )}

          {isAddModalOpen && (
            <div className={styles.modalOverlay}>
              <div className={styles.modalContent}>
                <div className={styles.modalHeader}>
                  <h3>Schedule New Hearing</h3>
                  <p>Select a child to schedule a hearing for.</p>
                </div>
                
                <div className={styles.comboboxContainer} ref={childDropdownRef}>
                  <input
                    type="text"
                    className={styles.comboboxInput}
                    placeholder="Search child by name or code..."
                    value={childSearchQuery}
                    onChange={(e) => {
                      setChildSearchQuery(e.target.value);
                      setIsChildDropdownOpen(true);
                    }}
                    onFocus={() => setIsChildDropdownOpen(true)}
                  />
                  {isChildDropdownOpen && (
                    <div className={styles.comboboxList}>
                      {(() => {
                        const filtered = childrenList.filter(c => 
                          (c.name || '').toLowerCase().includes(childSearchQuery.toLowerCase()) || 
                          (c.child_code || '').toLowerCase().includes(childSearchQuery.toLowerCase())
                        );
                        if (filtered.length > 0) {
                          return filtered.map(c => {
                            const isSelected = selectedChildId === c.id;
                            return (
                              <div 
                                key={c.id} 
                                className={`${styles.comboboxItem} ${isSelected ? styles.selected : ''}`}
                                onClick={() => {
                                  setSelectedChildId(isSelected ? null : c.id);
                                  setIsChildDropdownOpen(false);
                                }}
                                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                              >
                                <div style={{ width: '16px', height: '16px', borderRadius: '50%', border: '2px solid', borderColor: isSelected ? 'var(--accent)' : 'var(--border)', background: isSelected ? 'var(--accent)' : 'transparent', flexShrink: 0 }} />
                                <span className={styles.comboboxItemName}>{c.name}</span>
                                <span className={styles.comboboxItemCode}>{c.child_code}</span>
                              </div>
                            );
                          });
                        } else {
                          return <div className={styles.comboboxEmpty}>No children found</div>;
                        }
                      })()}
                    </div>
                  )}
                </div>

                {selectedChildId && (
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '12px', marginBottom: '12px' }}>
                    {(() => {
                      const child = childrenList.find(c => c.id === selectedChildId);
                      return child ? (
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--surface)', padding: '6px 10px', borderRadius: '6px', fontSize: '0.85rem', color: 'var(--text)', border: '1px solid var(--border)' }}>
                          {child.name} 
                          <button onClick={() => setSelectedChildId(null)} style={{ background: 'none', border: 'none', color: 'var(--muted)', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center' }}>
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
                          </button>
                        </div>
                      ) : null;
                    })()}
                  </div>
                )}

                <div className={styles.modalActions}>
                  <button 
                    className={styles.btnCancel} 
                    onClick={() => { 
                      setIsAddModalOpen(false); 
                      setSelectedChildId(null); 
                      setChildSearchQuery(''); 
                    }}
                    disabled={isCreating}
                  >
                    Cancel
                  </button>
                  <button 
                    className={styles.btnSubmit}
                    onClick={handleCreateHearing}
                    disabled={!selectedChildId || isCreating}
                  >
                    {isCreating ? 'Creating...' : 'Create Hearing'}
                  </button>
                </div>
              </div>
            </div>
          )}
      </div>
    );
  }

  // View B: Hearing Console (Chat interface)
  return (
    <div className={styles.container}>
      <div className={styles.consoleContainer}>
        {/* Header */}
        <div className={styles.consoleHeader}>
          <button className={styles.backBtn} onClick={handleCloseConsole}>
            <ArrowLeft size={20} />
          </button>
          <div className={styles.consoleTitle}>
            <h3>{selectedHearing?.child_name} ({selectedHearing?.child_code})</h3>
            <span className={styles.consoleSubtitle}>
              {formatDate(selectedHearing?.hearing_date)} • {selectedHearing?.scheduled_time || "TBD"}
            </span>
          </div>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span className={`${styles.statusBadge} ${styles[selectedHearing?.status]}`}>
              {formatStatus(selectedHearing?.status)}
            </span>
            <button
              onClick={() => setIsEditHearingModalOpen(true)}
              style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'transparent', color: 'var(--text)', cursor: 'pointer', fontSize: '0.85rem' }}
            >
              Edit Details
            </button>
            {(user?.role === 'cwc_chairperson' || user?.role === 'cwc_member') && (
              <button 
                onClick={() => setIsOrderModalOpen(true)}
                style={{ padding: '0.5rem 1rem', borderRadius: '6px', border: 'none', background: 'var(--accent)', color: 'var(--bg)', fontWeight: 600, cursor: 'pointer', fontSize: '0.85rem' }}
              >
                Draft Order
              </button>
            )}
          </div>
        </div>

        {/* Chat Thread */}
        <div className={styles.chatThread}>
          {recordings.map((rec) => {
            const isCurrentUser = user && (rec.user.id === user.id || rec.user.full_name === user.full_name);
            
            return (
              <div 
                key={rec.id} 
                className={`${styles.chatMessage} ${isCurrentUser ? styles.isCurrentUser : ''}`}
              >
                <div className={styles.messageAvatar}>
                  {isCurrentUser 
                    ? (user.full_name || user.username || 'You').charAt(0).toUpperCase()
                    : (rec.user.full_name || rec.user.id).charAt(0).toUpperCase()}
                </div>
                
                <div className={styles.messageContent}>
                  <div className={styles.messageMeta}>
                    <span className={styles.messageAuthor}>
                      {isCurrentUser ? 'You' : rec.user.full_name}
                    </span>
                    <span className={styles.messageTime}>{formatTime(rec.timestamp)}</span>
                  </div>
                  
                  <div className={styles.messageBubble}>
                    {rec.audioUrl ? (
                      <CustomAudioPlayer 
                        audioUrl={rec.audioUrl} 
                        explicitDuration={rec.duration} 
                        amplitudeHistory={rec.amplitudeHistory} 
                      />
                    ) : (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '4px', color: 'var(--muted)' }}>
                        <FileAudio size={18} />
                        <span style={{ fontSize: '0.85rem' }}>Audio attached ({rec.duration}s)</span>
                      </div>
                    )}
                    
                      <div className={styles.transcriptContainer}>
                        <span className={styles.transcriptLanguage}>
                          {supportedLanguages.find(l => l.id === rec.language)?.label || rec.language}
                        </span>
                        <p className={styles.transcriptText}>{rec.transcript}</p>
                      </div>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={threadEndRef} />
        </div>

        {/* Sticky Bottom Recording Bar */}
        <div className={styles.recordingBar} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className={styles.languageSelector}>
            {QUICK_LANGS.map(quickCode => {
              const lang = supportedLanguages.find(l => l.id === quickCode) || { id: quickCode, label: quickCode };
              return (
                <button
                  key={lang.id}
                  className={`${styles.langChip} ${selectedLang === lang.id ? styles.active : ''}`}
                  onClick={() => setSelectedLang(lang.id)}
                >
                  {lang.label}
                </button>
              );
            })}
            
            {supportedLanguages.length > QUICK_LANGS.length && (
              <div className={styles.dropdownContainer} ref={dropdownRef}>
                <button
                  className={`${styles.langChip} ${!QUICK_LANGS.includes(selectedLang) ? styles.active : ''}`}
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                >
                  {!QUICK_LANGS.includes(selectedLang) 
                    ? supportedLanguages.find(l => l.id === selectedLang)?.label || '+ More'
                    : '+ More'}
                </button>
                
                {isDropdownOpen && (
                  <div className={styles.dropdownMenu}>
                    {supportedLanguages
                      .filter(lang => !QUICK_LANGS.includes(lang.id))
                      .sort((a, b) => a.label.localeCompare(b.label))
                      .map(lang => (
                      <button
                        key={lang.id}
                        className={`${styles.dropdownItem} ${selectedLang === lang.id ? styles.active : ''}`}
                        onClick={() => {
                          setSelectedLang(lang.id);
                          setIsDropdownOpen(false);
                        }}
                      >
                        {lang.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
          
          <div style={{ 
            display: 'flex', 
            gap: '0.75rem', 
            alignItems: 'center', 
            width: '100%', 
            background: 'var(--surface)', 
            padding: '0.5rem', 
            borderRadius: '24px', 
            border: '1px solid var(--border)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.02)'
          }}>
            {inputMode === 'text' ? (
              <>
                <button 
                  onClick={() => setInputMode('audio')}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '0.5rem' }}
                  title="Switch to Audio"
                >
                  <FileAudio size={20} />
                </button>
                <input 
                  type="text" 
                  placeholder="Type manual transcription here..." 
                  value={manualText}
                  onChange={(e) => setManualText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleManualSubmit();
                  }}
                  style={{
                    flex: 1, 
                    padding: '0.6rem 0.5rem', 
                    border: 'none', 
                    background: 'transparent', 
                    color: 'var(--text)', 
                    outline: 'none',
                    fontSize: '0.95rem'
                  }}
                />
                <button 
                  onClick={handleManualSubmit}
                  disabled={!manualText.trim()}
                  style={{
                    padding: '0.6rem 1.2rem', 
                    borderRadius: '18px', 
                    border: 'none', 
                    background: 'var(--accent)', 
                    color: '#fff', 
                    fontWeight: 600, 
                    cursor: manualText.trim() ? 'pointer' : 'not-allowed',
                    opacity: manualText.trim() ? 1 : 0.5,
                    marginRight: '0.25rem',
                    transition: 'all 0.2s'
                  }}
                >
                  Send
                </button>
              </>
            ) : (
              <>
                <AudioRecorder 
                  onRecordingComplete={handleRecordingComplete}
                  onUploadFile={(file) => {
                    handleRecordingComplete(file, 0);
                  }}
                  onStateChange={(state) => setRecorderState(state)}
                  onSwitchToText={() => setInputMode('text')}
                />
                {recorderState === 'idle' && (
                  <div style={{ flex: 1, color: 'var(--muted)', fontSize: '0.95rem', paddingLeft: '0.5rem', display: 'flex', alignItems: 'center' }}>
                    Tap microphone to record...
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        
        {isOrderModalOpen && selectedHearing && (
          <OrderCreationModal 
            hearing={selectedHearing} 
            token={user?.token} 
            onClose={() => setIsOrderModalOpen(false)} 
            onOrderCreated={() => {
              setIsOrderModalOpen(false);
              alert('Order drafted successfully!');
            }}
          />
        )}

        {isEditHearingModalOpen && (
          <div className={styles.modalOverlay}>
            <div className={styles.modalContent}>
              <div className={styles.modalHeader}>
                <h3>Edit Hearing Details</h3>
              </div>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Hearing Date</label>
                  <CustomDatePicker
                    name="hearing_date"
                    value={editHearingData.hearing_date}
                    onChange={(e) => setEditHearingData(prev => ({ ...prev, hearing_date: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Scheduled Time</label>
                  <CustomTimePicker
                    name="scheduled_time"
                    value={editHearingData.scheduled_time}
                    onChange={e => setEditHearingData(prev => ({ ...prev, scheduled_time: e.target.value }))}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Hearing Type</label>
                  <CustomSelect
                    name="hearing_type"
                    value={editHearingData.hearing_type}
                    onChange={(e) => setEditHearingData(prev => ({ ...prev, hearing_type: e.target.value }))}
                    options={[
                      { value: 'initial', label: 'Initial Production' },
                      { value: 'followup', label: 'Follow-up' },
                      { value: 'final', label: 'Final Disposition' }
                    ]}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Status</label>
                  <CustomSelect
                    name="status"
                    value={editHearingData.status}
                    onChange={(e) => setEditHearingData(prev => ({ ...prev, status: e.target.value }))}
                    options={[
                      { value: 'scheduled', label: 'Scheduled' },
                      { value: 'in_progress', label: 'In Progress' },
                      { value: 'completed', label: 'Completed' },
                      { value: 'rescheduled', label: 'Rescheduled' },
                      { value: 'cancelled', label: 'Cancelled' }
                    ]}
                  />
                </div>
                {editHearingData.status === 'rescheduled' && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Reschedule Reason</label>
                    <input 
                      type="text" 
                      value={editHearingData.reschedule_reason} 
                      onChange={e => setEditHearingData(prev => ({ ...prev, reschedule_reason: e.target.value }))}
                      placeholder="Why was the hearing rescheduled?"
                      style={{ padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', color: 'var(--text)' }}
                    />
                  </div>
                )}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--muted)' }}>Attendees (CWC Members)</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', padding: '0.75rem', borderRadius: '6px', border: '1px solid var(--border)', background: 'var(--bg)', minHeight: '3rem' }}>
                    {cwcMembers.length > 0 ? cwcMembers.map(member => {
                      const isSelected = editHearingData.attendees.includes(member.id);
                      return (
                        <label key={member.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text)', background: isSelected ? 'var(--surface)' : 'transparent', padding: '6px 10px', borderRadius: '6px', border: '1px solid', borderColor: isSelected ? 'var(--accent)' : 'transparent' }}>
                          <input 
                            type="checkbox" 
                            checked={isSelected}
                            style={{ accentColor: 'var(--accent)' }}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setEditHearingData(prev => ({ ...prev, attendees: [...prev.attendees, member.id] }));
                              } else {
                                setEditHearingData(prev => ({ ...prev, attendees: prev.attendees.filter(id => id !== member.id) }));
                              }
                            }}
                          />
                          {member.full_name}
                        </label>
                      );
                    }) : <span style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No members found.</span>}
                  </div>
                </div>
              </div>

              <div className={styles.modalActions} style={{ marginTop: '1.5rem' }}>
                <button className={styles.btnCancel} onClick={() => setIsEditHearingModalOpen(false)}>Cancel</button>
                <button className={styles.btnSubmit} onClick={handleEditHearingSubmit}>Save Changes</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
