import React, { useEffect, useState } from 'react';
import { agentsApi, projectsApi } from '../../lib/api';

export default function AgentPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [form, setForm] = useState({ project_id: '', name: '', prompt: '' });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);

  const load = () => agentsApi.list().then(setAgents).catch(e => setError(e.message));
  useEffect(() => {
    load();
    projectsApi.list().then(data => {
      setProjects(data);
      if (data[0]) setForm(f => ({ ...f, project_id: data[0].id }));
    });
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await agentsApi.create(form.project_id, form.name, form.prompt, []);
      setForm(f => ({ ...f, name: '', prompt: '' }));
      setShowForm(false); load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除该智能体？')) return;
    try { await agentsApi.delete(id); load(); } catch (e: any) { setError(e.message); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>智能体管理</h1>
        <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 新建智能体</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {showForm && (
        <form onSubmit={handleCreate} style={formStyle}>
          <select style={inputStyle} value={form.project_id} onChange={e => setForm(f => ({ ...f, project_id: e.target.value }))} required>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input style={inputStyle} placeholder="智能体名称" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
          <input style={{ ...inputStyle, width: 240 }} placeholder="系统提示词" value={form.prompt} onChange={e => setForm(f => ({ ...f, prompt: e.target.value }))} />
          <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '创建中...' : '确认'}</button>
        </form>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16, marginTop: 16 }}>
        {agents.map(a => (
          <div key={a.id} style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 600 }}>{a.name}</span>
              <span style={{ fontSize: 11, background: '#e6f4ff', color: '#1677ff', padding: '2px 8px', borderRadius: 10 }}>v{a.version}</span>
            </div>
            <div style={{ color: '#666', fontSize: 13, marginTop: 8, wordBreak: 'break-all' }}>{a.prompt || '无提示词'}</div>
            <button style={{ ...btnSmall, marginTop: 12, color: '#ff4d4f', background: '#fff2f0' }} onClick={() => handleDelete(a.id)}>删除</button>
          </div>
        ))}
      </div>
      {agents.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无智能体</div>}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const btnSmall: React.CSSProperties = { padding: '4px 10px', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, marginRight: 8 };
const formStyle: React.CSSProperties = { background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const cardStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,.08)' };
