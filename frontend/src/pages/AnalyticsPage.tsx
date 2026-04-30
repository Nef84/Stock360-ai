import { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import toast from 'react-hot-toast';
import { analyticsApi } from '../api/client';
import { SalesByDay, TopProduct } from '../types';

const TT_STYLE = { background:'var(--panel)', border:'1px solid var(--border)', borderRadius:8, color:'var(--text)', fontSize:12 };

const FUNNEL = [
  { label:'Mensajes',  val:271, pct:100, color:'var(--muted)'  },
  { label:'Atendidos', val:243, pct:90,  color:'var(--cyan)'   },
  { label:'Interés',   val:189, pct:70,  color:'var(--yellow)' },
  { label:'Oferta',    val:142, pct:52,  color:'var(--orange)' },
  { label:'Cerrado',   val:87,  pct:32,  color:'var(--green)'  },
];

export default function AnalyticsPage() {
  const [salesData, setSalesData] = useState<SalesByDay[]>([]);
  const [topProds,  setTopProds]  = useState<TopProduct[]>([]);
  const [loading,   setLoading]   = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [d, t] = await Promise.all([
          analyticsApi.salesByDay(7),
          analyticsApi.topProducts(30),
        ]);
        setSalesData(d.data);
        setTopProds(t.data);
      } catch { toast.error('Error cargando analytics'); }
      finally { setLoading(false); }
    }
    load();
  }, []);

  return (
    <div style={{ padding:24, overflowY:'auto', height:'100%' }}>
      <div style={{ marginBottom:24 }}>
        <div style={{ fontSize:9, color:'var(--green)', letterSpacing:4, fontFamily:'var(--font-mono)', marginBottom:8 }}>ANALYTICS · INTELIGENCIA DE VENTAS</div>
        <h1 style={{ fontSize:24, fontWeight:800, color:'var(--text)', margin:0 }}>Rendimiento <span style={{ color:'var(--green)' }}>IA</span></h1>
        <p style={{ fontSize:13, color:'var(--muted)', marginTop:4 }}>Métricas de conversión automática y performance del agente Aria</p>
      </div>

      {/* Summary KPIs */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14, marginBottom:20 }}>
        {[
          { label:'Mensajes procesados', value:'271', color:'var(--cyan)',   icon:'📩' },
          { label:'Conversiones IA',     value:'87',  color:'var(--green)',  icon:'💰' },
          { label:'Tasa de conversión',  value:'32%', color:'var(--orange)', icon:'🔥' },
          { label:'Ticket promedio',     value:'$48', color:'var(--yellow)', icon:'🧾' },
        ].map((k,i) => (
          <div key={i} style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:18, position:'relative', overflow:'hidden' }}>
            <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,${k.color},transparent)` }}/>
            <div style={{ fontSize:20, marginBottom:8 }}>{k.icon}</div>
            <div style={{ fontSize:28, fontWeight:800, color:k.color, fontFamily:'var(--font-mono)' }}>{k.value}</div>
            <div style={{ fontSize:12, color:'var(--muted)', marginTop:5 }}>{k.label}</div>
          </div>
        ))}
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'2fr 1fr', gap:14, marginBottom:14 }}>
        {/* Bar chart */}
        <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:20 }}>
          <div style={{ fontSize:13, fontWeight:600, marginBottom:14, color:'var(--text)' }}>Ventas diarias — IA 🤖 vs Humano 👤 ($)</div>
          {loading ? <div style={{ height:200, display:'flex', alignItems:'center', justifyContent:'center', color:'var(--muted)' }}>Cargando…</div> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={salesData} barGap={4}>
                <XAxis dataKey="day"  tick={{ fill:'var(--muted)', fontSize:11 }} axisLine={false} tickLine={false}/>
                <YAxis                tick={{ fill:'var(--muted)', fontSize:11 }} axisLine={false} tickLine={false}/>
                <Tooltip contentStyle={TT_STYLE}/>
                <Bar dataKey="ai"    fill="#00E676" radius={[5,5,0,0]} name="🤖 IA"/>
                <Bar dataKey="human" fill="#00B4D8" radius={[5,5,0,0]} name="👤 Humano"/>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top products */}
        <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:20 }}>
          <div style={{ fontSize:13, fontWeight:600, marginBottom:14, color:'var(--text)' }}>🏆 Top productos — últimos 30 días</div>
          {loading ? <div style={{ color:'var(--muted)', fontSize:13 }}>Cargando…</div> : (
            <div style={{ display:'flex', flexDirection:'column', gap:13 }}>
              {(topProds.length > 0 ? topProds : [
                { product_id:1, product_name:'Nike Air Zoom',   units_sold:28, revenue:1820, pct:100 },
                { product_id:2, product_name:'Medias Pro Run',  units_sold:31, revenue:372,  pct:94  },
                { product_id:3, product_name:'Adidas Run Pro',  units_sold:19, revenue:1102, pct:58  },
                { product_id:4, product_name:'Camiseta Dry-Fit',units_sold:22, revenue:616,  pct:67  },
                { product_id:5, product_name:'Mochila Trail',   units_sold:14, revenue:630,  pct:42  },
              ]).map((p) => (
                <div key={p.product_id}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                    <span style={{ fontSize:12, color:'var(--text)' }}>{p.product_name}</span>
                    <span style={{ fontSize:11, color:'var(--green)', fontFamily:'var(--font-mono)', fontWeight:600 }}>${p.revenue.toFixed(0)}</span>
                  </div>
                  <div style={{ height:4, borderRadius:4, background:'var(--border)' }}>
                    <div style={{ height:'100%', width:`${p.pct}%`, background:'linear-gradient(90deg,var(--green),var(--cyan))', borderRadius:4 }}/>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Funnel */}
      <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:24 }}>
        <div style={{ fontSize:13, fontWeight:600, marginBottom:20, color:'var(--text)' }}>🤖 Embudo de conversión automática</div>
        <div style={{ display:'flex', alignItems:'flex-end', gap:0 }}>
          {FUNNEL.map((s, i) => (
            <div key={i} style={{ flex:1, display:'flex', flexDirection:'column', alignItems:'center', padding:'0 8px', position:'relative' }}>
              {i < 4 && <div style={{ position:'absolute', right:-5, top:'35%', color:'var(--border)', fontSize:20, zIndex:2 }}>›</div>}
              <div style={{
                width:'100%', height:`${s.pct * 1.5 + 30}px`,
                background:`${s.color}12`, border:`1px solid ${s.color}28`,
                borderRadius:10, display:'flex', alignItems:'center', justifyContent:'center', marginBottom:10,
              }}>
                <span style={{ fontFamily:'var(--font-mono)', fontWeight:800, fontSize:22, color:s.color }}>{s.val}</span>
              </div>
              <div style={{ fontSize:11, color:'var(--muted)', textAlign:'center', lineHeight:1.4 }}>{s.label}</div>
              <div style={{ fontSize:12, color:s.color, fontWeight:700, fontFamily:'var(--font-mono)', marginTop:3 }}>{s.pct}%</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop:20, padding:'12px 16px', borderRadius:10, background:'var(--green-dim)', border:'1px solid var(--green-bdr)', display:'flex', justifyContent:'space-between' }}>
          <span style={{ fontSize:13, color:'var(--green)', fontWeight:600 }}>
            💡 Conversión del 32% — 3.2× el promedio de industria (10%)
          </span>
          <span style={{ fontSize:12, color:'var(--muted)' }}>Aria optimiza cada conversación</span>
        </div>
      </div>
    </div>
  );
}
