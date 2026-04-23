// Room By Room — redesigned mobile PWA
// Clean, minimal, Nest-ish. Single strong direction.

const { useState, useEffect, useMemo, useRef } = React;

// ─────────────────────────────────────────────────────────────
// Tweakable defaults
// ─────────────────────────────────────────────────────────────
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#E86A33",
  "density": "comfortable",
  "showBackground": true,
  "units": "C",
  "simulatedHour": 17
}/*EDITMODE-END*/;

// ─────────────────────────────────────────────────────────────
// Data model — realistic heating state
// ─────────────────────────────────────────────────────────────
const INITIAL_ROOMS = [
  { id: 'kitchen',    name: 'Kitchen',      temp: 19.7, target: 20.0, mode: 'Timed', nextChange: { time: '17:30', target: 20.0 } },
  { id: 'sunroom',    name: 'Sunroom',      temp: 24.0, target: 16.5, mode: 'Timed', nextChange: { time: '16:30', target: 16.5 } },
  { id: 'lounge',     name: 'Lounge',       temp: 20.4, target: 21.0, mode: 'Timed', nextChange: { time: '17:30', target: 21.0 } },
  { id: 'hall',       name: 'Hall',         temp: null, target: 17.0, mode: 'Timed', nextChange: { time: '17:00', target: 17.0 }, offline: true },
  { id: 'office',     name: 'Office',       temp: 25.2, target: null, mode: 'Off',   nextChange: null },
  { id: 'mainbed',    name: 'Main Bedroom', temp: 23.0, target: 15.0, mode: 'Timed', nextChange: { time: '22:30', target: 15.0 } },
  { id: 'guestbed',   name: 'Guest Bedroom',temp: 22.9, target: null, mode: 'Off',   nextChange: null },
  { id: 'outside',    name: 'Outside',      temp: 11.6, target: null, mode: 'Sensor', nextChange: null, sensor: true },
];

const PROFILES = ['Monday-Friday', 'Weekend', 'All off'];

// A room is "calling for heat" when target > temp by more than a small deadband
function callingForHeat(room) {
  if (room.sensor || room.offline) return false;
  if (room.mode === 'Off') return false;
  if (room.target == null || room.temp == null) return false;
  return room.target - room.temp > 0.2;
}

// ─────────────────────────────────────────────────────────────
// Warm gradient background — shifts with hour
// Morning = peach, midday = cool cream, evening = warm amber, night = indigo
// ─────────────────────────────────────────────────────────────
function backgroundFor(hour) {
  // hour 0-23
  // Three anchor stops
  if (hour < 6)    return ['#1e2238', '#2d2a3e', '#433048']; // night
  if (hour < 10)   return ['#ffe8d4', '#ffd3b0', '#f5b994']; // morning peach
  if (hour < 15)   return ['#fdf6ec', '#fbeedd', '#f5e2c9']; // midday cream
  if (hour < 19)   return ['#ffe1c2', '#f7b88a', '#e88a5b']; // afternoon amber
  if (hour < 22)   return ['#f0a877', '#b66b56', '#5a3a52']; // sunset
  return ['#27253a', '#332b42', '#4a3450'];                  // late night
}

// ─────────────────────────────────────────────────────────────
// Icons — simple inline SVGs
// ─────────────────────────────────────────────────────────────
const Icon = {
  flame: (p) => (
    <svg viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M12 3c.5 3 3 4 3 7a3 3 0 01-6 0c0-1 .3-1.7.7-2.2C10 10 9 11.5 9 13a5 5 0 0010 0c0-4-4-6-7-10z" fill="currentColor"/>
    </svg>
  ),
  clock: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <circle cx="12" cy="12" r="9"/>
      <path d="M12 7v5l3 2" strokeLinecap="round"/>
    </svg>
  ),
  power: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M12 3v9" strokeLinecap="round"/>
      <path d="M6.5 7.5a8 8 0 1011 0" strokeLinecap="round"/>
    </svg>
  ),
  on: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M4 12h16M12 4v16" strokeLinecap="round"/>
    </svg>
  ),
  boost: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M12 3l7 9h-4l1 9-7-9h4l-1-9z" strokeLinejoin="round"/>
    </svg>
  ),
  chevron: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  calendar: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <rect x="3.5" y="5" width="17" height="15" rx="2"/>
      <path d="M8 3v4M16 3v4M3.5 10h17" strokeLinecap="round"/>
    </svg>
  ),
  menu: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round"/>
    </svg>
  ),
  minus: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" {...p}>
      <path d="M6 12h12" strokeLinecap="round"/>
    </svg>
  ),
  plus: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" {...p}>
      <path d="M12 6v12M6 12h12" strokeLinecap="round"/>
    </svg>
  ),
  sensor: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M12 14a2 2 0 100-4 2 2 0 000 4z" fill="currentColor" stroke="none"/>
      <path d="M8 8a5.66 5.66 0 000 8M16 8a5.66 5.66 0 010 8M5 5a10 10 0 000 14M19 5a10 10 0 010 14" strokeLinecap="round"/>
    </svg>
  ),
  edit: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M4 20h4L19 9l-4-4L4 16v4z" strokeLinejoin="round"/>
    </svg>
  ),
  wifiOff: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...p}>
      <path d="M3 3l18 18" strokeLinecap="round"/>
      <path d="M5 12.5a10 10 0 0114-2M8.5 16a5 5 0 016-1" strokeLinecap="round"/>
      <circle cx="12" cy="19" r="1" fill="currentColor" stroke="none"/>
    </svg>
  ),
  chevRight: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M9 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  ),
  close: (p) => (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...p}>
      <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round"/>
    </svg>
  ),
};

// ─────────────────────────────────────────────────────────────
// Utility: format temp with units
// ─────────────────────────────────────────────────────────────
function fmt(temp, units = 'C', digits = 1) {
  if (temp == null) return '—';
  if (units === 'F') return (temp * 9/5 + 32).toFixed(digits);
  return temp.toFixed(digits);
}
const U = (units) => units === 'F' ? '°F' : '°C';

// ─────────────────────────────────────────────────────────────
// Header: compact branded top bar
// ─────────────────────────────────────────────────────────────
function TopBar({ onMenu, accent }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '10px 18px 8px', background: 'rgba(255,255,255,0.82)',
      backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)',
      borderBottom: '1px solid rgba(0,0,0,0.05)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <HouseMark accent={accent} />
        <div>
          <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: -0.3, color: '#1a1a1a' }}>Room By Room</div>
          <div style={{ fontSize: 11, color: '#888', marginTop: -1 }}>QED6 · 214</div>
        </div>
      </div>
      <button onClick={onMenu} style={{
        width: 38, height: 38, borderRadius: 12, border: 'none',
        background: 'rgba(0,0,0,0.04)', display: 'flex', alignItems: 'center',
        justifyContent: 'center', cursor: 'pointer', color: '#1a1a1a',
      }}>
        <Icon.menu width={20} height={20}/>
      </button>
    </div>
  );
}

function HouseMark({ accent }) {
  return (
    <div style={{
      width: 34, height: 34, borderRadius: 10, background: accent,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: `0 4px 12px ${accent}40`,
    }}>
      <svg viewBox="0 0 24 24" width={20} height={20} fill="none" stroke="white" strokeWidth="2">
        <path d="M3 11L12 4l9 7v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1v-9z" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Summary card — the "glanceable" piece
// ─────────────────────────────────────────────────────────────
function SummaryCard({ rooms, accent, units, profile, onProfileTap }) {
  const heating = rooms.filter(callingForHeat);
  const count = heating.length;
  const avg = useMemo(() => {
    const indoor = rooms.filter(r => !r.sensor && !r.offline && r.temp != null);
    if (!indoor.length) return null;
    return indoor.reduce((s, r) => s + r.temp, 0) / indoor.length;
  }, [rooms]);
  const outside = rooms.find(r => r.sensor);

  return (
    <div style={{
      margin: '14px 16px 0', borderRadius: 20, padding: 18,
      background: 'white',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 8px 24px -8px rgba(0,0,0,0.08)',
    }}>
      {/* calling for heat status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: count > 0 ? `${accent}15` : '#f1f3f5',
          color: count > 0 ? accent : '#999',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          position: 'relative',
        }}>
          <Icon.flame width={20} height={20}/>
          {count > 0 && <span style={{
            position: 'absolute', top: 5, right: 5, width: 7, height: 7,
            borderRadius: 10, background: accent,
            boxShadow: `0 0 0 0 ${accent}80`,
            animation: 'pulse 1.6s infinite',
          }}/>}
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a', letterSpacing: -0.2 }}>
            {count === 0 ? 'Nothing calling for heat' :
             count === 1 ? `${heating[0].name} is calling for heat` :
             `${count} rooms calling for heat`}
          </div>
          <div style={{ fontSize: 12, color: '#777', marginTop: 2 }}>
            {count > 1 && heating.slice(0, 3).map(r => r.name).join(', ')
              + (count > 3 ? `, +${count-3} more` : '')}
            {count === 0 && 'Boiler idle'}
            {count === 1 && 'Boiler firing'}
          </div>
        </div>
      </div>

      {/* row of stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 0, borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
        <Stat label="Average indoor" value={avg != null ? `${fmt(avg, units, 1)}°` : '—'} />
        <Stat label="Outside" value={outside ? `${fmt(outside.temp, units, 1)}°` : '—'} />
        <Stat label="Today" value="Mon 23 Apr" small />
      </div>

      {/* profile pill */}
      <button onClick={onProfileTap} style={{
        marginTop: 14, width: '100%', border: '1px solid #ececec',
        background: '#fafafa', borderRadius: 12, padding: '10px 14px',
        display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer',
      }}>
        <Icon.calendar width={16} height={16} style={{ color: '#666' }}/>
        <div style={{ flex: 1, textAlign: 'left' }}>
          <div style={{ fontSize: 11, color: '#999', letterSpacing: 0.3, textTransform: 'uppercase' }}>Today's profile</div>
          <div style={{ fontSize: 14, color: '#1a1a1a', fontWeight: 500 }}>{profile}</div>
        </div>
        <Icon.chevRight width={16} height={16} style={{ color: '#bbb' }}/>
      </button>
    </div>
  );
}

function Stat({ label, value, small }) {
  return (
    <div style={{ padding: '0 4px' }}>
      <div style={{ fontSize: 10.5, color: '#999', letterSpacing: 0.4, textTransform: 'uppercase', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: small ? 14 : 18, fontWeight: 600, color: '#1a1a1a', letterSpacing: -0.3 }}>{value}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Room row — rest state + inline expansion
// ─────────────────────────────────────────────────────────────
function RoomRow({ room, expanded, onToggle, onChange, accent, units, density }) {
  const calling = callingForHeat(room);
  const compact = density === 'compact';

  return (
    <div style={{
      background: 'white', borderRadius: 16, overflow: 'hidden',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04), 0 4px 14px -8px rgba(0,0,0,0.08)',
      transition: 'box-shadow .2s',
      ...(expanded && { boxShadow: '0 1px 2px rgba(0,0,0,0.05), 0 12px 32px -8px rgba(0,0,0,0.12)' }),
    }}>
      {/* Rest row */}
      <button
        onClick={onToggle}
        style={{
          width: '100%', border: 'none', background: 'transparent',
          padding: compact ? '12px 14px' : '14px 16px',
          display: 'flex', alignItems: 'center', gap: 12,
          cursor: 'pointer', textAlign: 'left',
        }}>
        {/* mode dot + indicator */}
        <ModeChip room={room} accent={accent}/>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <div style={{ fontSize: compact ? 15 : 16, fontWeight: 600, color: '#1a1a1a', letterSpacing: -0.2 }}>{room.name}</div>
            {calling && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10.5, color: accent, fontWeight: 600 }}>
                <Icon.flame width={11} height={11}/>heating
              </span>
            )}
            {room.offline && (
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, fontSize: 10.5, color: '#c78a1a', fontWeight: 500 }}>
                <Icon.wifiOff width={11} height={11}/>offline
              </span>
            )}
          </div>
          <SubLine room={room} units={units}/>
        </div>

        {/* current temperature, big */}
        <div style={{ textAlign: 'right', paddingLeft: 6 }}>
          <div style={{ fontSize: compact ? 20 : 22, fontWeight: 500, letterSpacing: -0.8, color: room.offline ? '#bbb' : '#1a1a1a', lineHeight: 1 }}>
            {room.temp != null ? fmt(room.temp, units, 1) : '—'}
            <span style={{ fontSize: 11, color: '#999', fontWeight: 400, marginLeft: 2 }}>{U(units)}</span>
          </div>
          {room.target != null && !room.sensor && (
            <div style={{ fontSize: 11, color: '#999', marginTop: 3 }}>
              set <span style={{ color: '#555', fontWeight: 500 }}>{fmt(room.target, units, 1)}°</span>
            </div>
          )}
        </div>

        {!room.sensor && (
          <Icon.chevron width={16} height={16} style={{
            color: '#bbb',
            transition: 'transform .25s',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
          }}/>
        )}
      </button>

      {/* Expanded controls */}
      {expanded && !room.sensor && (
        <ExpandedControls room={room} onChange={onChange} accent={accent} units={units}/>
      )}
    </div>
  );
}

function SubLine({ room, units }) {
  if (room.sensor) {
    return <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Outdoor sensor</div>;
  }
  if (room.offline) {
    return <div style={{ fontSize: 12, color: '#c78a1a', marginTop: 2 }}>No signal since 14:22</div>;
  }
  if (room.mode === 'Off') {
    return <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>Off — no schedule</div>;
  }
  if (room.boost) {
    return <div style={{ fontSize: 12, color: '#1a1a1a', marginTop: 2 }}>
      Boost · {room.boost} left
    </div>;
  }
  if (room.nextChange) {
    return <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
      → {fmt(room.nextChange.target, units, 1)}° at {room.nextChange.time}
    </div>;
  }
  return null;
}

function ModeChip({ room, accent }) {
  const calling = callingForHeat(room);
  const bg = room.sensor ? '#f1f3f5'
    : room.offline ? '#fff4e0'
    : room.mode === 'Off' ? '#f1f3f5'
    : calling ? `${accent}15`
    : '#e8f4ec';
  const fg = room.sensor ? '#888'
    : room.offline ? '#c78a1a'
    : room.mode === 'Off' ? '#999'
    : calling ? accent
    : '#3a8c5f';

  const iconEl = room.sensor ? <Icon.sensor width={16} height={16}/>
    : room.mode === 'Off' ? <Icon.power width={16} height={16}/>
    : room.boost ? <Icon.boost width={16} height={16}/>
    : <Icon.clock width={16} height={16}/>;

  return (
    <div style={{
      width: 38, height: 38, borderRadius: 12, background: bg, color: fg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      {iconEl}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Expanded controls — mode, stepper target, boost
// ─────────────────────────────────────────────────────────────
function ExpandedControls({ room, onChange, accent, units }) {
  const setMode = (mode) => onChange({ ...room, mode, boost: null, target: mode === 'Off' ? null : (room.target ?? 20) });
  const stepTarget = (d) => onChange({ ...room, target: Math.max(5, Math.min(30, (room.target ?? 20) + d)) });
  const setBoost = (duration) => onChange({ ...room, mode: 'Boost', boost: duration });

  const modes = [
    { id: 'Timed', label: 'Timed', icon: <Icon.clock width={15} height={15}/> },
    { id: 'On',    label: 'On',    icon: <Icon.on width={15} height={15}/> },
    { id: 'Off',   label: 'Off',   icon: <Icon.power width={15} height={15}/> },
  ];

  return (
    <div style={{ padding: '4px 16px 18px', borderTop: '1px solid #f3f3f3' }}>
      {/* Mode segmented */}
      <div style={{ fontSize: 10.5, color: '#999', letterSpacing: 0.4, textTransform: 'uppercase', margin: '14px 0 8px' }}>Mode</div>
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6,
        background: '#f4f5f7', padding: 4, borderRadius: 12,
      }}>
        {modes.map(m => (
          <button key={m.id} onClick={() => setMode(m.id)} style={{
            border: 'none', borderRadius: 9, padding: '10px 6px',
            background: room.mode === m.id ? 'white' : 'transparent',
            color: room.mode === m.id ? '#1a1a1a' : '#888',
            fontWeight: room.mode === m.id ? 600 : 500, fontSize: 13,
            boxShadow: room.mode === m.id ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
            cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
            justifyContent: 'center', gap: 6,
          }}>
            {m.icon}{m.label}
          </button>
        ))}
      </div>

      {/* Target stepper */}
      {room.mode !== 'Off' && (
        <>
          <div style={{ fontSize: 10.5, color: '#999', letterSpacing: 0.4, textTransform: 'uppercase', margin: '16px 0 8px' }}>Target</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <StepBtn onClick={() => stepTarget(-0.5)} accent={accent}><Icon.minus width={22} height={22}/></StepBtn>
            <div style={{
              flex: 1, textAlign: 'center', padding: '14px 8px',
              background: `${accent}0a`, borderRadius: 14,
              border: `1px solid ${accent}20`,
            }}>
              <div style={{ fontSize: 30, fontWeight: 500, letterSpacing: -1, color: '#1a1a1a', lineHeight: 1 }}>
                {fmt(room.target ?? 20, units, 1)}
                <span style={{ fontSize: 15, color: accent, marginLeft: 4 }}>{U(units)}</span>
              </div>
              <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
                Target temperature
              </div>
            </div>
            <StepBtn onClick={() => stepTarget(0.5)} accent={accent}><Icon.plus width={22} height={22}/></StepBtn>
          </div>
        </>
      )}

      {/* Boost */}
      {room.mode !== 'Off' && (
        <>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', margin: '18px 0 8px' }}>
            <div style={{ fontSize: 10.5, color: '#999', letterSpacing: 0.4, textTransform: 'uppercase' }}>Boost</div>
            {room.boost && <button onClick={() => onChange({ ...room, boost: null, mode: 'Timed' })} style={{
              background: 'none', border: 'none', color: accent, fontSize: 12, cursor: 'pointer', padding: 0, fontWeight: 500,
            }}>Cancel</button>}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
            {['30 min', '1 hr', '2 hr'].map(d => {
              const active = room.boost === d;
              return (
                <button key={d} onClick={() => setBoost(d)} style={{
                  padding: '10px 0', borderRadius: 10,
                  border: active ? `1.5px solid ${accent}` : '1px solid #ececec',
                  background: active ? `${accent}12` : 'white',
                  color: active ? accent : '#1a1a1a',
                  fontSize: 13, fontWeight: active ? 600 : 500, cursor: 'pointer',
                }}>{d}</button>
              );
            })}
          </div>
        </>
      )}

      {/* Schedule link */}
      <button style={{
        marginTop: 14, width: '100%', background: 'transparent', border: '1px solid #ececec',
        borderRadius: 12, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10,
        cursor: 'pointer', color: '#1a1a1a',
      }}>
        <Icon.edit width={15} height={15} style={{ color: '#888' }}/>
        <div style={{ flex: 1, textAlign: 'left', fontSize: 13.5 }}>Edit schedule</div>
        <Icon.chevRight width={14} height={14} style={{ color: '#bbb' }}/>
      </button>
    </div>
  );
}

function StepBtn({ children, onClick, accent }) {
  return (
    <button onClick={onClick} style={{
      width: 54, height: 54, borderRadius: 17, border: 'none',
      background: 'white', color: accent, cursor: 'pointer',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 1px 2px rgba(0,0,0,0.06), 0 6px 16px -6px rgba(0,0,0,0.14)',
      flexShrink: 0,
    }}>{children}</button>
  );
}

// ─────────────────────────────────────────────────────────────
// Profile sheet (bottom sheet)
// ─────────────────────────────────────────────────────────────
function Sheet({ open, onClose, title, children }) {
  return (
    <>
      <div onClick={onClose} style={{
        position: 'absolute', inset: 0,
        background: open ? 'rgba(0,0,0,0.35)' : 'transparent',
        pointerEvents: open ? 'auto' : 'none',
        transition: 'background .24s', zIndex: 20,
      }}/>
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0,
        background: 'white', borderTopLeftRadius: 24, borderTopRightRadius: 24,
        transform: open ? 'translateY(0)' : 'translateY(100%)',
        transition: 'transform .28s cubic-bezier(.2,.9,.3,1)',
        zIndex: 21, paddingBottom: 24, maxHeight: '85%', overflow: 'auto',
        boxShadow: '0 -12px 40px -8px rgba(0,0,0,0.2)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', padding: '10px 0 0' }}>
          <div style={{ width: 40, height: 4, borderRadius: 2, background: '#e5e5e7' }}/>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 20px 4px' }}>
          <div style={{ fontSize: 17, fontWeight: 600, letterSpacing: -0.3 }}>{title}</div>
          <button onClick={onClose} style={{
            width: 30, height: 30, borderRadius: 15, border: 'none', background: '#f1f3f5',
            color: '#666', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
          }}><Icon.close width={16} height={16}/></button>
        </div>
        {children}
      </div>
    </>
  );
}

function ProfileSheet({ open, onClose, profile, setProfile, accent }) {
  const calendar = [
    ['Mon', 'Monday-Friday'], ['Tue', 'Monday-Friday'], ['Wed', 'Monday-Friday'],
    ['Thu', 'Monday-Friday'], ['Fri', 'Monday-Friday'], ['Sat', 'Weekend'], ['Sun', 'Weekend'],
  ];
  return (
    <Sheet open={open} onClose={onClose} title="Profile">
      <div style={{ padding: '4px 20px 0' }}>
        <div style={{ fontSize: 13, color: '#777', marginTop: 2 }}>
          Override today's profile, or let the calendar decide.
        </div>

        <div style={{ fontSize: 10.5, color: '#999', letterSpacing: 0.4, textTransform: 'uppercase', margin: '18px 0 8px' }}>Use now</div>
        <div style={{ display: 'grid', gap: 8 }}>
          {PROFILES.map(p => (
            <button key={p} onClick={() => { setProfile(p); onClose(); }} style={{
              textAlign: 'left', padding: '14px 14px', borderRadius: 12,
              border: profile === p ? `1.5px solid ${accent}` : '1px solid #ececec',
              background: profile === p ? `${accent}0d` : 'white',
              color: '#1a1a1a', fontSize: 15, fontWeight: 500, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <div style={{
                width: 18, height: 18, borderRadius: 9,
                border: profile === p ? `5px solid ${accent}` : '1.5px solid #ccc',
                flexShrink: 0,
              }}/>
              {p}
              {profile === p && <span style={{ marginLeft: 'auto', fontSize: 11, color: accent, fontWeight: 600 }}>ACTIVE</span>}
            </button>
          ))}
        </div>

        <div style={{ fontSize: 10.5, color: '#999', letterSpacing: 0.4, textTransform: 'uppercase', margin: '22px 0 8px' }}>Calendar</div>
        <div style={{ border: '1px solid #ececec', borderRadius: 12, overflow: 'hidden' }}>
          {calendar.map(([d, p], i) => (
            <div key={d} style={{
              display: 'flex', alignItems: 'center', padding: '12px 14px',
              borderTop: i ? '1px solid #f3f3f3' : 'none',
            }}>
              <div style={{ width: 38, fontSize: 13, fontWeight: 600, color: '#888' }}>{d}</div>
              <div style={{ flex: 1, fontSize: 14, color: '#1a1a1a' }}>{p}</div>
              <Icon.chevRight width={14} height={14} style={{ color: '#ccc' }}/>
            </div>
          ))}
        </div>

        <button style={{
          marginTop: 14, width: '100%', background: 'transparent',
          border: '1px solid #ececec', borderRadius: 12, padding: '12px',
          fontSize: 14, color: '#1a1a1a', cursor: 'pointer',
        }}>Manage profiles…</button>
      </div>
    </Sheet>
  );
}

function MenuSheet({ open, onClose, accent }) {
  const items = [
    { label: 'Profiles & schedules', sub: '3 profiles' },
    { label: 'Rooms & thermostats', sub: '8 devices' },
    { label: 'Holiday mode', sub: 'Off' },
    { label: 'Boiler & system', sub: 'QED6 · 214' },
    { label: 'Notifications' },
    { label: 'Help & support' },
  ];
  return (
    <Sheet open={open} onClose={onClose} title="Menu">
      <div style={{ padding: '4px 20px 8px' }}>
        <div style={{ border: '1px solid #ececec', borderRadius: 14, overflow: 'hidden', marginTop: 10 }}>
          {items.map((it, i) => (
            <button key={it.label} style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 12,
              padding: '14px 14px', background: 'white', border: 'none',
              borderTop: i ? '1px solid #f3f3f3' : 'none', cursor: 'pointer', textAlign: 'left',
            }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, color: '#1a1a1a', fontWeight: 500 }}>{it.label}</div>
                {it.sub && <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>{it.sub}</div>}
              </div>
              <Icon.chevRight width={14} height={14} style={{ color: '#bbb' }}/>
            </button>
          ))}
        </div>
        <div style={{ fontSize: 11, color: '#aaa', textAlign: 'center', marginTop: 18 }}>
          Room By Room · v4.2 · QED6 214
        </div>
      </div>
    </Sheet>
  );
}

// ─────────────────────────────────────────────────────────────
// Tweaks panel
// ─────────────────────────────────────────────────────────────
function TweaksPanel({ tweaks, setTweaks, visible }) {
  if (!visible) return null;
  const set = (k, v) => {
    const next = { ...tweaks, [k]: v };
    setTweaks(next);
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: { [k]: v } }, '*');
  };
  const swatches = ['#E86A33', '#2B7A5A', '#1a66d9', '#7a3fd9', '#c0392b', '#1a1a1a'];
  return (
    <div style={{
      position: 'fixed', bottom: 16, right: 16, width: 260, zIndex: 60,
      background: 'white', borderRadius: 16, padding: 14,
      boxShadow: '0 12px 40px -4px rgba(0,0,0,0.25)', fontSize: 12,
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 10 }}>Tweaks</div>

      <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 6 }}>Accent</div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {swatches.map(s => (
          <button key={s} onClick={() => set('accent', s)} style={{
            width: 24, height: 24, borderRadius: 12, background: s, cursor: 'pointer',
            border: tweaks.accent === s ? '2px solid #1a1a1a' : '2px solid transparent',
          }}/>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 6 }}>Density</div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {['comfortable', 'compact'].map(d => (
          <button key={d} onClick={() => set('density', d)} style={{
            flex: 1, padding: 6, fontSize: 12, borderRadius: 8,
            border: tweaks.density === d ? `1.5px solid ${tweaks.accent}` : '1px solid #ddd',
            background: tweaks.density === d ? `${tweaks.accent}12` : 'white', cursor: 'pointer',
          }}>{d}</button>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 6 }}>Units</div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        {['C', 'F'].map(u => (
          <button key={u} onClick={() => set('units', u)} style={{
            flex: 1, padding: 6, fontSize: 12, borderRadius: 8,
            border: tweaks.units === u ? `1.5px solid ${tweaks.accent}` : '1px solid #ddd',
            background: tweaks.units === u ? `${tweaks.accent}12` : 'white', cursor: 'pointer',
          }}>°{u}</button>
        ))}
      </div>

      <div style={{ fontSize: 10, color: '#888', textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 6 }}>Time of day — {tweaks.simulatedHour}:00</div>
      <input type="range" min="0" max="23" value={tweaks.simulatedHour}
        onChange={e => set('simulatedHour', +e.target.value)}
        style={{ width: '100%', marginBottom: 10, accentColor: tweaks.accent }}/>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#333' }}>
        <input type="checkbox" checked={tweaks.showBackground}
          onChange={e => set('showBackground', e.target.checked)}/>
        Show time-of-day background
      </label>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main app
// ─────────────────────────────────────────────────────────────
function App() {
  const initialState = (() => {
    const p = new URLSearchParams(window.location.search);
    const forced = window.__RBR_INIT || {};
    return {
      expandedId: forced.expandedId ?? p.get('expanded') ?? null,
      profileOpen: forced.profileOpen ?? p.get('sheet') === 'profile',
      menuOpen: forced.menuOpen ?? p.get('sheet') === 'menu',
    };
  })();
  const [rooms, setRooms] = useState(INITIAL_ROOMS);
  const [expandedId, setExpandedId] = useState(initialState.expandedId);
  const [profileOpen, setProfileOpen] = useState(initialState.profileOpen);
  const [menuOpen, setMenuOpen] = useState(initialState.menuOpen);
  const [profile, setProfile] = useState('Monday-Friday');
  const [tweaks, setTweaks] = useState(TWEAK_DEFAULTS);
  const [tweaksVisible, setTweaksVisible] = useState(false);

  // Expose for handoff screenshots
  useEffect(() => {
    window.__rbr = { setExpandedId, setProfileOpen, setMenuOpen, setProfile };
  });

  // Edit-mode wiring
  useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === '__activate_edit_mode') setTweaksVisible(true);
      if (e.data?.type === '__deactivate_edit_mode') setTweaksVisible(false);
    };
    window.addEventListener('message', handler);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', handler);
  }, []);

  const updateRoom = (updated) => setRooms(rs => rs.map(r => r.id === updated.id ? updated : r));
  const bg = backgroundFor(tweaks.simulatedHour);

  const content = (
    <div style={{
      width: '100%', height: '100%', overflow: 'hidden', position: 'relative',
      background: tweaks.showBackground
        ? `linear-gradient(180deg, ${bg[0]} 0%, ${bg[1]} 45%, ${bg[2]} 100%)`
        : '#f6f6f8',
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif',
      color: '#1a1a1a',
    }}>
      {/* subtle noise overlay for warmth */}
      {tweaks.showBackground && (
        <div style={{
          position: 'absolute', inset: 0,
          background: 'radial-gradient(ellipse at 50% -20%, rgba(255,255,255,0.5) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}/>
      )}

      <div style={{
        position: 'relative', zIndex: 1, height: '100%', overflow: 'auto',
        paddingBottom: 40,
      }}>
        <TopBar onMenu={() => setMenuOpen(true)} accent={tweaks.accent}/>
        <SummaryCard
          rooms={rooms} accent={tweaks.accent} units={tweaks.units}
          profile={profile} onProfileTap={() => setProfileOpen(true)}
        />

        <div style={{
          margin: '14px 16px 0', display: 'flex', flexDirection: 'column', gap: 8,
        }}>
          {rooms.map(r => (
            <RoomRow
              key={r.id} room={r}
              expanded={expandedId === r.id}
              onToggle={() => setExpandedId(id => id === r.id ? null : r.id)}
              onChange={updateRoom}
              accent={tweaks.accent} units={tweaks.units} density={tweaks.density}
            />
          ))}
        </div>

        <div style={{ fontSize: 11, color: 'rgba(0,0,0,0.42)', textAlign: 'center', marginTop: 18, padding: '0 16px' }}>
          Last sync 12s ago · 8 devices · all online
        </div>
      </div>

      <ProfileSheet open={profileOpen} onClose={() => setProfileOpen(false)}
        profile={profile} setProfile={setProfile} accent={tweaks.accent}/>
      <MenuSheet open={menuOpen} onClose={() => setMenuOpen(false)} accent={tweaks.accent}/>
    </div>
  );

  return (
    <>
      <style>{`
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 currentColor; }
          70% { box-shadow: 0 0 0 8px transparent; }
          100% { box-shadow: 0 0 0 0 transparent; }
        }
        button:active { transform: scale(0.98); }
        button { transition: background .15s, border-color .15s, transform .05s; }
        * { -webkit-tap-highlight-color: transparent; }
        ::-webkit-scrollbar { display: none; }
      `}</style>
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#e9ebf0',
        backgroundImage: 'radial-gradient(circle at 50% 50%, #f2f3f6, #d8dce3)',
        padding: '20px 0',
      }}>
        <IOSDevice width={402} height={874}>
          {content}
        </IOSDevice>
      </div>
      <TweaksPanel tweaks={tweaks} setTweaks={setTweaks} visible={tweaksVisible}/>
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
