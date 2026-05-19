import React, { useEffect, useState } from 'react';
import { teamsApi } from '../../lib/api';

export default function TeamPage() {
  const [teams, setTeams] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = () => teamsApi.list().then(setTeams).catch(e => setError(e.message));
  useEffect(() => { load(); }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await teamsApi.create(name, desc);
      setName(''); setDesc(''); setShowForm(false);
      load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  return (
    <div>
      <div style={{ marginBottom: 12, border: '1px solid #ffd591', background: '#fff7e6', color: '#ad6800', borderRadius: 8, padding: '10px 12px', fontSize: 13 }}>
        兼容模式：团队模块已降级为历史兼容能力，不再作为主线导航入口。建议优先使用技能、治理、观测等 AI 主线模块。
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>团队管理</h1>
        <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 创建团队</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {showForm && (
        <form onSubmit={handleCreate} style={formStyle}>
          <input style={inputStyle} placeholder="团队名称" value={name} onChange={e => setName(e.target.value)} required />
          <input style={inputStyle} placeholder="描述（可选）" value={desc} onChange={e => setDesc(e.target.value)} />
          <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '创建中...' : '确认创建'}</button>
        </form>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16, marginTop: 16 }}>
        {teams.map(t => (
          <div key={t.id} style={cardStyle}>
            <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>{t.name}</div>
            <div style={{ color: '#888', fontSize: 13 }}>{t.description || '暂无描述'}</div>
            <div style={{ marginTop: 10, fontSize: 12, color: '#aaa' }}>ID: {t.id}</div>
          </div>
        ))}
      </div>
      {teams.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无团队，点击右上角创建</div>}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, marginRight: 8 };
const formStyle: React.CSSProperties = { background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const cardStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,.08)' };
