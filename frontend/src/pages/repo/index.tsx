import React, { useEffect, useState } from 'react';
import { projectsApi, reposApi } from '../../lib/api';

export default function RepoPage() {
  const [repos, setRepos] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [form, setForm] = useState({ project_id: '', name: '', url: '', branch: 'main' });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);

  const load = () => reposApi.list().then(setRepos).catch(e => setError(e.message));
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
      await reposApi.create(form.project_id, form.name, form.url, form.branch);
      setForm(f => ({ ...f, name: '', url: '', branch: 'main' }));
      setShowForm(false); load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const handleSync = async (id: string) => {
    try { await reposApi.sync(id); load(); } catch (e: any) { setError(e.message); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>代码仓库管理</h1>
        <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 绑定仓库</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {showForm && (
        <form onSubmit={handleCreate} style={formStyle}>
          <select style={inputStyle} value={form.project_id} onChange={e => setForm(f => ({ ...f, project_id: e.target.value }))} required>
            {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input style={inputStyle} placeholder="仓库名称" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
          <input style={inputStyle} placeholder="仓库地址 URL" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} required />
          <input style={{ ...inputStyle, width: 100 }} placeholder="分支" value={form.branch} onChange={e => setForm(f => ({ ...f, branch: e.target.value }))} />
          <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '绑定中...' : '确认绑定'}</button>
        </form>
      )}
      <table style={{ width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
            {['仓库名称', '地址', '当前分支', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {repos.map(r => (
            <tr key={r.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
              <td style={tdStyle}>{r.name}</td>
              <td style={{ ...tdStyle, color: '#1677ff', wordBreak: 'break-all' }}>{r.url}</td>
              <td style={tdStyle}>{r.current_branch ?? r.branch}</td>
              <td style={tdStyle}>
                <button style={btnSmall} onClick={() => handleSync(r.id)}>同步</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {repos.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无仓库</div>}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const btnSmall: React.CSSProperties = { padding: '4px 10px', background: '#e6f4ff', color: '#1677ff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, marginRight: 8 };
const formStyle: React.CSSProperties = { background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
