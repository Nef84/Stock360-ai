import { useEffect, useRef, useState } from 'react';
import toast from 'react-hot-toast';
import { productsApi } from '../api/client';
import { Product, ProductCreate, ProductImportResult } from '../types';

const CATEGORIES = ['Todos','Calzado','Ropa','Accesorios'];

export default function InventoryPage() {
  const [products,  setProducts]  = useState<Product[]>([]);
  const [loading,   setLoading]   = useState(true);
  const [catFilter, setCatFilter] = useState('Todos');
  const [showModal, setShowModal] = useState(false);
  const [form,      setForm]      = useState<Partial<ProductCreate>>({ ai_priority:5, stock:0, cost:0, margin_pct:0 });
  const [saving,    setSaving]    = useState(false);
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { load(); }, []);

  async function load() {
    try {
      const { data } = await productsApi.list({ active_only:false });
      setProducts(data);
    } catch { toast.error('Error cargando productos'); }
    finally { setLoading(false); }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await productsApi.create(form);
      toast.success('Producto creado');
      setShowModal(false);
      setForm({ ai_priority:5, stock:0, cost:0, margin_pct:0 });
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Error al crear');
    } finally { setSaving(false); }
  }

  async function toggleActive(p: Product) {
    try {
      await productsApi.update(p.id, { is_active: !p.is_active });
      toast.success(p.is_active ? 'Producto desactivado' : 'Producto activado');
      load();
    } catch { toast.error('Error al actualizar'); }
  }

  async function adjustStock(p: Product, delta: number) {
    const reason = delta > 0 ? 'Restock manual' : 'Ajuste manual';
    try {
      await productsApi.adjustStock(p.id, delta, reason);
      toast.success(`Stock actualizado: ${p.stock + delta} uds`);
      load();
    } catch (err: any) { toast.error(err?.response?.data?.detail ?? 'Error'); }
  }

  async function handleImportFile(file?: File | null) {
    if (!file) return;
    setImporting(true);
    try {
      const { data }: { data: ProductImportResult } = await productsApi.importFile(file);
      toast.success(`Importación lista: ${data.created} creados, ${data.updated} actualizados`);
      if (data.skipped > 0) {
        toast(`${data.skipped} filas se omitieron`, { icon:'⚠️' });
      }
      load();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Error importando archivo');
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  const filtered = catFilter === 'Todos' ? products : products.filter(p => p.category === catFilter);

  return (
    <div style={{ padding:24, overflowY:'auto', height:'100%' }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:24 }}>
        <div>
          <div style={{ fontSize:9, color:'var(--green)', letterSpacing:4, fontFamily:'var(--font-mono)', marginBottom:8 }}>INVENTARIO · CONECTADO A IA</div>
          <h1 style={{ fontSize:24, fontWeight:800, color:'var(--text)' }}>Productos <span style={{ color:'var(--green)' }}>Activos</span></h1>
          <p style={{ fontSize:13, color:'var(--muted)', marginTop:4 }}>Aria consulta este inventario en tiempo real. El stock se descuenta automáticamente al cerrar ventas.</p>
        </div>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            style={{ display:'none' }}
            onChange={e => handleImportFile(e.target.files?.[0])}
          />
          <button onClick={() => fileInputRef.current?.click()} disabled={importing} style={{
            padding:'10px 18px', borderRadius:'var(--radius)', border:'1px solid var(--border)',
            background:'var(--panel)', color:'var(--text)', fontSize:13, fontWeight:700,
            cursor: importing ? 'not-allowed' : 'pointer', fontFamily:'var(--font-body)',
          }}>
            {importing ? 'Importando…' : 'Importar CSV/Excel'}
          </button>
          <button onClick={() => setShowModal(true)} style={{
            padding:'10px 20px', borderRadius:'var(--radius)', border:'none',
            background:'linear-gradient(135deg,var(--green),var(--cyan))',
            color:'var(--bg)', fontSize:13, fontWeight:700, cursor:'pointer',
            fontFamily:'var(--font-body)',
          }}>
            + Nuevo producto
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={{ display:'flex', gap:8, marginBottom:20 }}>
        {CATEGORIES.map(c => (
          <button key={c} onClick={() => setCatFilter(c)} style={{
            padding:'6px 16px', borderRadius:20, fontSize:12, cursor:'pointer',
            fontFamily:'var(--font-body)', fontWeight: catFilter===c ? 700 : 400,
            background: catFilter===c ? 'var(--green)' : 'transparent',
            color:      catFilter===c ? 'var(--bg)'    : 'var(--muted)',
            border:    `1px solid ${catFilter===c ? 'var(--green)' : 'var(--border)'}`,
          }}>{c}</button>
        ))}
        <div style={{ marginLeft:'auto', fontSize:12, color:'var(--muted)', alignSelf:'center' }}>
          {filtered.length} productos
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign:'center', color:'var(--muted)', marginTop:60 }}>Cargando…</div>
      ) : (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(260px,1fr))', gap:14 }}>
          {filtered.map(p => <ProductCard key={p.id} product={p} onToggle={toggleActive} onStock={adjustStock}/>)}
        </div>
      )}

      {/* Create modal */}
      {showModal && (
        <Modal title="➕ Nuevo producto" onClose={() => setShowModal(false)}>
          <form onSubmit={handleCreate} style={{ display:'flex', flexDirection:'column', gap:14 }}>
            {[
              { label:'Nombre',      key:'name',        type:'text',   req:true },
              { label:'Categoría',   key:'category',    type:'text',   req:true },
              { label:'Descripción', key:'description', type:'text',   req:false },
              { label:'Precio ($)',  key:'price',       type:'number', req:true },
              { label:'Costo ($)',   key:'cost',        type:'number', req:false },
              { label:'Stock',       key:'stock',       type:'number', req:false },
              { label:'Margen (%)',  key:'margin_pct',  type:'number', req:false },
              { label:'Prioridad IA (1-10)', key:'ai_priority', type:'number', req:false },
            ].map(f => (
              <div key={f.key}>
                <label style={{ fontSize:11, color:'var(--muted)', fontWeight:600, display:'block', marginBottom:4 }}>{f.label.toUpperCase()}</label>
                <input
                  type={f.type} required={f.req} min={f.type==='number'?0:undefined}
                  value={(form as any)[f.key] ?? ''}
                  onChange={e => setForm(prev => ({ ...prev, [f.key]: f.type==='number' ? parseFloat(e.target.value)||0 : e.target.value }))}
                  style={{ width:'100%', padding:'9px 12px', background:'var(--panel2)', border:'1px solid var(--border)', borderRadius:'var(--radius-sm)', color:'var(--text)', fontSize:13 }}
                />
              </div>
            ))}
            <button type="submit" disabled={saving} style={{ padding:'11px', borderRadius:'var(--radius-sm)', border:'none', background:'linear-gradient(135deg,var(--green),var(--cyan))', color:'var(--bg)', fontSize:14, fontWeight:700, cursor:saving?'not-allowed':'pointer', fontFamily:'var(--font-body)' }}>
              {saving ? 'Guardando…' : '✅ Crear producto'}
            </button>
          </form>
        </Modal>
      )}
    </div>
  );
}

function ProductCard({ product: p, onToggle, onStock }:
  { product:Product; onToggle:(p:Product)=>void; onStock:(p:Product,d:number)=>void }
) {
  const barColor = p.available_stock > 10 ? 'var(--green)' : p.available_stock > 3 ? 'var(--yellow)' : 'var(--orange)';
  const barPct   = Math.min((p.available_stock / 50) * 100, 100);

  return (
    <div style={{
      background:'var(--panel)', border:`1px solid ${p.is_active?'var(--border)':'rgba(255,75,75,0.2)'}`,
      borderRadius:14, padding:18, position:'relative', overflow:'hidden', opacity: p.is_active ? 1 : 0.65,
    }}>
      <div style={{ position:'absolute', top:0, left:0, right:0, height:2, background:`linear-gradient(90deg,${barColor},transparent)` }}/>

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
        <span style={{ fontSize:10, padding:'3px 8px', borderRadius:6, background:'rgba(255,255,255,0.05)', color:'var(--muted)' }}>
          {p.category}
        </span>
        <div style={{ display:'flex', alignItems:'center', gap:6 }}>
          <span style={{ fontSize:10, color:'var(--green)', fontFamily:'var(--font-mono)' }}>⭐ {p.ai_priority}/10</span>
          <button onClick={() => onToggle(p)} style={{ fontSize:11, padding:'2px 8px', borderRadius:6, border:`1px solid ${p.is_active?'rgba(0,230,118,0.3)':'rgba(255,75,75,0.3)'}`, background:'transparent', color: p.is_active?'var(--green)':'var(--red)', cursor:'pointer', fontFamily:'var(--font-body)' }}>
            {p.is_active ? '✓ Activo' : '✗ Inactivo'}
          </button>
        </div>
      </div>

      <div style={{ fontWeight:700, fontSize:15, color:'var(--text)', marginBottom:4 }}>{p.name}</div>
      {p.description && <div style={{ fontSize:12, color:'var(--muted)', marginBottom:12, lineHeight:1.4 }}>{p.description}</div>}

      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
        <span style={{ fontSize:26, fontWeight:800, color:'var(--green)', fontFamily:'var(--font-mono)' }}>${p.price}</span>
        <span style={{ fontSize:11, color:'var(--cyan)' }}>Margen {p.margin_pct.toFixed(0)}%</span>
      </div>

      <div style={{ height:4, borderRadius:4, background:'var(--border)', marginBottom:8 }}>
        <div style={{ height:'100%', width:`${barPct}%`, background:barColor, borderRadius:4, transition:'width 0.5s' }}/>
      </div>

      <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between' }}>
        <span style={{ fontSize:12, color:barColor, fontFamily:'var(--font-mono)' }}>
          {p.available_stock} uds disponibles
        </span>
        <div style={{ display:'flex', gap:6 }}>
          <button onClick={() => onStock(p, -1)} disabled={p.available_stock <= 0} style={{ width:26, height:26, borderRadius:6, border:'1px solid var(--border)', background:'transparent', color:'var(--orange)', cursor:'pointer', fontSize:14, display:'flex', alignItems:'center', justifyContent:'center' }}>−</button>
          <button onClick={() => onStock(p,  5)} style={{ width:26, height:26, borderRadius:6, border:'1px solid var(--border)', background:'transparent', color:'var(--green)',  cursor:'pointer', fontSize:14, display:'flex', alignItems:'center', justifyContent:'center' }}>+</button>
        </div>
      </div>

      {p.available_stock <= 3 && p.available_stock > 0 && (
        <div style={{ marginTop:8, fontSize:11, color:'var(--orange)' }}>⚠️ Stock bajo — Aria priorizará cross-sell</div>
      )}
      {p.available_stock === 0 && (
        <div style={{ marginTop:8, fontSize:11, color:'var(--red)' }}>🚫 Sin stock — Aria no ofrecerá este producto</div>
      )}
    </div>
  );
}

function Modal({ title, onClose, children }: { title:string; onClose:()=>void; children:React.ReactNode }) {
  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.7)', display:'flex', alignItems:'center', justifyContent:'center', zIndex:1000 }} onClick={onClose}>
      <div style={{ background:'var(--panel)', border:'1px solid var(--border)', borderRadius:16, padding:28, width:440, maxHeight:'85vh', overflowY:'auto' }} onClick={e => e.stopPropagation()}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
          <h2 style={{ fontSize:17, fontWeight:700, color:'var(--text)', margin:0 }}>{title}</h2>
          <button onClick={onClose} style={{ background:'none', border:'none', color:'var(--muted)', fontSize:20, cursor:'pointer' }}>×</button>
        </div>
        {children}
      </div>
    </div>
  );
}
