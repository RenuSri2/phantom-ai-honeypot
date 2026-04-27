import { UserX, Wrench, ShieldAlert, Bot, User } from 'lucide-react';
import { useFirebaseListener } from '../hooks/useFirebaseListener';

const sc = s => s==='APT'?'var(--red)':s==='intermediate'?'var(--yellow)':s==='script_kiddie'?'var(--green)':'var(--text-2)';
const LVL = ['script_kiddie','intermediate','APT'];

export default function AttackerProfile({ sessionId }) {
  const { data } = useFirebaseListener(sessionId ? `sessions/${sessionId}/info` : null);
  const skill  = data?.skill_level    || 'unknown';
  const intent = data?.intent         || 'unknown';
  const tools  = data?.tools_detected || [];
  const mitre  = data?.mitre_tactics  || [];
  const isBot  = data?.session_type === 'SIMULATED';
  const idx    = LVL.indexOf(skill);

  return (
    <div className="panel">
      <div className="panel-head">
        <UserX size={14}/>
        <h2>Attacker Profile</h2>
        {sessionId && (
          <span className={`badge ${isBot?'badge-yellow':'badge-red'}`} style={{ marginLeft:'auto' }}>
            {isBot ? <><Bot size={10}/> BOT</> : <><User size={10}/> HUMAN</>}
          </span>
        )}
      </div>
      <div className="panel-body">

        <div className="p-row">
          <span className="p-lbl">Skill Level</span>
          <span className="p-val" style={{ color: sc(skill) }}>{skill.replace(/_/g,' ').toUpperCase()}</span>
        </div>
        <div className="skill-bar">
          {LVL.map((l,i) => (
            <div key={l} className="skill-seg" style={{ background: idx>=0&&i<=idx ? sc(skill) : undefined }}/>
          ))}
        </div>

        <div style={{ marginBottom:10 }}>
          <div className="p-lbl" style={{ marginBottom:5 }}>Primary Intent</div>
          <div style={{ display:'inline-flex', alignItems:'center', gap:6, padding:'5px 9px',
            background:'var(--bg-2)', border:'1px solid var(--border)', borderRadius:'var(--r)',
            color: intent!=='unknown'?'var(--red)':'var(--text-2)', fontSize:11, fontWeight:600, textTransform:'uppercase' }}>
            <ShieldAlert size={12}/>{intent.replace(/_/g,' ')}
          </div>
        </div>

        <div style={{ marginBottom:10 }}>
          <div className="p-lbl" style={{ display:'flex', alignItems:'center', gap:4, marginBottom:5 }}>
            <Wrench size={10}/> Tools
          </div>
          <div className="tag-list">
            {tools.length>0 ? tools.map((t,i)=><span key={i} className="tag tag-b">{t}</span>)
              : <span style={{ fontSize:10, color:'var(--text-2)' }}>None identified</span>}
          </div>
        </div>

        <div>
          <div className="p-lbl" style={{ marginBottom:5 }}>MITRE ATT&amp;CK</div>
          <div className="tag-list">
            {mitre.length>0 ? mitre.map((m,i)=><span key={i} className="tag tag-y">{m}</span>)
              : <span style={{ fontSize:10, color:'var(--text-2)' }}>Analyzing…</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
