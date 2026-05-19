import React, { useEffect, useState } from 'react';
import { projectsApi, tasksApi } from '../../lib/api';

const STATUS_COLORS: Record<string, string> = {
  open: '#1677ff', in_progress: '#faad14', done: '#52c41a', closed: '#aaa',
};

export default function TaskPage() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [form, setForm] = useState({ project_id: '', title: '', description: '' });
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<any | null>(null);
  const [comment, setComment] = useState('');
  const [comments, setComments] = useState<any[]>([]);

  const load = () => tasksApi.list().then(setTasks).catch(e => setError(e.message));
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
      await tasksApi.create(form.project_id, form.title, form.description);
      setForm(f => ({ ...f, title: '', description: '' }));
      setShowForm(false); load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const handleSelect = async (task: any) => {
    setSelected(task);
    const c = await tasksApi.listComments(task.id).catch(() => []);
    setComments(c);
  };

  const handleComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selected || !comment.trim()) return;
    await tasksApi.addComment(selected.id, comment);
    setComment('');
    const c = await tasksApi.listComments(selected.id).catch(() => []);
    setComments(c);
  };

  const handleStatus = async (id: string, status: string) => {
    await tasksApi.update(id, { status }).catch(e => setError(e.message));
    load();
    if (selected?.id === id) setSelected((prev: any) => ({ ...prev, status }));
  };

  return (
    <div style={{ display: 'flex', gap: 20 }}>
      <div style={{ flex: 1 }}>
        <div style={{ marginBottom: 12, border: '1px solid #ffd591', background: '#fff7e6', color: '#ad6800', borderRadius: 8, padding: '10px 12px', fontSize: 13 }}>
          兼容模式：任务模块已降级为历史兼容能力，不再作为主线导航入口。建议通过技能提案、治理审批与观测中心完成主流程。
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h1>任务管理</h1>
          <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 新建任务</button>
        </div>
        {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
        {showForm && (
          <form onSubmit={handleCreate} style={formStyle}>
            <select style={inputStyle} value={form.project_id} onChange={e => setForm(f => ({ ...f, project_id: e.target.value }))} required>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
            <input style={{ ...inputStyle, width: 200 }} placeholder="任务标题" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
            <input style={{ ...inputStyle, width: 200 }} placeholder="描述（可选）" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '创建中...' : '确认'}</button>
          </form>
        )}
        {tasks.map(t => (
          <div key={t.id} style={{ ...cardStyle, cursor: 'pointer', borderLeft: `3px solid ${STATUS_COLORS[t.status] ?? '#d9d9d9'}` }} onClick={() => handleSelect(t)}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontWeight: 500 }}>{t.title}</span>
              <select
                style={{ border: 'none', fontSize: 12, color: STATUS_COLORS[t.status] ?? '#aaa', background: 'transparent', cursor: 'pointer' }}
                value={t.status}
                onChange={e => { e.stopPropagation(); handleStatus(t.id, e.target.value); }}
                onClick={e => e.stopPropagation()}
              >
                {['open', 'in_progress', 'done', 'closed'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div style={{ color: '#888', fontSize: 13, marginTop: 4 }}>{t.description}</div>
          </div>
        ))}
        {tasks.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无任务</div>}
      </div>

      {selected && (
        <div style={{ width: 320, background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,.08)', alignSelf: 'flex-start' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <strong>{selected.title}</strong>
            <span style={{ cursor: 'pointer', color: '#aaa' }} onClick={() => setSelected(null)}>✕</span>
          </div>
          <div style={{ fontSize: 13, color: '#666', marginBottom: 16 }}>{selected.description}</div>
          <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 8 }}>评论 ({comments.length})</div>
          {comments.map(c => (
            <div key={c.id} style={{ fontSize: 13, padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>{c.content}</div>
          ))}
          <form onSubmit={handleComment} style={{ marginTop: 12, display: 'flex', gap: 8 }}>
            <input style={{ flex: 1, padding: '6px 8px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 13 }} placeholder="添加评论" value={comment} onChange={e => setComment(e.target.value)} />
            <button style={{ ...btnPrimary, padding: '6px 12px' }} type="submit">发送</button>
          </form>
        </div>
      )}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, marginRight: 8 };
const formStyle: React.CSSProperties = { background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' };
const cardStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: 12 };
