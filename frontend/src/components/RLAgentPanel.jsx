import { BrainCircuit, CheckCircle, XCircle, AlertTriangle, Minus } from 'lucide-react';
import { useFirebaseListener } from '../hooks/useFirebaseListener';

const ac = a => !a?'var(--text-3)':a.includes('SERVE')?'var(--green)':a.includes('ERROR')||a.includes('DENY')?'var(--red)':a.includes('ALLOW')?'var(--yellow)':'var(--blue)';
const ai = a => {
  if (!a) return <Minus size={11}/>;
  if (a.includes('ERROR')||a.includes('DENY')) return <XCircle size={11}/>;
  if (a.includes('ALLOW')) return <AlertTriangle size={11}/>;
  return <CheckCircle size={11}/>;
};

export default function RLAgentPanel({ sessionId }) {
  const { data: cmdsObj } = useFirebaseListener(sessionId ? `sessions/${sessionId}/commands` : null);
  const { data: info }    = useFirebaseListener(sessionId ? `sessions/${sessionId}/info`     : null);

  const cmds   = cmdsObj ? Object.values(cmdsObj).sort((a,b) => b.timestamp - a.timestamp) : [];
  const withRL = cmds.filter(c => c.rl_action);
  const last   = withRL[0];
  const reward = info?.cumulative_reward ?? 0;
  const conf   = last?.rl_confidence != null ? `${Math.round(last.rl_confidence*100)}%` : '—';

  return (
    <div className="panel">
      <div className="panel-head">
        <BrainCircuit size={14}/>
        <h2>RL Deception Engine</h2>
        <span className={`badge ${sessionId?'badge-green':'badge-grey'}`} style={{ marginLeft:'auto' }}>
          {sessionId ? '● ACTIVE' : '○ IDLE'}
        </span>
      </div>
      <div className="panel-body" style={{ display:'flex', flexDirection:'column', gap:8, overflow:'hidden' }}>

        {/* Stats */}
        <div className="stat-grid">
          <div className="stat-card">
            <div className="lbl">Reward</div>
            <div className="val" style={{ color:'var(--blue)' }}>+{reward}</div>
          </div>
          <div className="stat-card">
            <div className="lbl">Confidence</div>
            <div className="val" style={{ color:'var(--green)' }}>{conf}</div>
          </div>
        </div>

        {/* Latest action */}
        <div className="rl-box" style={{ borderColor: ac(last?.rl_action) }}>
          <span style={{ color: ac(last?.rl_action), display:'flex', alignItems:'center' }}>{ai(last?.rl_action)}</span>
          <span style={{ color: ac(last?.rl_action), fontSize:12, fontFamily:'var(--mono)', fontWeight:600 }}>
            {last?.rl_action || 'WAITING FOR COMMANDS…'}
          </span>
          {last?.rl_reward != null &&
            <span style={{ marginLeft:'auto', fontSize:10, color:'var(--text-2)', fontFamily:'var(--mono)' }}>+{last.rl_reward} pts</span>}
        </div>

        {/* Confidence bar */}
        {last?.rl_confidence != null && (
          <div>
            <div style={{ height:3, background:'var(--bg-3)', borderRadius:2, overflow:'hidden' }}>
              <div style={{ height:'100%', width:`${last.rl_confidence*100}%`,
                background:'var(--green)', transition:'width 0.4s ease',
                boxShadow:'0 0 6px var(--green)' }}/>
            </div>
          </div>
        )}

        {/* Recent decisions */}
        <div>
          <div style={{ fontSize:9, color:'var(--text-2)', textTransform:'uppercase', letterSpacing:'0.8px', marginBottom:5 }}>
            Recent Decisions ({withRL.length})
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:3, overflowY:'auto', maxHeight:120 }}>
            {withRL.length === 0
              ? <div style={{ fontSize:11, color:'var(--text-2)' }}>
                  {cmds.length > 0 ? 'Commands logged — RL decisions pending from layer3' : 'No data yet'}
                </div>
              : withRL.slice(0,8).map((c,i) => (
                  <div key={i} className="rl-row" style={{ borderLeftColor: ac(c.rl_action), opacity: Math.max(0.3, 1-i*0.1) }}>
                    <span style={{ color: ac(c.rl_action), fontWeight:600, fontSize:10 }}>{c.rl_action}</span>
                    <span style={{ color:'var(--text-3)', fontSize:9, marginLeft:6 }}>
                      {new Date(c.timestamp).toLocaleTimeString([],{hour12:false})}
                    </span>
                    <span style={{ marginLeft:'auto', color:'var(--text-2)', fontSize:10 }}>
                      {c.rl_reward!=null ? `+${c.rl_reward}` : ''}
                    </span>
                  </div>
                ))
            }
          </div>
        </div>
      </div>
    </div>
  );
}
