import { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { analyticsApi } from '../api/client';
import { Sale } from '../types';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

const STATUS_COLOR: Record<string, string> = {
  pending:'var(--yellow)', confirmed:'var(--green)', shipped:'var(--cyan)',
  delivered:'#9B59B6', cancelled:'var(--red)',
};
const STATUS_LABEL: Record<string, string> = {
  pending:'⏳ Pendiente', confirmed:'✅ Confirmado', shipped:'📦 Enviado',
  delivered:'🎉 Entregado', cancelled:'❌ Cancelado',
};

export default function SalesPage() {
  const [sales,   setSales]   = useState<Sale[]>([]);
  const [loading, setLoading] = useState(true);
  const [aiOnly,  setAiOnly]  = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const { data } = await analyticsApi.sales({ limit:100 });
        setSales(data);
      } catch { toast.error('Error cargando ventas'); }
      finally { setLoading(false); }
    }
    load();
    const id = setInterval(load, 15_000);
    return () => clearInterval(id);
  }, []);

  const filtered = aiOnly ? sales.filter(s => s.closed_by_ai) : sales;
  const totalAI    = sales.filter(s => s.closed_by_ai).reduce((a, s) => a + s.total, 0);
  const totalHuman = sales.filter(s => !s.closed_by_ai).reduce((a, s) => a + s.total, 0);

  return (
    <div style={{ padding:24, overflowY:'auto', height:'100%' }}>
      <div style={{ marginBottom:24 }}>
        <div style={{ fontSize:9, color:'var(--green)', letterSpacing:4, fontFamily:'var(--font-mono)', marginBottom:8 }}>REGISTRO DE VENTAS</div>
        <h1 style={{ fontSize:24, fontWeight:800, color:'var(--text)', margin:0 }}>Historial de <span style={{ color:'var(--green)' }}>Ventas</span></h1>
        <p style={{ fontSize:13, color:'var(--muted)', marginTop:4 }}>Todas las ventas cerradas — por IA y por agentes humanos</p>
      </div>

      {/* Summary */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:14, marginBottom:24 }}>
        <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:18, position:'relative', overflow:'hidden' }}>
          <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:'linear-gradient(90deg,var(--green),transparent)' }}/>
          <div style={{ fontSize:11, color:'var(--muted)', marginBottom:6 }}>💰 Total ventas IA</div>
          <div style={{ fontSize:28, fontWeight:800, color:'var(--green)', fontFamily:'var(--font-mono)' }}>${totalAI.toFixed(2)}</div>
          <div style={{ fontSize:11, color:'var(--green)', marginTop:4 }}>🤖 {sales.filter(s=>s.closed_by_ai).length} transacciones</div>
        </div>
        <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:18, position:'relative', overflow:'hidden' }}>
          <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:'linear-gradient(90deg,var(--cyan),transparent)' }}/>
          <div style={{ fontSize:11, color:'var(--muted)', marginBottom:6 }}>👤 Total ventas humanas</div>
          <div style={{ fontSize:28, fontWeight:800, color:'var(--cyan)', fontFamily:'var(--font-mono)' }}>${totalHuman.toFixed(2)}</div>
          <div style={{ fontSize:11, color:'var(--cyan)', marginTop:4 }}>👤 {sales.filter(s=>!s.closed_by_ai).length} transacciones</div>
        </div>
        <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, padding:18, position:'relative', overflow:'hidden' }}>
          <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:'linear-gradient(90deg,var(--orange),transparent)' }}/>
          <div style={{ fontSize:11, color:'var(--muted)', marginBottom:6 }}>📊 % Ventas por IA</div>
          <div style={{ fontSize:28, fontWeight:800, color:'var(--orange)', fontFamily:'var(--font-mono)' }}>
            {sales.length > 0 ? Math.round((sales.filter(s=>s.closed_by_ai).length / sales.length) * 100) : 0}%
          </div>
          <div style={{ fontSize:11, color:'var(--orange)', marginTop:4 }}>de {sales.length} ventas totales</div>
        </div>
      </div>

      {/* Filter */}
      <div style={{ display:'flex', gap:10, marginBottom:16, alignItems:'center' }}>
        <button onClick={() => setAiOnly(!aiOnly)} style={{
          padding:'6px 16px', borderRadius:20, fontSize:12, cursor:'pointer', fontFamily:'var(--font-body)',
          background: aiOnly ? 'var(--green)' : 'transparent',
          color:      aiOnly ? 'var(--bg)'    : 'var(--muted)',
          border:    `1px solid ${aiOnly ? 'var(--green)' : 'var(--border)'}`,
          fontWeight: aiOnly ? 700 : 400,
        }}>
          🤖 Solo ventas IA
        </button>
        <span style={{ fontSize:12, color:'var(--muted)' }}>{filtered.length} registros</span>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ textAlign:'center', color:'var(--muted)', marginTop:60 }}>Cargando ventas…</div>
      ) : filtered.length === 0 ? (
        <div style={{ textAlign:'center', color:'var(--dim)', marginTop:60, fontSize:14 }}>
          <div style={{ fontSize:36, marginBottom:12 }}>💰</div>
          Sin ventas registradas aún.<br/>Las ventas aparecerán aquí cuando Aria cierre su primera conversación.
        </div>
      ) : (
        <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:14, overflow:'hidden' }}>
          <div style={{ display:'grid', gridTemplateColumns:'2fr 2fr 1fr 1fr 1fr 1fr', padding:'12px 16px', borderBottom:'1px solid var(--border)', fontSize:10, color:'var(--muted)', fontWeight:600, letterSpacing:1 }}>
            <span>PRODUCTO</span>
            <span>CLIENTE</span>
            <span>TOTAL</span>
            <span>ESTADO</span>
            <span>CANAL</span>
            <span>FECHA</span>
          </div>
          {filtered.map(sale => (
            <div key={sale.id} style={{ display:'grid', gridTemplateColumns:'2fr 2fr 1fr 1fr 1fr 1fr', padding:'13px 16px', borderBottom:'1px solid var(--border)', alignItems:'center', transition:'background 0.1s' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--panel2)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <div>
                <div style={{ fontSize:13, fontWeight:600, color:'var(--text)' }}>{sale.product.name}</div>
                <div style={{ fontSize:11, color:'var(--muted)' }}>x{sale.quantity} · ${sale.unit_price} c/u</div>
              </div>
              <div style={{ fontSize:13, color:'var(--text)' }}>{sale.customer.name}</div>
              <div style={{ fontSize:14, fontWeight:700, color:'var(--green)', fontFamily:'var(--font-mono)' }}>${sale.total.toFixed(2)}</div>
              <div style={{ fontSize:11, color: STATUS_COLOR[sale.status] }}>{STATUS_LABEL[sale.status]}</div>
              <div style={{ display:'flex', alignItems:'center', gap:5 }}>
                {sale.closed_by_ai
                  ? <span style={{ fontSize:11, color:'var(--green)', background:'var(--green-dim)', border:'1px solid var(--green-bdr)', padding:'2px 7px', borderRadius:8 }}>🤖 IA</span>
                  : <span style={{ fontSize:11, color:'var(--cyan)',  background:'var(--cyan-dim)',  border:'1px solid rgba(0,180,216,0.25)', padding:'2px 7px', borderRadius:8 }}>👤 Agente</span>
                }
              </div>
              <div style={{ fontSize:11, color:'var(--muted)' }}>
                {format(new Date(sale.created_at), 'dd MMM HH:mm', { locale: es })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
