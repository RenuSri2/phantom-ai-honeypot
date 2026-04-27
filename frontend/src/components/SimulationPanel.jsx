import { useState, useEffect } from 'react';
import { Play, Target, Loader } from 'lucide-react';

const SCENARIOS = [
  { value: 'sql_injection',  label: 'SQL Injection' },
  { value: 'ssh_brute',      label: 'SSH Brute Force' },
  { value: 'directory_enum', label: 'Directory Enumeration' },
  { value: 'privilege_esc',  label: 'Privilege Escalation' },
  { value: 'data_theft',     label: 'Data Exfiltration' },
];

export default function SimulationPanel({ onSessionStart, sessionId }) {
  const [type,    setType]    = useState('sql_injection');
  const [diff,    setDiff]    = useState(5);
  const [ip,      setIp]      = useState('192.168.1.100');
  const [running, setRunning] = useState(false);
  const [timeLeft,setTimeLeft]= useState(0);

  useEffect(() => {
    if (timeLeft > 0 && running) {
      const t = setTimeout(() => setTimeLeft(p => p - 1), 1000);
      return () => clearTimeout(t);
    }
    if (timeLeft === 0 && running) setRunning(false);
  }, [timeLeft, running]);

  const launch = async () => {
    setRunning(true); setTimeLeft(60);
    try {
      const res = await fetch(`${import.meta.env.VITE_LAYER1_URL||'http://localhost:8080'}/api/simulate-attack`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attack_type: type, difficulty: +diff, attacker_ip: ip, num_commands: 15, duration_seconds: 60 }),
      });
      const d = await res.json();
      if (d.session_id) onSessionStart(d.session_id);
    } catch(e) { alert('Launch failed: ' + e.message); setRunning(false); setTimeLeft(0); }
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <Target size={14} />
        <h2>Attack Simulation</h2>
        {running && <span className="badge badge-red" style={{ marginLeft: 'auto' }}>● LIVE</span>}
      </div>
      <div className="panel-body">
        <div className="field">
          <label>Scenario</label>
          <select value={type} onChange={e => setType(e.target.value)} disabled={running}>
            {SCENARIOS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div className="field">
          <label>Difficulty — {diff}/10</label>
          <input type="range" min="1" max="10" value={diff} onChange={e => setDiff(e.target.value)} disabled={running} />
        </div>
        <div className="field">
          <label>Attacker IP</label>
          <input type="text" value={ip} onChange={e => setIp(e.target.value)} disabled={running} />
        </div>

        {running && (
          <div style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 9, color: 'var(--text-2)', textTransform: 'uppercase' }}>Progress</span>
              <span style={{ fontSize: 9, fontFamily: 'var(--mono)', color: 'var(--text-2)' }}>{timeLeft}s</span>
            </div>
            <div style={{ height: 3, background: 'var(--bg-3)', borderRadius: 2, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${(timeLeft/60)*100}%`, background: 'var(--red)', transition: 'width 1s linear' }} />
            </div>
          </div>
        )}

        <button className="btn btn-green btn-full" onClick={launch} disabled={running}>
          {running
            ? <><Loader size={13} className="spin"/> Simulating… ({timeLeft}s)</>
            : <><Play size={13}/> Launch Demo</>}
        </button>

        {sessionId && (
          <div style={{ marginTop: 10, padding: '6px 8px', background: 'var(--bg-2)',
            borderRadius: 'var(--r)', border: '1px solid var(--border)' }}>
            <div style={{ fontSize: 9, color: 'var(--text-2)', textTransform: 'uppercase', marginBottom: 2 }}>Active Session</div>
            <div style={{ fontSize: 11, fontFamily: 'var(--mono)', color: 'var(--blue)' }}>{sessionId}</div>
          </div>
        )}
      </div>
    </div>
  );
}
