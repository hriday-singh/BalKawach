import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, Calendar, Clock, ChevronRight, FileAudio, Loader2 } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import AudioRecorder from '../components/recorder/AudioRecorder';
import CustomAudioPlayer from '../components/recorder/CustomAudioPlayer';
import styles from './Hearings.module.css';

const INITIAL_MOCK_RECORDINGS = [
  {
    id: 'r1',
    user: { id: 'u1', full_name: 'Deepak Joshi', role: 'cwc_chairperson' },
    timestamp: '2026-07-01T10:32:00Z',
    language: 'hi',
    transcript: 'बच्चा 14 दिन पहले चारमीनार के पास मिला था। पुलिस ने बच्चे को CWC के सामने पेश किया। बच्चे की उम्र लगभग 4 साल है।',
    audioUrl: 'https://actions.google.com/sounds/v1/water/water_drop.ogg', // Dummy mock audio
    duration: 45,
  },
  {
    id: 'r2',
    user: { id: 'u2', full_name: 'Priya Sharma', role: 'cwc_member' },
    timestamp: '2026-07-01T10:35:00Z',
    language: 'hi',
    transcript: 'सोशल इन्वेस्टिगेशन रिपोर्ट अभी तक नहीं आई है। DCPU से रिपोर्ट मांगी जाए।',
    audioUrl: 'https://actions.google.com/sounds/v1/water/water_drop.ogg',
    duration: 28,
  },
  {
    id: 'r3',
    user: { id: 'u1', full_name: 'Deepak Joshi', role: 'cwc_chairperson' },
    timestamp: '2026-07-01T10:38:00Z',
    language: 'hi',
    transcript: 'CWC का आदेश: बच्चे को शिशु विहार CCI में रखा जाए। 30 दिन में जांच रिपोर्ट पेश की जाए।',
    audioUrl: 'https://actions.google.com/sounds/v1/water/water_drop.ogg',
    duration: 32,
  },
];

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
  const [newHearingChildId, setNewHearingChildId] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [selectedLang, setSelectedLang] = useState('hi');
  const [supportedLanguages, setSupportedLanguages] = useState([
    { id: 'hi', label: 'Hindi' },
    { id: 'te', label: 'Telugu' },
    { id: 'en', label: 'English' }
  ]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  
  const QUICK_LANGS = ['hi', 'te', 'en'];
  
  const threadEndRef = useRef(null);
  const dropdownRef = useRef(null);
  const childDropdownRef = useRef(null);
  const [childSearchQuery, setChildSearchQuery] = useState('');
  const [isChildDropdownOpen, setIsChildDropdownOpen] = useState(false);

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
          setSupportedLanguages(langArray);
        }
      } catch (err) {
        console.error("Error fetching languages:", err);
      }
    };
    fetchHearings();
    fetchLanguages();
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
    if (!newHearingChildId) return;

    // Check if hearing already exists for this child
    const existingHearing = hearings.find(h => h.child_id === newHearingChildId || h.child_id == newHearingChildId);
    if (existingHearing) {
      setIsAddModalOpen(false);
      setNewHearingChildId('');
      setChildSearchQuery('');
      setSearchParams({ hearingId: existingHearing.id });
      return;
    }

    setIsCreating(true);
    try {
      const res = await axios.post('/api/hearings', { child_id: newHearingChildId, district: user?.district || 'Unknown' });
      const newHearings = await axios.get('/api/hearings');
      setHearings(newHearings.data);
      setIsAddModalOpen(false);
      setNewHearingChildId('');
      setChildSearchQuery('');
      setSearchParams({ hearingId: res.data.id });
    } catch (e) {
      console.error(e);
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
                <span><Calendar size={14} /> {hearing.hearing_date}</span>
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
                      if (newHearingChildId) setNewHearingChildId('');
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
                          return filtered.map(c => (
                            <div 
                              key={c.id} 
                              className={`${styles.comboboxItem} ${newHearingChildId === c.id ? styles.selected : ''}`}
                              onClick={() => {
                                setNewHearingChildId(c.id);
                                setChildSearchQuery(`${c.name} (${c.child_code})`);
                                setIsChildDropdownOpen(false);
                              }}
                            >
                              <span className={styles.comboboxItemName}>{c.name}</span>
                              <span className={styles.comboboxItemCode}>{c.child_code}</span>
                            </div>
                          ));
                        } else {
                          return <div className={styles.comboboxEmpty}>No children found</div>;
                        }
                      })()}
                    </div>
                  )}
                </div>

                <div className={styles.modalActions}>
                  <button 
                    className={styles.btnCancel} 
                    onClick={() => { 
                      setIsAddModalOpen(false); 
                      setNewHearingChildId(''); 
                      setChildSearchQuery(''); 
                    }}
                    disabled={isCreating}
                  >
                    Cancel
                  </button>
                  <button 
                    className={styles.btnSubmit}
                    onClick={handleCreateHearing}
                    disabled={!newHearingChildId || isCreating}
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
              {selectedHearing?.hearing_date} • {selectedHearing?.scheduled_time || "TBD"}
            </span>
          </div>
          <span className={`${styles.statusBadge} ${styles[selectedHearing?.status]}`}>
            {formatStatus(selectedHearing?.status)}
          </span>
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
        <div className={styles.recordingBar}>
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
          
          <AudioRecorder 
            onRecordingComplete={handleRecordingComplete}
            onUploadFile={(file) => {
              // Mock file upload
              handleRecordingComplete(file, 0);
            }}
          />
        </div>
      </div>
    </div>
  );
}
