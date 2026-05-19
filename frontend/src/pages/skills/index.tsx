import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { skillsApi } from '../../lib/api';

export default function SkillsListPage() {
  const [skills, setSkills] = useState<any[]>([]);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [form, setForm] = useState({ name: '', description: '', category: 'general', system_prompt: '', tags: '' });
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const loadSkills = (q?: string) => {
    const p = q ? skillsApi.search(q).then((r) => r.items) : skillsApi.list().then((r) => r.items);
    p.then(setSkills).catch((e) => setError(e.message));
  };

  useEffect(() => {
    loadSkills();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    try {
      const created = await skillsApi.create({
        name: form.name,
        description: form.description,
        category: form.category,
        system_prompt: form.system_prompt,
        tags: form.tags.split(',').map((x) => x.trim()).filter(Boolean),
      });
      setShowForm(false);
      setForm({ name: '', description: '', category: 'general', system_prompt: '', tags: '' });
      await loadSkills(query || undefined);
      window.location.assign(`/skills/${created.id}`);
    } catch (e: any) {
      setError(e.message || '创建技能失败');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>技能平台</h1>
        <button style={btnPrimary} onClick={() => setShowForm((v) => !v)}>{showForm ? '收起表单' : '+ 新建技能'}</button>
      </div>

      <div style={{ marginBottom: 16, color: '#666', fontSize: 13 }}>
        独立的 List + Detail 管理流。点击技能进入详情页，可编辑并导出 Claude/OpenCode 兼容文件结构。
      </div>

      {error && <div style={{ color: '#ff4d4f', marginBottom: 12 }}>{error}</div>}

      <form onSubmit={(e) => { e.preventDefault(); loadSkills(query || undefined); }} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input style={{ ...inputStyle, flex: 1 }} placeholder="搜索技能名称/描述" value={query} onChange={(e) => setQuery(e.target.value)} />
        <button style={btnPrimary} type="submit">搜索</button>
        {query && <button type="button" style={btnSecondary} onClick={() => { setQuery(''); loadSkills(); }}>清除</button>}
      </form>

      {showForm && (
        <form onSubmit={handleCreate} style={cardStyle}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
            <input style={{ ...inputStyle, flex: 1 }} required placeholder="技能名称" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
            <select style={inputStyle} value={form.category} onChange={(e) => setForm((s) => ({ ...s, category: e.target.value }))}>
              {['general', 'coding', 'writing', 'analysis', 'search', 'tool_use'].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <input style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginBottom: 8 }} placeholder="描述" value={form.description} onChange={(e) => setForm((s) => ({ ...s, description: e.target.value }))} />
          <input style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginBottom: 8 }} placeholder="标签，逗号分隔" value={form.tags} onChange={(e) => setForm((s) => ({ ...s, tags: e.target.value }))} />
          <textarea style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', minHeight: 120, resize: 'vertical' }} placeholder="System Prompt" value={form.system_prompt} onChange={(e) => setForm((s) => ({ ...s, system_prompt: e.target.value }))} />
          <div style={{ marginTop: 10 }}>
            <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '创建中...' : '创建并进入详情'}</button>
          </div>
        </form>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {skills.map((s) => (
          <Link key={s.id} to={`/skills/${s.id}`} style={{ ...cardStyle, textDecoration: 'none', color: '#222' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <strong>{s.name}</strong>
              <span style={pillStyle}>{s.category}</span>
            </div>
            <div style={{ fontSize: 13, color: '#666', marginBottom: 6 }}>{s.description || '（无描述）'}</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {(s.tags || []).map((t: string) => <span key={t} style={tagStyle}>{t}</span>)}
            </div>
          </Link>
        ))}
      </div>
      {skills.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无技能</div>}
    </div>
  );
}

const cardStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,.08)', padding: 14 };
const inputStyle: React.CSSProperties = { border: '1px solid #d9d9d9', borderRadius: 4, padding: '8px 10px', fontSize: 14 };
const btnPrimary: React.CSSProperties = { border: 'none', borderRadius: 4, background: '#1677ff', color: '#fff', cursor: 'pointer', padding: '8px 14px' };
const btnSecondary: React.CSSProperties = { border: '1px solid #d9d9d9', borderRadius: 4, background: '#fff', color: '#666', cursor: 'pointer', padding: '8px 14px' };
const tagStyle: React.CSSProperties = { fontSize: 11, background: '#f5f5f5', color: '#666', borderRadius: 3, padding: '2px 6px' };
const pillStyle: React.CSSProperties = { fontSize: 11, background: '#f0f5ff', color: '#1677ff', borderRadius: 3, padding: '2px 6px' };
