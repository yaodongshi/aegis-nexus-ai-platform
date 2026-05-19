import React, { useEffect, useState } from 'react';
import { pluginsApi, teamsApi } from '../../lib/api';

export default function PluginPage() {
  const [plugins, setPlugins] = useState<any[]>([]);
  const [teams, setTeams] = useState<any[]>([]);
  const [form, setForm] = useState({ team_id: '', name: '', description: '', version: '1.0.0' });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);

  const load = () => pluginsApi.list().then(setPlugins).catch(e => setError(e.message));
  useEffect(() => {
    load();
    teamsApi.list().then(data => {
      setTeams(data);
      if (data[0]) setForm(f => ({ ...f, team_id: data[0].id }));
    });
  }, []);

  const handleInstall = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await pluginsApi.install(form.team_id, form.name, form.description, form.version, {});
      setForm(f => ({ ...f, name: '', description: '', version: '1.0.0' }));
      setShowForm(false); load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const handleToggle = async (id: string, enabled: boolean) => {
    try { await pluginsApi.update(id, { enabled }); load(); } catch (e: any) { setError(e.message); }
  };

  const handleUninstall = async (id: string) => {
    if (!confirm('确认卸载插件？')) return;
    try { await pluginsApi.uninstall(id); load(); } catch (e: any) { setError(e.message); }
  };

  return (
    <div>
      <div style={{ marginBottom: 12, border: '1px solid #ffd591', background: '#fff7e6', color: '#ad6800', borderRadius: 8, padding: '10px 12px', fontSize: 13 }}>
        兼容模式：插件模块已降级为历史兼容能力，不再作为主线导航入口。建议将能力沉淀到 Skill / Agent / MCP 统一治理链路中。
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>插件市场</h1>
        <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 安装插件</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {showForm && (
        <form onSubmit={handleInstall} style={formStyle}>
          <select style={inputStyle} value={form.team_id} onChange={e => setForm(f => ({ ...f, team_id: e.target.value }))} required>
            {teams.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
          <input style={inputStyle} placeholder="插件名称" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
          <input style={inputStyle} placeholder="版本" value={form.version} onChange={e => setForm(f => ({ ...f, version: e.target.value }))} />
          <input style={{ ...inputStyle, width: 200 }} placeholder="描述" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '安装中...' : '确认安装'}</button>
        </form>
      )}
      <table style={{ width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
            {['插件名称', '版本', '状态', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {plugins.map(p => (
            <tr key={p.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
              <td style={tdStyle}>{p.name}</td>
              <td style={tdStyle}>{p.version}</td>
              <td style={tdStyle}>
                <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 10, background: p.enabled ? '#f6ffed' : '#f5f5f5', color: p.enabled ? '#52c41a' : '#aaa' }}>
                  {p.enabled ? '已启用' : '已禁用'}
                </span>
              </td>
              <td style={tdStyle}>
                <button style={btnSmall} onClick={() => handleToggle(p.id, !p.enabled)}>{p.enabled ? '禁用' : '启用'}</button>
                <button style={{ ...btnSmall, marginLeft: 8, color: '#ff4d4f', background: '#fff2f0' }} onClick={() => handleUninstall(p.id)}>卸载</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {plugins.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无已安装插件</div>}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const btnSmall: React.CSSProperties = { padding: '4px 10px', background: '#e6f4ff', color: '#1677ff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, marginRight: 8 };
const formStyle: React.CSSProperties = { background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
