import React, { useState, useEffect, useRef } from 'react';
import { Mic, Trash2, Send, X, Check, Paperclip, Keyboard } from 'lucide-react';
import CustomAudioPlayer from './CustomAudioPlayer';
import styles from './AudioRecorder.module.css';

const AudioRecorder = ({ onRecordingComplete, onUploadFile, onStateChange, onSwitchToText }) => {
  const [state, setState] = useState('idle'); // 'idle' | 'recording' | 'done'

  const updateState = (newState) => {
    setState(newState);
    if (onStateChange) onStateChange(newState);
  };
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const sourceRef = useRef(null);
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const streamRef = useRef(null);
  const amplitudeHistoryRef = useRef([]);
  const lastSampleTimeRef = useRef(0);

  const fileInputRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        updateState('done');
        cleanupStream();
      };
      
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      const audioCtx = new AudioContext();
      audioContextRef.current = audioCtx;
      
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;
      
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);
      sourceRef.current = source;
      
      amplitudeHistoryRef.current = [];
      
      mediaRecorder.start(100);
      updateState('recording');
      setRecordingTime(0);
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
      
    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  };

  const setupCanvas = () => {
    if (canvasRef.current) {
      const parent = canvasRef.current.parentElement;
      canvasRef.current.width = parent.clientWidth * 2;
      canvasRef.current.height = parent.clientHeight * 2;
    }
  };

  const drawRoundRect = (ctx, x, y, width, height, radius) => {
    if (width < 2 * radius) radius = width / 2;
    if (height < 2 * radius) radius = height / 2;
    ctx.beginPath();
    ctx.moveTo(x + radius, y);
    ctx.arcTo(x + width, y, x + width, y + height, radius);
    ctx.arcTo(x + width, y + height, x, y + height, radius);
    ctx.arcTo(x, y + height, x, y, radius);
    ctx.arcTo(x, y, x + width, y, radius);
    ctx.closePath();
    ctx.fill();
  };

  const drawWaveform = () => {
    if (!canvasRef.current || !analyserRef.current || state !== 'recording') return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const analyser = analyserRef.current;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
      const draw = () => {
      if (state !== 'recording') return;
      animationFrameRef.current = requestAnimationFrame(draw);
      
      const now = performance.now();
      if (now - lastSampleTimeRef.current > 100) {
        lastSampleTimeRef.current = now;
        
        analyser.getByteTimeDomainData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          const val = (dataArray[i] - 128) / 128;
          sum += val * val;
        }
        const rms = Math.sqrt(sum / bufferLength);
        const amplitude = Math.min(1, rms * 10);
        
        amplitudeHistoryRef.current.push(amplitude);
      }
      
      const width = canvas.width;
      const height = canvas.height;
      
      const barWidth = 6;
      const gap = 4;
      const totalBarWidth = barWidth + gap;
      const maxBars = Math.floor(width / totalBarWidth);
      
      if (amplitudeHistoryRef.current.length > maxBars) {
        amplitudeHistoryRef.current.shift();
      }
      
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = '#E4720C'; // Accent color for bars
      
      const history = amplitudeHistoryRef.current;
      for (let i = 0; i < history.length; i++) {
        const amp = history[i];
        const minH = barWidth;
        const maxH = height * 0.9;
        const h = Math.max(minH, amp * maxH);
        
        const x = i * totalBarWidth;
        const y = (height - h) / 2;
        
        drawRoundRect(ctx, x, y, barWidth, h, barWidth / 2);
      }
    };
    
    draw();
  };
  
  const stopRecording = (cancel = false) => {
    if (mediaRecorderRef.current && state === 'recording') {
      if (cancel) {
        mediaRecorderRef.current.onstop = cleanupAll;
        updateState('idle');
      }
      mediaRecorderRef.current.stop();
    }
  };

  const cleanupStream = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (animationFrameRef.current) cancelAnimationFrame(animationFrameRef.current);
    
    if (sourceRef.current) sourceRef.current.disconnect();
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close();
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    
    audioContextRef.current = null;
    analyserRef.current = null;
    sourceRef.current = null;
    mediaRecorderRef.current = null;
    streamRef.current = null;
  };

  const cleanupAll = () => {
    cleanupStream();
    updateState('idle');
    setRecordingTime(0);
    setAudioBlob(null);
    amplitudeHistoryRef.current = [];
  };
  
  useEffect(() => {
    return cleanupAll;
  }, []);
  
  useEffect(() => {
    if (state === 'recording' && canvasRef.current) {
      setupCanvas();
      drawWaveform();
    }
  }, [state]);
  
  useEffect(() => {
    const handleResize = () => {
      if (state === 'recording') {
        setupCanvas();
      }
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [state]);

  const formatTime = (timeInSeconds) => {
    const minutes = Math.floor(timeInSeconds / 60).toString().padStart(2, '0');
    const seconds = (timeInSeconds % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  const handleSend = () => {
    if (audioBlob && onRecordingComplete) {
      onRecordingComplete(audioBlob, recordingTime, amplitudeHistoryRef.current);
    }
    updateState('idle');
    setAudioBlob(null);
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      if (onUploadFile) {
        onUploadFile(e.target.files[0]);
      }
    }
  };

  if (state === 'idle') {
    return (
      <div className={`${styles.recorderContainer} ${styles.idle}`}>
        <div className={styles.idleContainer}>
          <button 
            className={styles.micButton} 
            onClick={startRecording}
            title="Start Recording"
          >
            <Mic size={20} color="#fff" />
          </button>
          <button 
            className={styles.uploadIconButton}
            onClick={() => fileInputRef.current?.click()}
            title="Upload Audio File"
          >
            <Paperclip size={18} />
          </button>
          {onSwitchToText && (
            <button 
              className={styles.uploadIconButton}
              onClick={onSwitchToText}
              title="Type manually"
            >
              <Keyboard size={18} />
            </button>
          )}
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept="audio/*" 
            style={{ display: 'none' }} 
          />
        </div>
      </div>
    );
  }

  if (state === 'recording') {
    return (
      <div className={styles.recorderContainer}>
        <div className={styles.recordingContainer}>
          <div className={styles.recordingStatus}>
            <div className={styles.pulsingDotWrapper}>
              <div className={styles.pulsingDot}></div>
              <span className={styles.timerText}>{formatTime(recordingTime)}</span>
            </div>
            <span className={styles.recordingHint}>Recording...</span>
          </div>
          
          <div className={styles.canvasContainer}>
            <canvas ref={canvasRef} className={styles.waveformCanvas}></canvas>
          </div>
          
          <div className={styles.recordingActions}>
            <button 
              className={styles.cancelIconBtn}
              onClick={() => stopRecording(true)}
              aria-label="Cancel recording"
            >
              <X size={24} />
            </button>
            <button 
              className={styles.stopButton}
              onClick={() => stopRecording(false)}
              aria-label="Stop recording"
            >
              <div className={styles.stopSquare}></div>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (state === 'done') {
    return (
      <div className={styles.recorderContainer}>
        <div className={styles.doneContainer}>
          <div className={styles.fileInfo}>
            <div className={styles.checkCircle}>
              <Check size={20} />
            </div>
            <div className={styles.fileDetails}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span className={styles.fileName}>New Recording</span>
                <span className={styles.fileDuration}>({formatTime(recordingTime)})</span>
              </div>
              <CustomAudioPlayer 
                audioUrl={audioBlob ? URL.createObjectURL(audioBlob) : ''} 
                amplitudeHistory={amplitudeHistoryRef.current} 
                explicitDuration={recordingTime}
              />
            </div>
          </div>
          
          <div className={styles.doneActions}>
            <button 
              className={styles.deleteButton}
              onClick={cleanupAll}
              aria-label="Delete recording"
            >
              <Trash2 size={20} />
            </button>
            <button 
              className={styles.sendButton}
              onClick={handleSend}
            >
              <Send size={16} /> Send
            </button>
          </div>
        </div>
      </div>
    );
  }

  return null;
};

export default AudioRecorder;
