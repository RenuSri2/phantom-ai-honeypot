import { useEffect } from 'react';
import { Globe, MapPin } from 'lucide-react';
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet';
import { useFirebaseListener } from '../hooks/useFirebaseListener';

function Recenter({ pos }) {
  const map = useMap();
  useEffect(() => {
    if (pos[0] !== 20 || pos[1] !== 0) map.setView(pos, 4, { animate: true });
  }, [pos, map]);
  return null;
}

export default function WorldMap({ sessionId }) {
  const { data } = useFirebaseListener(sessionId ? `sessions/${sessionId}/info` : null);
  const geo   = data?.geo || {};
  const pos   = [geo.lat || 20, geo.lon || 0];
  const valid = !!(geo.lat && geo.lon);

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', background:'var(--bg-1)' }}>
      <div className="panel-head">
        <Globe size={14}/>
        <h2>Attack Origin Map</h2>
        {valid && (
          <span style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:5,
            fontSize:11, color:'var(--red)', fontFamily:'var(--mono)' }}>
            <MapPin size={11}/>{geo.city}, {geo.country}
          </span>
        )}
      </div>

      {valid && (
        <div style={{ padding:'7px 14px', background:'var(--bg-2)', borderBottom:'1px solid var(--border)',
          display:'flex', gap:24, flexShrink:0 }}>
          {[['IP', data?.attacker_ip],['Country',geo.country],['City',geo.city],['ISP',geo.isp]].map(([l,v])=>(
            <div key={l}>
              <div style={{ fontSize:9, color:'var(--text-2)', textTransform:'uppercase', letterSpacing:'0.8px', marginBottom:2 }}>{l}</div>
              <div style={{ fontSize:11, fontFamily:'var(--mono)', color:'var(--text)' }}>{v||'—'}</div>
            </div>
          ))}
        </div>
      )}

      {!valid && (
        <div style={{ padding:'7px 14px', background:'var(--bg-2)', borderBottom:'1px solid var(--border)',
          fontSize:11, color:'var(--text-2)', flexShrink:0 }}>
          📍 Run a simulation then Generate Report to see attacker location
        </div>
      )}

      {/* Key trick: give MapContainer an absolute fill inside a relative wrapper */}
      <div style={{ flex:1, position:'relative', minHeight:0 }}>
        <div style={{ position:'absolute', inset:0 }}>
          <MapContainer center={[20,0]} zoom={2}
            style={{ height:'100%', width:'100%' }}
            zoomControl={false} attributionControl={false}>
            <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"/>
            <Recenter pos={pos}/>
            {valid && (
              <>
                <CircleMarker center={pos} radius={10}
                  fillColor="#FF4444" color="#FF4444" weight={2} fillOpacity={0.85}>
                  <Popup>
                    <strong style={{ fontFamily:'monospace' }}>{data?.attacker_ip}</strong><br/>
                    {geo.city}, {geo.country}<br/>{geo.isp}
                  </Popup>
                </CircleMarker>
                <CircleMarker center={pos} radius={26} fillColor="#FF4444" color="transparent" fillOpacity={0.08}/>
                <CircleMarker center={pos} radius={44} fillColor="#FF4444" color="transparent" fillOpacity={0.04}/>
              </>
            )}
          </MapContainer>
        </div>
      </div>
    </div>
  );
}
