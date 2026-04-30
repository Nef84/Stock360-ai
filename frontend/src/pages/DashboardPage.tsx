import { useEffect, useState } from 'react';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';
import { analyticsApi } from '../api/client';
import { DashboardStats, SalesByDay, TopProduct } from '../types';

const CHANNEL_DATA = [
  { name: 'WhatsApp', value: 62, color: '#00E676' },
  { name: 'Messenger', value: 28, color: '#00B4D8' },
  { name: 'Manual',   value: 10, color: '#FF6B35' },
];

const ACTIVITY = [
  { msg: 'Venta cerrada por IA: Nike Air Zoom talla 42',       time: 'hace 2 min',  type: 'sale'     },
  { msg: 'Cross-sell: Medias Pro Run — $12 extra',             time: 'hace 9 min',  type: 'sale'     },
  { msg: 'Seguimiento automático enviado a 4 clientes',        time: 'hace 18 min', type: 'followup' },
  { msg: 'Chat escalado a agente humano (queja de envío)',     time: 'hace 27 min', type: 'escalate' },
  { msg: 'Venta cerrada: Mochila Trail 25L — $45',             time: 'hace 35 min', type: 'sale'     },
  { msg: 'Nueva conversación abierta — WhatsApp',              time: 'hace 52 min', type: 'info'     },
];

const TT_STYLE = { background:'var(--panel)', border:'1px solid var(--border)', borderRadius:8, color:'var(--text)', fontSize:12 };

export default function DashboardPage() {
  const [stats,     setStats]     = useState<DashboardStats | null>(null);
  const [salesData, setSalesData] = useState<SalesByDay[]>([]);
  const [topProds,  setTopProds]  = useState<TopProduct[]>([]);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [s, d, t] = await Promise.all([
          analyticsApi.dashboard(),
          analyticsApi.salesByDay(7),
          analyticsApi.topProducts(30),
        ]);
        setStats(s.data);
        setSalesData(d.data);
        setTopProds(t.data);
      } catch {
        toast.error('Error cargando métricas');
      } finally {
        setLoading(false);
      }
    }
    load();
    const id = setInterval(load, 30_000); // refresh every 30s
    return () => clearInterval(id);
  }, []);

  if (loading) return <Loader />;

  const kpis = [
    { label:'Ventas por IA hoy',   value:`$${(stats?.ai_sales_today ?? 0).toLocaleString()}`, icon:'💰', color:'var(--green)',  sub:`de $${(stats?.total_sales_today ?? 0).toLocaleString()} totales` },
    { label:'Clientes atendidos',  value: stats?.clients_served_ai ?? 0,                      icon:'🤖', color:'var(--cyan)',   sub:'sin intervención humana' },
    { label:'Tasa de conversión',  value:`${stats?.conversion_rate ?? 0}%`,                    icon:'🔥', color:'var(--orange)', sub:'últimos 7 días' },
    { label:'Respuesta promedio',  value:`${((stats?.avg_response_ms ?? 0)/1000).toFixed(1)}s`,icon:'⚡', color:'var(--yellow)', sub:'tiempo de IA' },
  ];

  return (
    <div style={{ padding:24, overflowY:'auto', height:'100%' }}>
      <PageHeader
        tag="PANEL DE CONTROL"
        title={<>Dashboard <span style={{ color:'var(--green)' }}>Tiempo Real</span></>}
        sub="Tu vendedor digital Aria está activo 24/7 — cerrando ventas ahora mismo"
      />

      {/* KPIs */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14, marginBottom:20 }}>
        {kpis.map((k, i) => (
          <KpiCard key={i} {...k} />
        ))}
      </div>

      {/* Charts row */}
      <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:14, marginBottom:20 }}>
        {/* Area chart */}
        <Panel title="📈 Ventas IA vs Humano — Últimos 7 días ($)">
          <ResponsiveContainer width="100%" height={195}>
            <AreaChart data={salesData}>
              <defs>
                <linearGradient id="gAI" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00E676" stopOpacity={0.35}/>
                  <stop offset="95%" stopColor="#00E676" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="gHU" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00B4D8" stopOpacity={0.35}/>
                  <stop offset="95%" stopColor="#00B4D8" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="day"  tick={{ fill:'var(--muted)', fontSize:11 }} axisLine={false} tickLine={false}/>
              <YAxis                tick={{ fill:'var(--muted)', fontSize:11 }} axisLine={false} tickLine={false}/>
              <Tooltip contentStyle={TT_STYLE}/>
              <Area type="monotone" dataKey="ai"    stroke="#00E676" fill="url(#gAI)" strokeWidth={2.5} name="🤖 IA"/>
              <Area type="monotone" dataKey="human" stroke="#00B4D8" fill="url(#gHU)" strokeWidth={2}   name="👤 Humano"/>
            </AreaChart>
          </ResponsiveContainer>
        </Panel>

        {/* Channels pie */}
        <Panel title="📲 Canales de venta">
          <ResponsiveContainer width="100%" height={130}>
            <PieChart>
              <Pie data={CHANNEL_DATA} cx="50%" cy="50%" innerRadius={38} outerRadius={58} dataKey="value" paddingAngle={4}>
                {CHANNEL_DATA.map((d, i) => <Cell key={i} fill={d.color}/>)}
              </Pie>
              <Tooltip contentStyle={TT_STYLE}/>
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display:'flex', flexDirection:'column', gap:8, marginTop:8 }}>
            {CHANNEL_DATA.map((d, i) => (
              <div key={i} style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                  <div style={{ width:8, height:8, borderRadius:'50%', background:d.color }}/>
                  <span style={{ fontSize:12, color:'var(--muted)' }}>{d.name}</span>
                </div>
                <span style={{ fontSize:12, color:d.color, fontWeight:700, fontFamily:'var(--font-mono)' }}>{d.value}%</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      {/* Bottom row */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:14 }}>
        {/* Activity */}
        <Panel title="🤖 Actividad IA en tiempo real">
          <div style={{ display:'flex', flexDirection:'column', gap:7 }}>
            {ACTIVITY.map((item, i) => {
              const accent = item.type==='sale'?'#00E676':item.type==='escalate'?'#FF6B35':item.type==='followup'?'#00B4D8':'#FFB547';
              return (
                <div key={i} style={{
                  display:'flex', alignItems:'center', gap:10,
                  padding:'9px 12px', borderRadius:9,
                  background:`${accent}08`, border:`1px solid ${accent}20`,
                }}>
                  <span style={{ fontSize:15 }}>
                    {item.type==='sale'?'💰':item.type==='escalate'?'👤':item.type==='followup'?'📲':'ℹ️'}
                  </span>
                  <span style={{ flex:1, fontSize:12, color:'var(--text)' }}>{item.msg}</span>
                  <span style={{ fontSize:10, color:'var(--muted)', whiteSpace:'nowrap' }}>{item.time}</span>
                </div>
              );
            })}
          </div>
        </Panel>

        {/* Top products */}
        <Panel title="🏆 Productos más vendidos por IA">
          <div style={{ display:'flex', flexDirection:'column', gap:13 }}>
            {topProds.map((p, i) => (
              <div key={i}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:5 }}>
                  <span style={{ fontSize:13, color:'var(--text)' }}>{p.product_name}</span>
                  <div style={{ display:'flex', gap:12 }}>
                    <span style={{ fontSize:11, color:'var(--muted)' }}>{p.units_sold} uds</span>
                    <span style={{ fontSize:12, color:'var(--green)', fontFamily:'var(--font-mono)', fontWeight:600 }}>${p.revenue.toFixed(0)}</span>
                  </div>
                </div>
                <div style={{ height:5, borderRadius:4, background:'var(--border)' }}>
                  <div style={{ height:'100%', width:`${p.pct}%`, background:'linear-gradient(90deg, var(--green), var(--cyan))', borderRadius:4, transition:'width 0.5s' }}/>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

/* ── Shared sub-components ─────────────────────────────────────────────────── */
function KpiCard({ label, value, icon, color, sub }: { label:string; value:any; icon:string; color:string; sub:string }) {
  return (
    <div style={{
      background:'var(--panel)', border:'1px solid var(--border)',
      borderRadius:14, padding:20, position:'relative', overflow:'hidden',
    }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,${color},transparent)` }}/>
      <div style={{ fontSize:22, marginBottom:10 }}>{icon}</div>
      <div style={{ fontSize:28, fontWeight:800, color, fontFamily:'var(--font-mono)', lineHeight:1 }}>{String(value)}</div>
      <div style={{ fontSize:12, color:'var(--muted)', marginTop:6 }}>{label}</div>
      <div style={{ fontSize:11, color, opacity:0.8, marginTop:4 }}>{sub}</div>
    </div>
  );
}

function Panel({ title, children }: { title:string; children:React.ReactNode }) {
  return (
    <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:20 }}>
      <div style={{ fontSize:13, fontWeight:600, marginBottom:14, color:'var(--text)' }}>{title}</div>
      {children}
    </div>
  );
}

function PageHeader({ tag, title, sub }: { tag:string; title:React.ReactNode; sub:string }) {
  return (
    <div style={{ marginBottom:24 }}>
      <div style={{ fontSize:10, color:'var(--green)', letterSpacing:4, fontFamily:'var(--font-mono)', marginBottom:8 }}>
        {tag}
      </div>
      <h1 style={{ fontSize:24, fontWeight:800, color:'var(--text)', margin:0 }}>{title}</h1>
      <p style={{ fontSize:13, color:'var(--muted)', marginTop:5 }}>{sub}</p>
    </div>
  );
}

function Loader() {
  return (
    <div style={{ height:'100%', display:'flex', alignItems:'center', justifyContent:'center' }}>
      <div style={{ textAlign:'center' }}>
        <div style={{ fontSize:32, marginBottom:12, animation:'spin 1s linear infinite', display:'inline-block' }}>⚡</div>
        <div style={{ color:'var(--muted)', fontSize:13 }}>Cargando métricas…</div>
      </div>
    </div>
  );
}
