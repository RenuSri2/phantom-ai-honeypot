import { useRef, useEffect, useState } from 'react';
import { Terminal, Database, Code, Globe } from 'lucide-react';
import { useFirebaseListener } from '../hooks/useFirebaseListener';

const getIcon = (cmd='') => {
  const t = cmd.toLowerCase();
  if (t.includes('select')||t.includes('union')||t.includes('drop')) return <Database size={11} style={{ color:'var(--red)', flexShrink:0 }}/>;
  if (t.includes('<script')||t.includes('eval('))                    return <Code size={11} style={{ color:'var(--yellow)', flexShrink:0 }}/>;
  if (t.includes('ssh ')||t.includes('wget ')||t.includes('curl '))  return <Globe size={11} style={{ color:'var(--blue)', flexShrink:0 }}/>;
  return <Terminal size={11} style={{ color:'var(--green)', flexShrink:0 }}/>;
};

export default function LiveAttackFeed({ sessionId }) {
  const { data: cmdsObj } = useFirebaseListener(sessionId ? `sessions/${sessionId}/commands` : null);
  const ref = useRef(null);
  const [auto, setAuto] = useState(true);

  const cmds = cmdsObj ? Object.values(cmdsObj).sort((a,b) => a.timestamp - b.timestamp) : [];

  useEffect(() => {
    if (auto && ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [cmds, auto]);

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', overflow:'hidden', background:'var(--bg-1)' }}>
      <div className="panel-head">
        <Terminal size={14}/>
        <h2>Live Attack Feed</h2>
        <div className="ph-right">
          <span style={{ display:'flex', alignItems:'center', gap:5, fontSize:11,
            color: sessionId?'var(--green)':'var(--text-2)' }}>
            <span className={`dot ${sessionId?'dot-g pulse':''}`}/>
            {sessionId ? 'Listening' : 'Waiting'}
          </span>
          <button onClick={()=>setAuto(p=>!p)} className="btn" style={{
            padding:'1px 8px', fontSize:9,
            color: auto?'var(--green)':'var(--text-2)',
            background: auto?'var(--green-dim)':'transparent',
            border:`1px solid ${auto?'rgba(0,255,136,.2)':'var(--border)'}`,
          }}>AUTO</button>
        </div>
      </div>

      {/* This div is the scroll container — flex:1 + overflow:auto = scrollable */}
      <div
        ref={ref}
        onMouseEnter={()=>setAuto(false)}
        onMouseLeave={()=>setAuto(true)}
        style={{ flex:1, overflowY:'auto', overflowX:'hidden', minHeight:0 }}
      >
        {cmds.length===0
          ? <div className="feed-empty">No commands yet — launch a simulation</div>
          : <div className="feed-list">
              {cmds.map((c,i) => (
                <div key={i} className="feed-item">
                  <span className="feed-time">{new Date(c.timestamp).toLocaleTimeString([],{hour12:false})}</span>
                  {getIcon(c.raw_command)}
                  <span className="feed-cmd">{c.raw_command}</span>
                  {c.rl_action && <span className="feed-act">→ {c.rl_action}</span>}
                </div>
              ))}
            </div>
        }
      </div>
    </div>
  );
}
