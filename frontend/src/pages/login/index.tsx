import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi, setToken } from '../../lib/api';

type Mode = 'login' | 'register';

const S = {
  page: { height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f7fa' } as React.CSSProperties,
  card: { width: 360, padding: 32, boxShadow: '0 2px 12px rgba(0,0,0,.1)', borderRadius: 8, background: '#fff' } as React.CSSProperties,
  title: { textAlign: 'center' as const, marginBottom: 24, fontSize: 20, fontWeight: 700 },
  field: { marginBottom: 14 } as React.CSSProperties,
  input: { width: '100%', padding: '8px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14 } as React.CSSProperties,
  btn: { width: '100%', padding: '9px 0', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 15, marginTop: 8 } as React.CSSProperties,
  link: { textAlign: 'center' as const, marginTop: 16, fontSize: 13, color: '#888' },
  error: { color: '#ff4d4f', fontSize: 13, marginTop: 8 } as React.CSSProperties,
};

export default function LoginPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('login');
  const [identity, setIdentity] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'register') {
        await authApi.register(username, email, password);
        // Auto-login after register
        const data = await authApi.login(email, password);
        setToken(data.access_token);
      } else {
        const data = await authApi.login(identity, password);
        setToken(data.access_token);
      }
      navigate('/');
    } catch (err: any) {
      setError(err.message ?? '操作失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={S.page}>
      <div style={S.card}>
        <h2 style={S.title}>Team AI Platform</h2>
        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <>
              <div style={S.field}>
                <input style={S.input} placeholder="用户名" value={username} onChange={e => setUsername(e.target.value)} required />
              </div>
              <div style={S.field}>
                <input style={S.input} placeholder="邮箱" type="email" value={email} onChange={e => setEmail(e.target.value)} required />
              </div>
            </>
          )}
          {mode === 'login' && (
            <div style={S.field}>
              <input style={S.input} placeholder="邮箱 / 用户名" value={identity} onChange={e => setIdentity(e.target.value)} required />
            </div>
          )}
          <div style={S.field}>
            <input style={S.input} placeholder="密码" type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          {error && <div style={S.error}>{error}</div>}
          <button style={S.btn} type="submit" disabled={loading}>
            {loading ? '请稍候...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>
        <div style={S.link}>
          {mode === 'login' ? (
            <>还没有账号？<span style={{ color: '#1677ff', cursor: 'pointer' }} onClick={() => setMode('register')}>立即注册</span></>
          ) : (
            <>已有账号？<span style={{ color: '#1677ff', cursor: 'pointer' }} onClick={() => setMode('login')}>去登录</span></>
          )}
        </div>
      </div>
    </div>
  );
}
