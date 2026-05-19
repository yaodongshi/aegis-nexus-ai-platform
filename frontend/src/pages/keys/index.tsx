import React, { useEffect, useState } from 'react';
import { keysApi } from '../../lib/api';

export default function KeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [newKey, setNewKey] = useState<{ key_id: string; key_secret: string } | null>(null);
  const [form, setForm] = useState({ label: '', user_id: 'admin', scope: 'project:*', expires_days: '', quota: '' });
  const [showForm, setShowForm] = useState(false);
  const [creating, setCreating] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');
  const [error, setError] = useState('');

  const load = () =>
    keysApi.list(statusFilter ? { status: statusFilter } : undefined)
      .then(r => { setKeys(r.items); setTotal(r.total); })
      .catch(e => setError(e.message));

  useEffect(() => { load(); }, [statusFilter]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleIssue = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const resp = await keysApi.issue({
        label: form.label || undefined,
        user_id: form.user_id,
        scope: form.scope,
        expires_days: form.expires_days ? Number(form.expires_days) : undefined,
        quota: form.quota ? Number(form.quota) : undefined,
      });
      setNewKey(resp);
      setForm({ label: '', user_id: 'admin', scope: 'project:*', expires_days: '', quota: '' });
      setShowForm(false);
      load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const handleRevoke = async (id: string, label?: string) => {
    if (!confirm(`确认撤销密钥「${label || id}」？此操作不可逆。`)) return;
    try { await keysApi.revoke(id); load(); } catch (e: any) { setError(e.message); }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1>虚拟密钥管理</h1>
        <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 发放密钥</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}

      {/* 新密钥一次性展示 */}
      {newKey && (
        <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <strong style={{ color: '#389e0d' }}>密钥已生成（仅显示一次，请立即复制保存）</strong>
          <div style={{ fontFamily: 'monospace', fontSize: 14, marginTop: 8, background: '#fff', padding: '8px 12px', borderRadius: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ wordBreak: 'break-all' }}>{newKey.key_secret}</span>
            <button style={{ ...btnPrimary, padding: '4px 12px', fontSize: 12, marginLeft: 8, flexShrink: 0 }} onClick={() => navigator.clipboard.writeText(newKey.key_secret)}>复制</button>
          </div>
          <div style={{ fontSize: 12, color: '#888', marginTop: 6 }}>密钥 ID: {newKey.key_id}</div>
          <button style={{ marginTop: 8, fontSize: 12, color: '#888', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setNewKey(null)}>关闭</button>
        </div>
      )}

      {/* 发放表单 */}
      {showForm && (
        <form onSubmit={handleIssue} style={{ background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <input style={inputStyle} placeholder="标签（可选，便于识别）" value={form.label} onChange={e => setForm(f => ({ ...f, label: e.target.value }))} />
            <input style={inputStyle} placeholder="用户 ID" value={form.user_id} onChange={e => setForm(f => ({ ...f, user_id: e.target.value }))} required />
            <input style={inputStyle} placeholder="权限范围（如 project:*）" value={form.scope} onChange={e => setForm(f => ({ ...f, scope: e.target.value }))} />
            <input style={{ ...inputStyle, width: 110 }} placeholder="有效天数" type="number" min={1} value={form.expires_days} onChange={e => setForm(f => ({ ...f, expires_days: e.target.value }))} />
            <input style={{ ...inputStyle, width: 120 }} placeholder="配额（调用次数）" type="number" min={1} value={form.quota} onChange={e => setForm(f => ({ ...f, quota: e.target.value }))} />
            <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '发放中...' : '确认发放'}</button>
            <button type="button" style={{ ...btnPrimary, background: '#fff', color: '#666', border: '1px solid #d9d9d9' }} onClick={() => setShowForm(false)}>取消</button>
          </div>
        </form>
      )}

      {/* 筛选栏 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: '#888' }}>共 {total} 条</span>
        <select style={{ ...inputStyle, marginRight: 0 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">全部状态</option>
          <option value="active">有效</option>
          <option value="revoked">已撤销</option>
        </select>
      </div>

      <table style={tableStyle}>
        <thead>
          <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
            {['标签', '用户', '权限范围', '状态', '到期时间', '创建时间', '操作'].map(h => (
              <th key={h} style={thStyle}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {keys.map(k => (
            <tr key={k.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
              <td style={tdStyle}>{k.label || <span style={{ color: '#ccc' }}>—</span>}</td>
              <td style={tdStyle}>{k.user_id || '—'}</td>
              <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12, color: '#555' }}>{k.scope}</td>
              <td style={tdStyle}>
                <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: k.status === 'active' ? '#f6ffed' : '#fff2f0', color: k.status === 'active' ? '#52c41a' : '#ff4d4f' }}>
                  {k.status === 'active' ? '有效' : '已撤销'}
                </span>
              </td>
              <td style={{ ...tdStyle, fontSize: 12, color: '#aaa' }}>{k.expire_at ? new Date(k.expire_at).toLocaleDateString() : '永久'}</td>
              <td style={{ ...tdStyle, fontSize: 12, color: '#aaa' }}>{new Date(k.created_at).toLocaleString()}</td>
              <td style={tdStyle}>
                {k.status === 'active' && (
                  <button style={{ fontSize: 12, padding: '4px 10px', background: '#fff2f0', color: '#ff4d4f', border: '1px solid #ffccc7', borderRadius: 4, cursor: 'pointer' }} onClick={() => handleRevoke(k.id, k.label)}>撤销</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {keys.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无密钥，点击「发放密钥」创建第一条</div>}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14 };
const tableStyle: React.CSSProperties = { width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' };
const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
