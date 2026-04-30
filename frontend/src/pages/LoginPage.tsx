import { useState, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { authApi } from '../api/client';
import { useAuthStore } from '../store/auth';
import { TokenResponse } from '../types';

export default function LoginPage() {
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [loading,  setLoading]  = useState(false);
  const { login } = useAuthStore();
  const navigate  = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await authApi.login(email, password);
      const res = data as TokenResponse;
      login(res.user, res.access_token, res.refresh_token);
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Credenciales incorrectas');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      height:'100vh', display:'flex', alignItems:'center', justifyContent:'center',
      background:'var(--bg)',
      backgroundImage:'radial-gradient(ellipse at 20% 50%, rgba(0,230,118,0.06) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(0,180,216,0.05) 0%, transparent 50%)',
    }}>
      <div style={{ width:400, animation:'fadeIn 0.3s ease' }}>
        {/* Header */}
        <div style={{ textAlign:'center', marginBottom:36 }}>
          <div style={{
            width:60, height:60, borderRadius:16,
            background:'linear-gradient(135deg, var(--green), var(--cyan))',
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:28, margin:'0 auto 16px',
          }}>⚡</div>
          <h1 style={{ fontSize:28, fontWeight:800, color:'var(--text)', marginBottom:6 }}>
            Stock360 <span style={{ color:'var(--green)' }}>AI</span>
          </h1>
          <p style={{ fontSize:13, color:'var(--muted)' }}>
            Tu vendedor digital 24/7 — accede al panel
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{
          background:'var(--panel)', border:'1px solid var(--border)',
          borderRadius:'var(--radius-lg)', padding:32,
        }}>
          <div style={{ marginBottom:18 }}>
            <label style={{ display:'block', fontSize:12, color:'var(--muted)', fontWeight:600, marginBottom:6 }}>
              CORREO ELECTRÓNICO
            </label>
            <input
              type="email" required value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="admin@stock360.ai"
              style={{
                width:'100%', padding:'11px 14px',
                background:'var(--panel2)', border:'1px solid var(--border)',
                borderRadius:'var(--radius-sm)', color:'var(--text)', fontSize:14,
                transition:'border 0.15s',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--green)')}
              onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>

          <div style={{ marginBottom:24 }}>
            <label style={{ display:'block', fontSize:12, color:'var(--muted)', fontWeight:600, marginBottom:6 }}>
              CONTRASEÑA
            </label>
            <input
              type="password" required value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              style={{
                width:'100%', padding:'11px 14px',
                background:'var(--panel2)', border:'1px solid var(--border)',
                borderRadius:'var(--radius-sm)', color:'var(--text)', fontSize:14,
                transition:'border 0.15s',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--green)')}
              onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
            />
          </div>

          <button
            type="submit" disabled={loading}
            style={{
              width:'100%', padding:'13px',
              background: loading ? 'var(--border)' : 'linear-gradient(135deg, var(--green), var(--cyan))',
              border:'none', borderRadius:'var(--radius-sm)',
              color: loading ? 'var(--muted)' : 'var(--bg)',
              fontSize:15, fontWeight:700, cursor: loading ? 'not-allowed' : 'pointer',
              transition:'opacity 0.15s',
            }}
          >
            {loading ? '⏳ Ingresando...' : '🚀 Ingresar al panel'}
          </button>

          <p style={{ marginTop:16, textAlign:'center', fontSize:12, color:'var(--dim)' }}>
            Primera vez: usa las credenciales del archivo <code style={{ color:'var(--green)' }}>.env</code>
          </p>
        </form>
      </div>
    </div>
  );
}
