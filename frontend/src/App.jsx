import { useState, useEffect } from 'react';
import { Shield, FileText, Activity } from 'lucide-react';
import SimulationPanel   from './components/SimulationPanel';
import LiveAttackFeed    from './components/LiveAttackFeed';
import ThreatScoreMeter  from './components/ThreatScoreMeter';
import WorldMap          from './components/WorldMap';
import RLAgentPanel      from './components/RLAgentPanel';
import AttackerProfile   from './components/AttackerProfile';
import './App.css';

export default function App() {
  const [sessionId,  setSessionId]  = useState(null);
  const [reportUrl,  setReportUrl]  = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => { setReportUrl(null); }, [sessionId]);

  const handleReport = async () => {
    if (!sessionId) return;
    setGenerating(true);
    try {
      const base = import.meta.env.VITE_LAYER5_URL || 'http://localhost:8084';
      const res  = await fetch(`${base}/api/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId }),
      });
      const data = await res.json();
      if (data.pdf_url) setReportUrl(data.pdf_url);
      else alert('No PDF URL: ' + JSON.stringify(data));
    } catch (e) { alert('Report failed: ' + e.message); }
    finally     { setGenerating(false); }
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-logo">
          <Shield size={20} style={{ color: 'var(--green)' }} />
          <h1>PHANTOM <span>AI</span></h1>
          <span className="topbar-badge">HONEYPOT DECEPTION SYSTEM</span>
        </div>
        <div className="topbar-right">
          {sessionId && (
            <div className="session-pill">
              <span className="dot dot-g pulse" />
              <b>{sessionId}</b>
            </div>
          )}
          {reportUrl
            ? <a href={reportUrl} target="_blank" rel="noreferrer" className="btn btn-green"><FileText size={14}/> Download PDF</a>
            : <button className="btn btn-green" onClick={handleReport} disabled={!sessionId||generating}>
                {generating ? <><Activity size={14} className="spin"/> Generating…</> : <><FileText size={14}/> Generate Report</>}
              </button>
          }
        </div>
      </header>

      <div className="main">
        {/* LEFT col: Map top, Feed bottom */}
        <div style={{ display:'flex', flexDirection:'column', overflow:'hidden', gap:1, background:'var(--border)' }}>
          <div style={{ flex:1, overflow:'hidden' }}><WorldMap sessionId={sessionId} /></div>
          <div style={{ flex:1, overflow:'hidden' }}><LiveAttackFeed sessionId={sessionId} /></div>
        </div>

        {/* RIGHT col: 2x2 grid */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gridTemplateRows:'1fr 1fr', gap:1, background:'var(--border)', overflow:'hidden' }}>
          <SimulationPanel  onSessionStart={setSessionId} sessionId={sessionId} />
          <ThreatScoreMeter sessionId={sessionId} />
          <RLAgentPanel     sessionId={sessionId} />
          <AttackerProfile  sessionId={sessionId} />
        </div>
      </div>
    </div>
  );
}
