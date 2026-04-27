import { Activity } from 'lucide-react';
import { useFirebaseListener } from '../hooks/useFirebaseListener';

export default function ThreatScoreMeter({ sessionId }) {
  const { data } = useFirebaseListener(sessionId ? `sessions/${sessionId}/info` : null);
  const score = data?.threat_score ?? 0;
  const r = 48; const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 70 ? 'var(--red)' : score >= 40 ? 'var(--yellow)' : 'var(--green)';
  const label = score >= 70 ? 'Critical' : score >= 40 ? 'Elevated' : 'Low Risk';

  return (
    <div className="panel">
      <div className="panel-head">
        <Activity size={14} />
        <h2>Threat Score</h2>
        <span className={`badge ${score>=70?'badge-red':score>=40?'badge-yellow':'badge-green'}`} style={{ marginLeft: 'auto' }}>
          {label}
        </span>
      </div>
      <div className="panel-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
        <div className="gauge-wrap">
          <div style={{ position: 'relative', width: 110, height: 110 }}>
            <svg width="110" height="110" style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="55" cy="55" r={r} fill="none" stroke="var(--bg-3)" strokeWidth="9"/>
              <circle cx="55" cy="55" r={r} fill="none" stroke={color} strokeWidth="9"
                strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
                style={{ transition: 'all 0.6s ease', filter: `drop-shadow(0 0 6px ${color})` }}/>
            </svg>
            <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: 30, fontWeight: 700, lineHeight: 1, color, fontFamily: 'var(--mono)' }}>{score}</span>
              <span style={{ fontSize: 10, color: 'var(--text-2)' }}>/100</span>
            </div>
          </div>
        </div>

        <div className="stat-grid" style={{ width: '100%' }}>
          {[
            ['Commands', data?.command_count ?? '—'],
            ['Reward',   `+${data?.cumulative_reward ?? 0}`],
            ['Type',     data?.session_type ?? '—'],
            ['Status',   data?.status ?? '—'],
          ].map(([l, v]) => (
            <div className="stat-card" key={l}>
              <div className="lbl">{l}</div>
              <div className="val" style={{ fontSize: 13, color }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
