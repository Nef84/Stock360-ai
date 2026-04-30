import { useEffect, useState, useRef } from 'react';
import toast from 'react-hot-toast';
import { conversationsApi } from '../api/client';
import { Conversation, Message, AIChatResponse, Channel, ConversationStatus } from '../types';

const CH_ICON: Record<Channel, string> = { whatsapp:'📱', messenger:'💬', web:'🌐', manual:'✍️' };
const ST_COLOR: Record<ConversationStatus, string> = {
  open:'var(--green)', in_progress:'var(--cyan)', escalated:'var(--orange)', closed:'var(--dim)'
};
const ST_LABEL: Record<ConversationStatus, string> = {
  open:'🟢 Abierto', in_progress:'💬 En proceso', escalated:'🔴 Escalado', closed:'✅ Cerrado'
};

function initials(name: string) { return name.split(' ').map(n => n[0]).join('').slice(0,2).toUpperCase(); }
function fmtTime(iso: string) { return new Date(iso).toLocaleTimeString('es', { hour:'2-digit', minute:'2-digit' }); }
function nowTime() { return new Date().toLocaleTimeString('es', { hour:'2-digit', minute:'2-digit' }); }

const AVATAR_COLORS = ['#00E676','#00B4D8','#FF6B35','#FFB547','#9B59B6','#E74C3C'];
function avatarColor(id: number) { return AVATAR_COLORS[id % AVATAR_COLORS.length]; }

const DEMO_NAMES = [
  'Luis Herrera','Sofia Castro','Roberto Paz','Elena Mora','Diego Torres','Valeria Quintanilla',
  'Mateo Rivera','Daniela Flores','Andres Mejia','Camila Pineda','Sebastian Ayala','Gabriela Cruz',
  'Javier Escobar','Paola Alvarado','Fernando Ruiz','Lucia Menendez','Oscar Bonilla','Mariana Araujo',
  'Kevin Portillo','Alejandra Rivas','Bryan Aguilar','Natalia Marroquin','Ernesto Campos','Carla Molina',
  'Samuel Hernandez','Andrea Orellana','Ricardo Sorto','Isabella Palma','Mauricio Renderos','Daniela Arce',
];

export default function InboxPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId,      setActiveId]      = useState<number | null>(null);
  const [messages,      setMessages]      = useState<Message[]>([]);
  const [inputMsg,      setInputMsg]      = useState('');
  const [aiTyping,      setAiTyping]      = useState(false);
  const [loading,       setLoading]       = useState(true);
  const [filterStatus,  setFilterStatus]  = useState<string>('all');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const active = conversations.find(c => c.id === activeId) ?? null;

  // Load conversations
  useEffect(() => {
    loadConversations();
    const id = setInterval(loadConversations, 10_000);
    return () => clearInterval(id);
  }, []);

  // Load messages when active changes
  useEffect(() => {
    if (activeId) loadMessages(activeId);
  }, [activeId]);

  // Scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior:'smooth' });
  }, [messages, aiTyping]);

  async function loadConversations() {
    try {
      const { data } = await conversationsApi.list({ limit:100 });
      setConversations(data);
      if (!activeId && data.length > 0) setActiveId(data[0].id);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }

  async function loadMessages(id: number) {
    try {
      const { data } = await conversationsApi.getMessages(id);
      setMessages(data);
    } catch { toast.error('Error cargando mensajes'); }
  }

  async function handleSend() {
    if (!inputMsg.trim() || !activeId || aiTyping) return;
    const text = inputMsg.trim();
    setInputMsg('');
    setAiTyping(true);

    // Optimistic customer message
    const tempMsg: Message = {
      id: Date.now(), conversation_id: activeId, content: text,
      source:'customer', sender_id: null,
      created_at: new Date().toISOString(), is_read: false,
    };
    setMessages(prev => [...prev, tempMsg]);

    try {
      if (!active?.ai_active) {
        const { data } = await conversationsApi.sendMessage(activeId, text);
        setMessages(prev => [
          ...prev.filter(m => m.id !== tempMsg.id),
          data,
        ]);
        toast.success('Mensaje enviado por agente');
        return;
      }

      const { data }: { data: AIChatResponse } = await conversationsApi.aiChat(activeId, text);

      setMessages(prev => [
        ...prev.filter(m => m.id !== tempMsg.id),
        data.message,
        data.ai_response,
      ]);

      // Update conversation status in list
      setConversations(prev => prev.map(c =>
        c.id === activeId
          ? { ...c, status: data.escalated ? 'escalated' : data.sale_detected ? 'closed' : 'in_progress', ai_active: !data.escalated }
          : c
      ));

      if (data.sale_detected) toast.success('💰 ¡Venta cerrada automáticamente por Aria!');
      if (data.escalated)     toast('👤 Chat escalado a agente humano', { icon:'⚠️' });

    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Error de IA');
      setMessages(prev => prev.filter(m => m.id !== tempMsg.id));
    } finally {
      setAiTyping(false);
    }
  }

  async function createDemoConv() {
    try {
      // Create a demo customer + conversation
      const usedNames = new Set(conversations.map(conv => conv.customer.name));
      const availableNames = DEMO_NAMES.filter(name => !usedNames.has(name));
      const pool = availableNames.length > 0 ? availableNames : DEMO_NAMES;
      const name  = pool[Math.floor(Math.random() * pool.length)];
      const { data: customer } = await conversationsApi.createCustomer({ name, channel:'whatsapp' });
      const { data: conv    } = await conversationsApi.create({ customer_id: customer.id, channel:'whatsapp' });
      setConversations(prev => [conv, ...prev]);
      setActiveId(conv.id);
      setMessages([]);
      toast.success(`Nueva conversación con ${name}`);
    } catch { toast.error('Error creando conversación'); }
  }

  async function escalate() {
    if (!activeId) return;
    try {
      await conversationsApi.update(activeId, { ai_active: false, status:'escalated', escalation_reason:'Escalado manualmente por agente' });
      setConversations(prev => prev.map(c => c.id === activeId ? { ...c, ai_active:false, status:'escalated' } : c));
      toast('👤 IA desactivada. Agente tomó el control.', { icon:'🔶' });
    } catch { toast.error('Error al escalar'); }
  }

  async function closeConversation() {
    if (!activeId) return;
    try {
      await conversationsApi.update(activeId, { ai_active: false, status:'closed' });
      setConversations(prev => prev.map(c => c.id === activeId ? { ...c, ai_active:false, status:'closed' } : c));
      toast.success('Conversación cerrada');
    } catch {
      toast.error('Error al cerrar');
    }
  }

  async function hideConversation() {
    if (!activeId) return;
    try {
      await conversationsApi.hide(activeId);
      setConversations(prev => prev.filter(c => c.id !== activeId));
      const nextId = conversations.find(c => c.id !== activeId)?.id ?? null;
      setActiveId(nextId);
      if (nextId) loadMessages(nextId); else setMessages([]);
      toast.success('Conversación ocultada');
    } catch {
      toast.error('Error al ocultar');
    }
  }

  async function hideClosedConversations() {
    try {
      await conversationsApi.hideClosed();
      await loadConversations();
      if (active?.status === 'closed') {
        const nextVisible = conversations.find(c => c.id !== active.id && c.status !== 'closed');
        setActiveId(nextVisible?.id ?? null);
        setMessages([]);
      }
      toast.success('Conversaciones cerradas ocultadas');
    } catch {
      toast.error('Error ocultando conversaciones cerradas');
    }
  }

  const filtered = conversations.filter(c =>
    filterStatus === 'all' || c.status === filterStatus
  );

  if (loading) return (
    <div style={{ height:'100%', display:'flex', alignItems:'center', justifyContent:'center' }}>
      <div style={{ color:'var(--muted)' }}>Cargando conversaciones…</div>
    </div>
  );

  return (
    <div style={{ display:'flex', height:'100%', overflow:'hidden' }}>

      {/* ── Conversation list ──────────────────────────────────────────── */}
      <div style={{ width:300, borderRight:'1px solid var(--border)', display:'flex', flexDirection:'column', overflow:'hidden', flexShrink:0, background:'var(--sidebar)' }}>
        <div style={{ padding:'18px 16px 12px', borderBottom:'1px solid var(--border)' }}>
          <div style={{ fontSize:9, color:'var(--green)', letterSpacing:4, fontFamily:'var(--font-mono)', marginBottom:6 }}>BANDEJA · ARIA IA</div>
          <h2 style={{ fontSize:17, fontWeight:800, color:'var(--text)', margin:0 }}>Conversaciones</h2>
          <div style={{ marginTop:10 }}>
            <button onClick={hideClosedConversations} style={{
              fontSize:10, padding:'5px 10px', borderRadius:8, cursor:'pointer',
              border:'1px solid var(--border)', background:'var(--panel)', color:'var(--muted)',
              fontFamily:'var(--font-body)',
            }}>
              Ocultar cerradas
            </button>
          </div>
          <div style={{ display:'flex', gap:5, marginTop:10, flexWrap:'wrap' }}>
            {['all','open','in_progress','escalated','closed'].map(s => (
              <button key={s} onClick={() => setFilterStatus(s)} style={{
                fontSize:10, padding:'3px 10px', borderRadius:16, cursor:'pointer', fontFamily:'var(--font-body)',
                background: filterStatus===s ? 'var(--green)' : 'transparent',
                color:      filterStatus===s ? 'var(--bg)'    : 'var(--muted)',
                border:    `1px solid ${filterStatus===s ? 'var(--green)' : 'var(--border)'}`,
                fontWeight: filterStatus===s ? 700 : 400,
              }}>
                {s==='all'?'Todos':s==='in_progress'?'Activos':s.charAt(0).toUpperCase()+s.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ flex:1, overflowY:'auto' }}>
          {filtered.length === 0 && (
            <div style={{ padding:24, textAlign:'center', color:'var(--dim)', fontSize:13 }}>
              Sin conversaciones
            </div>
          )}
          {filtered.map(conv => (
            <div key={conv.id} onClick={() => { setActiveId(conv.id); loadMessages(conv.id); }}
              style={{
                padding:'12px 14px', cursor:'pointer',
                background: activeId===conv.id ? 'var(--green-dim)' : 'transparent',
                borderLeft: `3px solid ${activeId===conv.id ? 'var(--green)' : 'transparent'}`,
                borderBottom:'1px solid var(--border)', transition:'background 0.15s',
              }}
            >
              <div style={{ display:'flex', gap:9, alignItems:'flex-start' }}>
                <div style={{
                  width:38, height:38, borderRadius:'50%', flexShrink:0,
                  background:`linear-gradient(135deg,${avatarColor(conv.customer.id)},${avatarColor(conv.customer.id)}88)`,
                  display:'flex', alignItems:'center', justifyContent:'center',
                  fontSize:12, fontWeight:800, color:'var(--bg)',
                }}>
                  {initials(conv.customer.name)}
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', marginBottom:2 }}>
                    <span style={{ fontSize:12, fontWeight:700, color:'var(--text)' }}>{conv.customer.name}</span>
                    <span style={{ fontSize:10, color:'var(--muted)' }}>{fmtTime(conv.updated_at)}</span>
                  </div>
                  <div style={{ display:'flex', gap:5, alignItems:'center', marginTop:3 }}>
                    <span style={{ fontSize:11 }}>{CH_ICON[conv.channel]}</span>
                    <span style={{ fontSize:10, color: ST_COLOR[conv.status] }}>{ST_LABEL[conv.status]}</span>
                    {conv.ai_active && <span style={{ marginLeft:'auto', fontSize:9, color:'var(--green)', background:'var(--green-dim)', border:'1px solid var(--green-bdr)', padding:'1px 6px', borderRadius:8 }}>🤖 IA</span>}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ padding:12, borderTop:'1px solid var(--border)' }}>
          <button onClick={createDemoConv} style={{
            width:'100%', padding:'9px', borderRadius:10,
            border:'1px dashed var(--green)', background:'var(--green-dim)',
            color:'var(--green)', fontSize:12, fontWeight:600,
            cursor:'pointer', fontFamily:'var(--font-body)',
          }}>
            + Nuevo chat demo
          </button>
        </div>
      </div>

      {/* ── Chat window ────────────────────────────────────────────────── */}
      {active ? (
        <div style={{ flex:1, display:'flex', flexDirection:'column', overflow:'hidden' }}>
          {/* Header */}
          <div style={{ padding:'12px 18px', borderBottom:'1px solid var(--border)', display:'flex', alignItems:'center', gap:12, background:'var(--sidebar)', flexShrink:0 }}>
            <div style={{ width:40, height:40, borderRadius:'50%', background:`linear-gradient(135deg,${avatarColor(active.customer.id)},${avatarColor(active.customer.id)}88)`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:800, color:'var(--bg)' }}>
              {initials(active.customer.name)}
            </div>
            <div style={{ flex:1 }}>
              <div style={{ fontWeight:700, fontSize:14, color:'var(--text)' }}>{active.customer.name}</div>
              <div style={{ fontSize:11, color: active.ai_active ? 'var(--green)' : 'var(--orange)', display:'flex', alignItems:'center', gap:5 }}>
                {active.ai_active
                  ? <><span style={{ width:5, height:5, borderRadius:'50%', background:'var(--green)', animation:'blink 2s infinite', display:'inline-block' }}/> 🤖 Aria (IA) · {CH_ICON[active.channel]} {active.channel}</>
                  : <>👤 Agente humano · {CH_ICON[active.channel]} {active.channel}</>
                }
              </div>
            </div>
            <div style={{ display:'flex', gap:8 }}>
              {active.ai_active && (
                <button onClick={escalate} style={{ background:'var(--orange-dim)', border:'1px solid rgba(255,107,53,0.3)', color:'var(--orange)', borderRadius:8, padding:'7px 12px', fontSize:12, cursor:'pointer', fontFamily:'var(--font-body)', fontWeight:600 }}>
                  👤 Escalar humano
                </button>
              )}
              {active.status !== 'closed' && (
                <button onClick={closeConversation} style={{ background:'var(--panel)', border:'1px solid var(--border)', color:'var(--muted)', borderRadius:8, padding:'7px 12px', fontSize:12, cursor:'pointer', fontFamily:'var(--font-body)', fontWeight:600 }}>
                  Cerrar chat
                </button>
              )}
              <button onClick={hideConversation} style={{ background:'var(--panel)', border:'1px solid var(--border)', color:'var(--muted)', borderRadius:8, padding:'7px 12px', fontSize:12, cursor:'pointer', fontFamily:'var(--font-body)', fontWeight:600 }}>
                Ocultar
              </button>
              <div style={{ fontSize:11, padding:'4px 10px', borderRadius:8, background:'var(--panel)', border:'1px solid var(--border)', color: ST_COLOR[active.status] }}>
                {ST_LABEL[active.status]}
              </div>
            </div>
          </div>

          {/* Messages */}
          <div style={{ flex:1, overflowY:'auto', padding:'18px 20px', display:'flex', flexDirection:'column', gap:10 }}>
            {messages.length === 0 && (
              <div style={{ alignSelf:'center', color:'var(--dim)', fontSize:13, marginTop:40, textAlign:'center' }}>
                Chat vacío.<br/>Escribe el primer mensaje del cliente ↓
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id} style={{ display:'flex', justifyContent: msg.source==='customer'?'flex-start':'flex-end', alignItems:'flex-end', gap:8 }}>
                {msg.source==='customer' && (
                  <div style={{ width:28, height:28, borderRadius:'50%', background:`linear-gradient(135deg,${avatarColor(active.customer.id)},${avatarColor(active.customer.id)}88)`, display:'flex', alignItems:'center', justifyContent:'center', fontSize:10, fontWeight:800, color:'var(--bg)', flexShrink:0 }}>
                    {initials(active.customer.name)}
                  </div>
                )}
                <div style={{ maxWidth:'66%' }}>
                  {msg.source==='ai' && <div style={{ fontSize:9, color:'var(--green)', marginBottom:3, fontWeight:700, textAlign:'right', fontFamily:'var(--font-mono)' }}>🤖 ARIA · IA</div>}
                  {msg.source==='agent' && <div style={{ fontSize:9, color:'var(--cyan)', marginBottom:3, fontWeight:700, textAlign:'right' }}>👤 AGENTE</div>}
                  <div style={{
                    padding:'10px 14px', fontSize:13, lineHeight:1.55, color:'var(--text)', whiteSpace:'pre-wrap',
                    borderRadius: msg.source==='customer' ? '14px 14px 14px 4px' : '14px 14px 4px 14px',
                    background: msg.source==='customer' ? 'var(--panel2)' : msg.source==='ai' ? 'linear-gradient(135deg,rgba(0,230,118,0.10),rgba(0,180,216,0.06))' : 'var(--cyan-dim)',
                    border:`1px solid ${msg.source==='customer'?'var(--border)':msg.source==='ai'?'var(--green-bdr)':'rgba(0,180,216,0.25)'}`,
                  }}>
                    {msg.content}
                  </div>
                  <div style={{ fontSize:10, color:'var(--dim)', marginTop:2, textAlign: msg.source==='customer'?'left':'right' }}>
                    {fmtTime(msg.created_at)}
                  </div>
                </div>
              </div>
            ))}

            {aiTyping && (
              <div style={{ display:'flex', justifyContent:'flex-end', alignItems:'center' }}>
                <div style={{ padding:'10px 14px', borderRadius:'14px 14px 4px 14px', background:'var(--green-dim)', border:'1px solid var(--green-bdr)', display:'flex', alignItems:'center', gap:5 }}>
                  {[0,1,2].map(j => (
                    <div key={j} style={{ width:6, height:6, borderRadius:'50%', background:'var(--green)', animation:`pulse-dot 1s ${j*0.2}s infinite` }}/>
                  ))}
                  <span style={{ fontSize:11, color:'var(--green)', marginLeft:4 }}>Aria escribiendo…</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef}/>
          </div>

          {/* Input */}
          <div style={{ padding:'12px 18px', borderTop:'1px solid var(--border)', display:'flex', gap:10, background:'var(--sidebar)', flexShrink:0 }}>
            <input
              value={inputMsg}
              onChange={e => setInputMsg(e.target.value)}
              onKeyDown={e => e.key==='Enter' && !e.shiftKey && handleSend()}
              placeholder={active.ai_active ? 'Escribe como el cliente… Aria responde con IA real 🤖' : 'Modo agente humano — responde directamente…'}
              disabled={aiTyping}
              style={{
                flex:1, background:'var(--panel2)', border:'1px solid var(--border)',
                borderRadius:'var(--radius)', padding:'11px 14px', color:'var(--text)',
                fontSize:13, transition:'border 0.15s',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--green)')}
              onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
            />
            <button onClick={handleSend} disabled={aiTyping || !inputMsg.trim()} style={{
              width:46, height:46, borderRadius:'var(--radius)', border:'none',
              cursor: (aiTyping || !inputMsg.trim()) ? 'not-allowed' : 'pointer',
              background: (aiTyping || !inputMsg.trim()) ? 'var(--border)' : 'linear-gradient(135deg,var(--green),var(--cyan))',
              fontSize:18, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
            }}>
              {aiTyping ? '⏳' : '➤'}
            </button>
          </div>
        </div>
      ) : (
        <div style={{ flex:1, display:'flex', alignItems:'center', justifyContent:'center' }}>
          <div style={{ textAlign:'center', color:'var(--dim)' }}>
            <div style={{ fontSize:40, marginBottom:12 }}>💬</div>
            <div style={{ fontSize:14 }}>Selecciona o crea una conversación</div>
          </div>
        </div>
      )}
    </div>
  );
}
