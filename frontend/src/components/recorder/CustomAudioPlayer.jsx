import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause } from 'lucide-react';
import styles from './CustomAudioPlayer.module.css';

const CustomAudioPlayer = ({ audioUrl, amplitudeHistory = [], explicitDuration = null }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0); // 0 to 1
  const [duration, setDuration] = useState(explicitDuration || 0);
  const durationRef = useRef(explicitDuration || 0);
  const [currentTime, setCurrentTime] = useState(0);
  const [realWaveform, setRealWaveform] = useState(amplitudeHistory || []);
  
  const audioRef = useRef(null);
  const canvasRef = useRef(null);
  const requestRef = useRef();

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const updateProgress = () => {
      if (!audio) return;
      const activeDuration = (audio.duration && audio.duration !== Infinity && !isNaN(audio.duration)) ? audio.duration : durationRef.current;
      if (activeDuration > 0) {
        setProgress(audio.currentTime / activeDuration);
        setCurrentTime(audio.currentTime);
      }
    };
    
    const updateProgressSmoothly = () => {
      updateProgress();
      if (!audio.paused) {
        requestRef.current = requestAnimationFrame(updateProgressSmoothly);
      }
    };
    
    const handleLoadedMetadata = () => {
      if (audio.duration && audio.duration !== Infinity && !isNaN(audio.duration)) {
        setDuration(audio.duration);
        durationRef.current = audio.duration;
      } else if (explicitDuration) {
        setDuration(explicitDuration);
        durationRef.current = explicitDuration;
      }
    };
    
    if (audio.readyState >= 1) {
      handleLoadedMetadata();
    }
    
    const handleEnded = () => {
      setProgress(0);
      setCurrentTime(0);
    };

    const handlePlay = () => {
      setIsPlaying(true);
      requestRef.current = requestAnimationFrame(updateProgressSmoothly);
    };
    const handlePause = () => {
      setIsPlaying(false);
      cancelAnimationFrame(requestRef.current);
      updateProgress();
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('durationchange', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);

    return () => {
      cancelAnimationFrame(requestRef.current);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('durationchange', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
    };
  }, []);
  
  // Fetch and decode audio to get exact duration and generate waveform
  useEffect(() => {
    if (!audioUrl) return;
    let isSubscribed = true;
    
    const fetchAndDecode = async () => {
      try {
        const response = await fetch(audioUrl);
        const arrayBuffer = await response.arrayBuffer();
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
        
        if (!isSubscribed) return;
        
        if (audioBuffer.duration && !isNaN(audioBuffer.duration)) {
          setDuration(audioBuffer.duration);
          durationRef.current = audioBuffer.duration;
        }
        
        const channelData = audioBuffer.getChannelData(0);
        const samples = 100;
        const step = Math.ceil(channelData.length / samples);
        const waveform = [];
        
        for (let i = 0; i < samples; i++) {
          let max = 0;
          for (let j = 0; j < step; j++) {
            const idx = (i * step) + j;
            if (idx < channelData.length) {
              const val = Math.abs(channelData[idx]);
              if (val > max) max = val;
            }
          }
          waveform.push(max);
        }
        
        const maxAmp = Math.max(...waveform);
        const normalized = waveform.map(v => (maxAmp > 0 ? Math.max(0.1, v / maxAmp) : 0.1));
        setRealWaveform(normalized);
      } catch (err) {
        console.error("Error decoding audio for waveform:", err);
        // Fallback to amplitudeHistory if fetch/decode fails (e.g. some CORS issue)
        if (amplitudeHistory && amplitudeHistory.length > 0) {
          setRealWaveform(amplitudeHistory);
        }
      }
    };
    
    fetchAndDecode();
    return () => { isSubscribed = false; };
  }, [audioUrl, amplitudeHistory]);

  useEffect(() => {
    drawWaveform();
  }, [progress, realWaveform]);

  const drawWaveform = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);

    const barWidth = 3;
    const gap = 2;
    const totalBarWidth = barWidth + gap;
    const maxBars = Math.floor(width / totalBarWidth);
    
    // Generate a pseudo-random history if empty to make it look like a real waveform for mocks.
    const history = (realWaveform && realWaveform.length > 0) 
       ? realWaveform 
       : Array.from({length: maxBars}, (_, i) => Math.abs(Math.sin(i * 0.4)) * 0.6 + 0.1);
    
    const step = history.length > maxBars ? history.length / maxBars : 1;
    
    for (let i = 0; i < maxBars; i++) {
      const idx = Math.floor(i * step);
      const amp = history[idx] || 0.05;
      const minH = barWidth;
      const maxH = height * 0.9;
      const h = Math.max(minH, amp * maxH);
      
      const x = i * totalBarWidth;
      const y = (height - h) / 2;
      
      // Calculate if this bar is before or after progress tracker
      const barProgress = i / maxBars;
      ctx.fillStyle = barProgress <= progress ? '#E4720C' : '#D4C9B8';
      
      // Draw rounded rect
      ctx.beginPath();
      let r = barWidth / 2;
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + barWidth, y, x + barWidth, y + h, r);
      ctx.arcTo(x + barWidth, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + barWidth, y, r);
      ctx.closePath();
      ctx.fill();
    }
    
    // Draw tracker line
    const trackerX = progress * width;
    ctx.fillStyle = '#C24A3A';
    ctx.fillRect(trackerX - 1, 0, 2, height);
  };

  const togglePlay = () => {
    if (audioRef.current) {
      if (audioRef.current.paused) {
        // Pause all other audio elements on the page
        document.querySelectorAll('audio').forEach(el => {
          if (el !== audioRef.current && !el.paused) {
            el.pause();
          }
        });
        audioRef.current.play().catch(e => console.error('Playback error:', e));
      } else {
        audioRef.current.pause();
      }
    }
  };
  
  const handleCanvasClick = (e) => {
    const activeDuration = (audioRef.current.duration && audioRef.current.duration !== Infinity && !isNaN(audioRef.current.duration)) 
      ? audioRef.current.duration 
      : (durationRef.current || explicitDuration);
      
    if (!audioRef.current || !activeDuration) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const newProgress = Math.max(0, Math.min(1, clickX / rect.width));
    
    // Some browsers need a slight delay or try/catch for setting currentTime on streamed audio
    try {
      audioRef.current.currentTime = newProgress * activeDuration;
    } catch (err) {
      console.warn("Could not set currentTime", err);
    }
    
    setProgress(newProgress);
    setCurrentTime(newProgress * activeDuration);
  };

  const formatTime = (time) => {
    if (isNaN(time) || !isFinite(time)) return "0:00";
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  return (
    <div className={styles.container}>
      <button className={styles.playButton} onClick={togglePlay}>
        {isPlaying ? <Pause size={14} /> : <Play size={14} style={{marginLeft: '2px'}} />}
      </button>
      
      <div className={styles.waveformContainer} style={{ position: 'relative' }}>
        <canvas 
          ref={canvasRef} 
          width={120} 
          height={32} 
          className={styles.canvas}
          style={{ pointerEvents: 'none' }}
        />
        <input 
          type="range" 
          min="0" 
          max="1" 
          step="0.01"
          value={progress || 0}
          onChange={(e) => {
            const newProgress = parseFloat(e.target.value);
            const activeDuration = (audioRef.current?.duration && audioRef.current?.duration !== Infinity && !isNaN(audioRef.current?.duration)) 
              ? audioRef.current.duration 
              : (durationRef.current || explicitDuration);
            
            if (audioRef.current && activeDuration) {
              try {
                audioRef.current.currentTime = newProgress * activeDuration;
              } catch (err) {}
            }
            setProgress(newProgress);
            setCurrentTime(newProgress * activeDuration);
          }}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            opacity: 0,
            cursor: 'pointer',
            margin: 0
          }}
        />
      </div>
      
      <span className={styles.timeLabel}>
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
      
      <audio ref={audioRef} src={audioUrl} preload="metadata" style={{display: 'none'}} />
    </div>
  );
};

export default CustomAudioPlayer;
