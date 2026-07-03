import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { Navigate } from 'react-router-dom';
import CustomAudioPlayer from '../components/recorder/CustomAudioPlayer';
import { Loader2, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import { formatRole } from '../utils/formatters';

const TranscriptCell = ({ transcript }) => {
  const [expanded, setExpanded] = useState(false);
  const [showButton, setShowButton] = useState(false);
  const textRef = useRef(null);
  
  useEffect(() => {
    if (textRef.current) {
      // If the true scroll height is greater than the 3-line clamped height, it needs the button
      if (textRef.current.scrollHeight > textRef.current.clientHeight) {
        setShowButton(true);
      }
    }
  }, [transcript]);
  
  if (!transcript) {
    return <span style={{ color: '#A79D8F', fontStyle: 'italic' }}>Pending or no final transcript</span>;
  }
  
  return (
    <div className="transcript-cell-wrapper" style={{ maxWidth: '400px' }}>
      <div ref={textRef} style={{
        display: '-webkit-box',
        WebkitLineClamp: expanded ? 'unset' : 3,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
        lineHeight: '1.5',
        wordBreak: 'break-word',
        whiteSpace: 'pre-wrap'
      }}>
        {transcript}
      </div>
      {showButton && (
        <button 
          onClick={() => setExpanded(!expanded)}
          style={{
            background: 'none', border: 'none', color: '#D49A44', cursor: 'pointer', 
            padding: '4px 0', fontSize: '0.8rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px'
          }}
        >
          {expanded ? <><ChevronUp size={14}/> Show less</> : <><ChevronDown size={14}/> Show more</>}
        </button>
      )}
    </div>
  );
};

export default function TranscriptionLogs() {
  const { user } = useAuth();
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const response = await axios.get('/api/transcriptions');
        setLogs(response.data);
      } catch (error) {
        console.error("Error fetching transcription logs:", error);
      } finally {
        setLoading(false);
      }
    };
    if (user?.role === 'system_admin') {
      fetchLogs();
    }
  }, [user]);

  const handleDelete = async (jobId) => {
    if (!window.confirm("Are you sure you want to permanently delete this transcription and its audio file?")) return;
    try {
      await axios.delete(`/api/transcriptions/${jobId}`);
      setLogs(prev => prev.filter(log => log.job_id !== jobId));
    } catch (err) {
      console.error("Failed to delete log:", err);
      alert("Failed to delete the transcription log.");
    }
  };

  if (user?.role !== 'system_admin') {
    return <Navigate to="/" replace />;
  }

  return (
    <div style={{ padding: '16px', maxWidth: '1200px', margin: '0 auto', width: '100%', boxSizing: 'border-box' }}>
      <style>{`
        .logs-table { width: 100%; border-collapse: collapse; text-align: left; }
        .logs-table th { padding: 16px; font-weight: 600; color: #685D4D; border-bottom: 1px solid #EEE6D8; background: #FBF8F2; }
        .logs-table td { padding: 16px; vertical-align: top; border-bottom: 1px solid #EEE6D8; }
        
        @media (max-width: 768px) {
          .table-container { border: none !important; background: transparent !important; border-radius: 0 !important; }
          .logs-table, .logs-table tbody, .logs-table tr, .logs-table td { display: block; width: 100%; box-sizing: border-box; }
          .logs-table thead { display: none; }
          .logs-table tr {
            margin-bottom: 16px;
            border: 1px solid #EEE6D8;
            border-radius: 12px;
            background: #fff;
            padding: 8px 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.02);
          }
          .logs-table td {
            padding: 12px 0;
            border-bottom: 1px solid #f5f0e6;
            display: flex;
            flex-direction: column;
          }
          .logs-table td:last-child { border-bottom: none; }
          .logs-table td::before {
            content: attr(data-label);
            font-weight: 600;
            color: #A79D8F;
            font-size: 0.75rem;
            text-transform: uppercase;
            margin-bottom: 6px;
            letter-spacing: 0.5px;
          }
          .audio-cell-wrapper { width: 100% !important; min-width: 100% !important; }
          .transcript-cell-wrapper { max-width: 100% !important; width: 100%; }
        }
      `}</style>
      
      <h2 style={{ marginBottom: '8px', fontSize: '1.5rem', fontWeight: 600 }}>Transcription Logs</h2>
      <p style={{ color: '#A79D8F', marginBottom: '24px' }}>Monitor all system-wide transcription jobs</p>

      {loading ? (
        <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', color: 'var(--muted)' }}>
          <Loader2 style={{ animation: 'spin 1s linear infinite', color: 'var(--accent)' }} size={32} />
          <p>Loading logs...</p>
        </div>
      ) : (
        <div className="table-container" style={{ overflowX: 'auto', background: '#fff', borderRadius: '12px', border: '1px solid #EEE6D8' }}>
          <table className="logs-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Person</th>
                <th>Hearing</th>
                <th>Audio</th>
                <th style={{ width: '40%' }}>Transcription</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => {
                const personName = log.full_name 
                  ? log.full_name 
                  : log.username 
                    ? log.username 
                    : log.role === 'sys_admin' || log.role === 'admin'
                      ? 'System Admin'
                      : (log.user_id && log.user_id.length > 20) 
                        ? 'Unknown User' 
                        : log.user_id;
                
                const parts = log.audio_path ? log.audio_path.split(/[/\\]/) : [];
                const fileName = parts.length > 0 ? parts.pop() : '';
                const audioUrl = fileName ? `/audio/${fileName}` : null;

                  return (
                    <tr key={log.job_id}>
                      <td data-label="Time" style={{ color: '#685D4D' }}>
                        {log.created_at ? new Date(log.created_at.replace('Z', '')).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', month: 'short', day: 'numeric', hour: 'numeric', minute: 'numeric', hour12: true }) : '-'}
                      </td>
                      <td data-label="Person">
                        <div style={{ fontWeight: 500, color: '#2C2822' }}>{personName}</div>
                        <div style={{ fontSize: '0.85rem', color: '#A79D8F' }}>
                          {formatRole(log.role)}
                        </div>
                      </td>
                      <td data-label="Hearing">
                        <div style={{ fontWeight: 500, color: '#2C2822' }}>{log.child_name || log.hearing_id || '-'}</div>
                        {log.child_code && <div style={{ fontSize: '0.85rem', color: '#A79D8F' }}>{log.child_code}</div>}
                      </td>
                      <td data-label="Audio" className="audio-cell-wrapper" style={{ width: '250px' }}>
                        <CustomAudioPlayer 
                          audioUrl={log.audio_path ? `/api/audio/${log.audio_path.split(/[/\\]/).pop()}` : null} 
                          explicitDuration={0} 
                          amplitudeHistory={[]} 
                        />
                      </td>
                      <td data-label="Transcription">
                        <div style={{ display: 'inline-block', padding: '4px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, marginBottom: '8px',
                          background: log.status === 'completed' ? '#E9F5EC' : log.status === 'failed' || log.status === 'error' ? '#FBEAE9' : '#FFF4E6',
                          color: log.status === 'completed' ? '#2E603E' : log.status === 'failed' || log.status === 'error' ? '#D93A36' : '#E4720C'
                         }}>
                          {log.status.toUpperCase()}
                        </div>
                        <div style={{ marginTop: '4px', color: '#4A433A' }}>
                          <TranscriptCell transcript={log.final_transcript} />
                        </div>
                        <button 
                          onClick={() => handleDelete(log.job_id)}
                          style={{ marginTop: '16px', background: 'transparent', border: 'none', color: '#D93A36', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', padding: '4px 0', opacity: 0.8 }}
                          onMouseOver={(e) => e.target.style.opacity = 1}
                          onMouseOut={(e) => e.target.style.opacity = 0.8}
                        >
                          <Trash2 size={14} /> Delete
                        </button>
                      </td>
                    </tr>
                  );
              })}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: '#A79D8F' }}>
                    No transcription logs found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
