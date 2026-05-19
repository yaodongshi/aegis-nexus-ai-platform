import React, { useEffect, useState } from 'react';
import { authApi } from '../../lib/api';

export default function ProfilePage() {
  const [user, setUser] = useState<any>(null);
  const [error, setError] = useState('');
  const [editPwd, setEditPwd] = useState(false);
  const [oldPwd, setOldPwd] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    authApi.me().then(setUser).catch(e => setError(e.message));
  }, []);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg('');
    try {
      await authApi.resetPassword(oldPwd, newPwd);
      setMsg('密码修改成功');
      setEditPwd(false);
      setOldPwd(''); setNewPwd('');
    } catch (e: any) {
      setMsg(e.message);
    }
  };

  if (error) return <div style={{ color: 'red' }}>{error}</div>;
  if (!user) return <div>加载中...</div>;

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>个人资料</h1>
      <div style={{ background: '#fff', borderRadius: 8, padding: 24, maxWidth: 480, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
        <Row label="用户名" value={user.username} />
        <Row label="邮箱" value={user.email} />
        <Row label="角色" value={user.role} />
        <div style={{ marginTop: 20 }}>
          {editPwd ? (
            <form onSubmit={handleReset}>
              <Input placeholder="当前密码" type="password" value={oldPwd} onChange={setOldPwd} />
              <Input placeholder="新密码" type="password" value={newPwd} onChange={setNewPwd} />
              {msg && <div style={{ color: msg.includes('成功') ? '#52c41a' : '#ff4d4f', marginBottom: 8 }}>{msg}</div>}
              <button style={btnStyle} type="submit">确认修改</button>
              <button style={{ ...btnStyle, background: '#fff', color: '#333', border: '1px solid #d9d9d9', marginLeft: 8 }} type="button" onClick={() => setEditPwd(false)}>取消</button>
            </form>
          ) : (
            <button style={btnStyle} onClick={() => setEditPwd(true)}>修改密码</button>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', marginBottom: 16, fontSize: 14 }}>
      <span style={{ width: 80, color: '#888' }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}

function Input({ placeholder, type = 'text', value, onChange }: { placeholder: string; type?: string; value: string; onChange: (v: string) => void }) {
  return (
    <input
      placeholder={placeholder}
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{ width: '100%', padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, marginBottom: 10, fontSize: 14 }}
    />
  );
}

const btnStyle: React.CSSProperties = {
  padding: '7px 20px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14,
};
