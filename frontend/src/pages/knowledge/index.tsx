import React, { useEffect, useState } from 'react';
import { knowledgeApi, projectsApi, skillsApi } from '../../lib/api';

type KnTab = 'docs' | 'skills';

export default function KnowledgePage() {
  const [mainTab, setMainTab] = useState<KnTab>('docs');

  // ── 知识库 ──
  const [docs, setDocs] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [form, setForm] = useState({ project_id: '', title: '', content: '', tags: '' });
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);

  // ── 技能库 ──
  const [skills, setSkills] = useState<any[]>([]);
  const [skillQ, setSkillQ] = useState('');
  const [skillForm, setSkillForm] = useState({ name: '', description: '', category: 'general', system_prompt: '', tags: '' });
  const [showSkillForm, setShowSkillForm] = useState(false);
  const [creatingSkill, setCreatingSkill] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<any | null>(null);
  const [skillSaving, setSkillSaving] = useState(false);

  const [error, setError] = useState('');

  const loadDocs = (query?: string) => knowledgeApi.list(query).then(setDocs).catch(e => setError(e.message));
  const loadSkills = (query?: string) => {
    const p = query
      ? skillsApi.search(query).then(r => setSkills(r.items))
      : skillsApi.list().then(r => setSkills(r.items));
    return p.catch(e => setError(e.message));
  };

  useEffect(() => {
    loadDocs();
    loadSkills();
    projectsApi.list().then(data => {
      setProjects(data);
      if (data[0]) setForm(f => ({ ...f, project_id: data[0].id }));
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); loadDocs(q || undefined); };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await knowledgeApi.create(form.project_id, form.title, form.content, form.tags.split(',').map(s => s.trim()).filter(Boolean));
      setForm(f => ({ ...f, title: '', content: '', tags: '' }));
      setShowForm(false); loadDocs();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确认删除？')) return;
    try { await knowledgeApi.delete(id); loadDocs(); setSelected(null); } catch (e: any) { setError(e.message); }
  };

  const handleCreateSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingSkill(true);
    try {
      await skillsApi.create({
        name: skillForm.name,
        description: skillForm.description,
        category: skillForm.category,
        system_prompt: skillForm.system_prompt,
        tags: skillForm.tags.split(',').map(s => s.trim()).filter(Boolean),
      });
      setSkillForm({ name: '', description: '', category: 'general', system_prompt: '', tags: '' });
      setShowSkillForm(false);
      loadSkills();
    } catch (e: any) { setError(e.message); }
    finally { setCreatingSkill(false); }
  };

  const handleDeleteSkill = async (id: string, name: string) => {
    if (!confirm(`确认删除技能「${name}」？`)) return;
    try {
      await skillsApi.delete(id);
      loadSkills();
      if (selectedSkill?.id === id) setSelectedSkill(null);
    } catch (e: any) { setError(e.message); }
  };

  const handleOpenSkill = async (id: string) => {
    try {
      const detail = await skillsApi.get(id);
      setSelectedSkill(detail);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSaveSkill = async () => {
    if (!selectedSkill) return;
    setSkillSaving(true);
    try {
      const updated = await skillsApi.update(selectedSkill.id, {
        name: selectedSkill.name,
        description: selectedSkill.description,
        system_prompt: selectedSkill.system_prompt,
        category: selectedSkill.category,
        tags: selectedSkill.tags || [],
      });
      setSelectedSkill(updated);
      await loadSkills(skillQ || undefined);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSkillSaving(false);
    }
  };

  return (
    <div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}

      {/* 顶部 Tab 切换 */}
      <div style={{ fontSize: 12, color: '#666', marginBottom: 10 }}>
        说明：技能平台用于管理 Prompt/技能版本；知识库用于沉淀 RAG 文档。这里保留技能视图用于联动检查。
      </div>
      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '2px solid #f0f0f0' }}>
        {([['docs', '📄 知识库(RAG)'], ['skills', '🔧 技能视图']] as [KnTab, string][]).map(([key, label]) => (
          <button key={key} onClick={() => setMainTab(key)} style={tabBtn(mainTab === key)}>{label}</button>
        ))}
      </div>

      {/* ── 知识库 Tab ── */}
      {mainTab === 'docs' && (
        <div style={{ display: 'flex', gap: 20 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>知识文档</h2>
              <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 新建文档</button>
            </div>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <input style={{ flex: 1, ...inputStyle }} placeholder="搜索标题或内容..." value={q} onChange={e => setQ(e.target.value)} />
              <button style={btnPrimary} type="submit">搜索</button>
              {q && <button style={{ ...btnPrimary, background: '#fff', color: '#333', border: '1px solid #d9d9d9' }} type="button" onClick={() => { setQ(''); loadDocs(); }}>清除</button>}
            </form>
            {showForm && (
              <form onSubmit={handleCreate} style={{ ...formStyle, flexDirection: 'column', alignItems: 'stretch' }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <select style={inputStyle} value={form.project_id} onChange={e => setForm(f => ({ ...f, project_id: e.target.value }))} required>
                    {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                  <input style={{ flex: 1, ...inputStyle }} placeholder="标题" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
                  <input style={inputStyle} placeholder="标签（逗号分隔）" value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))} />
                </div>
                <textarea rows={4} style={{ ...inputStyle, resize: 'vertical', marginRight: 0 }} placeholder="Markdown 内容..." value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))} required />
                <div style={{ marginTop: 8 }}>
                  <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '保存中...' : '确认创建'}</button>
                </div>
              </form>
            )}
            {docs.map(d => (
              <div key={d.id} style={{ ...cardStyle, cursor: 'pointer' }} onClick={() => setSelected(d)}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 500 }}>{d.title}</span>
                  <span style={{ fontSize: 11, color: '#aaa' }}>v{d.version}</span>
                </div>
                {d.tags?.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    {d.tags.map((tag: string) => (
                      <span key={tag} style={{ fontSize: 11, background: '#f5f5f5', padding: '2px 6px', borderRadius: 3, marginRight: 4 }}>{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {docs.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无文档</div>}
          </div>
          {selected && (
            <div style={{ width: 380, background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,.08)', alignSelf: 'flex-start' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <strong>{selected.title}</strong>
                <span style={{ cursor: 'pointer', color: '#aaa' }} onClick={() => setSelected(null)}>✕</span>
              </div>
              <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, color: '#444', lineHeight: 1.7 }}>{selected.content}</pre>
              <button style={{ ...btnPrimary, background: '#fff2f0', color: '#ff4d4f', border: 'none', marginTop: 16 }} onClick={() => handleDelete(selected.id)}>删除文档</button>
            </div>
          )}
        </div>
      )}

      {/* ── 技能库 Tab ── */}
      {mainTab === 'skills' && (
        <div style={{ display: 'flex', gap: 20 }}>
          <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ margin: 0 }}>Skill 技能库</h2>
            <button style={btnPrimary} onClick={() => setShowSkillForm(v => !v)}>+ 注册技能</button>
          </div>
          {/* 搜索 */}
          <form onSubmit={e => { e.preventDefault(); loadSkills(skillQ || undefined); }} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <input style={{ flex: 1, ...inputStyle }} placeholder="语义搜索技能描述..." value={skillQ} onChange={e => setSkillQ(e.target.value)} />
            <button style={btnPrimary} type="submit">搜索</button>
            {skillQ && <button type="button" style={{ ...btnPrimary, background: '#fff', color: '#333', border: '1px solid #d9d9d9' }} onClick={() => { setSkillQ(''); loadSkills(); }}>清除</button>}
          </form>
          {/* 创建表单 */}
          {showSkillForm && (
            <form onSubmit={handleCreateSkill} style={{ ...formStyle, flexDirection: 'column', alignItems: 'stretch' }}>
              <div style={{ display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
                <input style={inputStyle} placeholder="技能名称" value={skillForm.name} onChange={e => setSkillForm(f => ({ ...f, name: e.target.value }))} required />
                <select style={inputStyle} value={skillForm.category} onChange={e => setSkillForm(f => ({ ...f, category: e.target.value }))}>
                  {['general', 'coding', 'writing', 'analysis', 'search', 'tool_use'].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <input style={inputStyle} placeholder="标签（逗号分隔）" value={skillForm.tags} onChange={e => setSkillForm(f => ({ ...f, tags: e.target.value }))} />
              </div>
              <input style={{ ...inputStyle, marginBottom: 8, marginRight: 0, width: '100%', boxSizing: 'border-box' }} placeholder="简短描述" value={skillForm.description} onChange={e => setSkillForm(f => ({ ...f, description: e.target.value }))} />
              <textarea rows={3} style={{ ...inputStyle, resize: 'vertical', marginRight: 0 }} placeholder="System Prompt（可选，定义技能的角色和行为）" value={skillForm.system_prompt} onChange={e => setSkillForm(f => ({ ...f, system_prompt: e.target.value }))} />
              <div style={{ marginTop: 8 }}>
                <button style={btnPrimary} type="submit" disabled={creatingSkill}>{creatingSkill ? '注册中...' : '确认注册'}</button>
              </div>
            </form>
          )}
          {/* 技能列表 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {skills.map(s => (
              <div key={s.id} style={{ ...cardStyle, position: 'relative', cursor: 'pointer' }} onClick={() => handleOpenSkill(s.id)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <span style={{ fontWeight: 600, fontSize: 15 }}>{s.name}</span>
                    <span style={{ fontSize: 11, padding: '1px 6px', borderRadius: 3, background: '#f0f5ff', color: '#1677ff', marginLeft: 8 }}>{s.category}</span>
                  </div>
                  <button onClick={(e) => { e.stopPropagation(); handleDeleteSkill(s.id, s.name); }} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#ccc', fontSize: 16 }}>✕</button>
                </div>
                {s.description && <div style={{ fontSize: 13, color: '#666', marginTop: 6 }}>{s.description}</div>}
                {s.tags?.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    {s.tags.map((t: string) => <span key={t} style={{ fontSize: 11, background: '#f5f5f5', padding: '2px 6px', borderRadius: 3, marginRight: 4 }}>{t}</span>)}
                  </div>
                )}
                {s.system_prompt && (
                  <div style={{ marginTop: 8, fontSize: 12, color: '#888', background: '#fafafa', padding: '6px 8px', borderRadius: 4, fontFamily: 'monospace', maxHeight: 60, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {s.system_prompt.slice(0, 120)}{s.system_prompt.length > 120 ? '...' : ''}
                  </div>
                )}
              </div>
            ))}
          </div>
          {skills.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无技能，点击「注册技能」添加第一个</div>}
          </div>

          {selectedSkill && (
            <div style={{ width: 420, background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,.08)', alignSelf: 'flex-start' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <div>
                  <strong>{selectedSkill.name}</strong>
                  <span style={{ fontSize: 11, padding: '1px 6px', borderRadius: 3, background: '#f0f5ff', color: '#1677ff', marginLeft: 8 }}>{selectedSkill.category}</span>
                </div>
                <span style={{ cursor: 'pointer', color: '#aaa' }} onClick={() => setSelectedSkill(null)}>✕</span>
              </div>

              {selectedSkill.description && (
                <div style={{ fontSize: 13, color: '#666', marginBottom: 10 }}>{selectedSkill.description}</div>
              )}

              {selectedSkill.tags?.length > 0 && (
                <div style={{ marginBottom: 10 }}>
                  {selectedSkill.tags.map((t: string) => <span key={t} style={{ fontSize: 11, background: '#f5f5f5', padding: '2px 6px', borderRadius: 3, marginRight: 4 }}>{t}</span>)}
                </div>
              )}

              <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>System Prompt</div>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginBottom: 8, marginRight: 0 }}
                value={selectedSkill.name || ''}
                onChange={(e) => setSelectedSkill((s: any) => ({ ...s, name: e.target.value }))}
                placeholder="技能名称"
              />
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginBottom: 8, marginRight: 0 }}
                value={selectedSkill.description || ''}
                onChange={(e) => setSelectedSkill((s: any) => ({ ...s, description: e.target.value }))}
                placeholder="技能描述"
              />
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginBottom: 8, marginRight: 0 }}
                value={(selectedSkill.tags || []).join(', ')}
                onChange={(e) => setSelectedSkill((s: any) => ({ ...s, tags: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) }))}
                placeholder="标签，逗号分隔"
              />
              <textarea
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', marginRight: 0, minHeight: 140, resize: 'vertical' }}
                value={selectedSkill.system_prompt || ''}
                onChange={(e) => setSelectedSkill((s: any) => ({ ...s, system_prompt: e.target.value }))}
                placeholder="System Prompt"
              />

              <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
                <button
                  style={{ ...btnPrimary, background: '#1677ff', color: '#fff', border: 'none' }}
                  onClick={handleSaveSkill}
                  disabled={skillSaving}
                >
                  {skillSaving ? '保存中...' : '保存修改'}
                </button>
                <button
                  style={{ ...btnPrimary, background: '#fff2f0', color: '#ff4d4f', border: 'none' }}
                  onClick={() => handleDeleteSkill(selectedSkill.id, selectedSkill.name)}
                >
                  删除技能
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: '8px 20px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 14,
  fontWeight: active ? 700 : 400, color: active ? '#1677ff' : '#666',
  borderBottom: active ? '2px solid #1677ff' : '2px solid transparent', marginBottom: -2,
});
const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, marginRight: 8 };
const formStyle: React.CSSProperties = { background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, display: 'flex' };
const cardStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: 12 };
