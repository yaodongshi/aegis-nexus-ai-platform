import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { modelsApi, providersApi } from '../../lib/api';

type ModelTab = 'registry' | 'aliases';

export default function ModelsPage() {
  const location = useLocation();
  const [models, setModels] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [aliases, setAliases] = useState<any>(null);
  const [tab, setTab] = useState<ModelTab>('registry');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    provider: '',
    provider_id: '',
    upstream_model: '',
    name: '',
    endpoint: '',
    context_window: '8192',
    cost_tier: 'medium',
    deployment_status: 'active',
  });
  const [creating, setCreating] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [syncResult, setSyncResult] = useState<string>('');
  const [providerFilter, setProviderFilter] = useState('');
  const [error, setError] = useState('');
  const focus = new URLSearchParams(location.search).get('focus');

  const load = () => {
    const offset = (page - 1) * pageSize;
    return modelsApi.list(providerFilter || undefined, undefined, pageSize, offset)
      .then(r => {
        setModels(r.items);
        setTotal(r.total);
        const ids = new Set(r.items.map((item: any) => item.id));
        setSelectedIds(prev => prev.filter(id => ids.has(id)));
        const totalPages = Math.max(1, Math.ceil((r.total || 0) / pageSize));
        if (page > totalPages) {
          setPage(totalPages);
        }
      })
      .catch(e => setError(e.message));
  };

  useEffect(() => {
    load();
    modelsApi.aliases().then(setAliases).catch(() => {});
  }, [providerFilter, page, pageSize]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await modelsApi.register({ ...form, context_window: Number(form.context_window) });
      setForm({
        provider: '',
        provider_id: '',
        upstream_model: '',
        name: '',
        endpoint: '',
        context_window: '8192',
        cost_tier: 'medium',
        deployment_status: 'active',
      });
      setShowForm(false);
      load();
    } catch (e: any) { setError(e.message); }
    finally { setCreating(false); }
  };

  const toggleAvailability = async (id: string, current: string) => {
    try {
      await modelsApi.update(id, { availability: current === 'active' ? 'disabled' : 'active' });
      load();
    } catch (e: any) { setError(e.message); }
  };

  const handleSyncGateway = async () => {
    setSyncing(true);
    setSyncResult('');
    try {
      const result = await providersApi.syncGateway();
      setSyncResult(result?.detail || '同步成功');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSyncing(false);
    }
  };

  const handleBatchDelete = async () => {
    if (!selectedIds.length) return;
    if (!confirm(`确认批量删除 ${selectedIds.length} 个模型？此操作不可恢复。`)) return;

    setDeleting(true);
    setSyncResult('');
    try {
      const result = await modelsApi.batchDelete(selectedIds);
      setSelectedIds([]);
      await load();
      const missing = result.missing_ids?.length ? `，未找到 ${result.missing_ids.length} 个` : '';
      setSyncResult(`批量删除完成：已删除 ${result.deleted} 个${missing}`);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setDeleting(false);
    }
  };

  const toggleSelectAll = () => {
    if (!models.length) return;
    const allIds = models.map(m => m.id);
    setSelectedIds(prev => (prev.length === allIds.length ? [] : allIds));
  };

  const toggleSelectOne = (modelId: string) => {
    setSelectedIds(prev => (
      prev.includes(modelId)
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    ));
  };

  const providers: string[] = aliases?.providers ?? [];
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1>模型注册管理</h1>
        {tab === 'registry' && (
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={{ ...btnPrimary, background: '#13c2c2' }} onClick={handleSyncGateway} disabled={syncing}>
              {syncing ? '同步中...' : '同步到网关'}
            </button>
            <button
              style={{ ...btnPrimary, background: '#ff4d4f', opacity: selectedIds.length ? 1 : 0.55 }}
              onClick={handleBatchDelete}
              disabled={!selectedIds.length || deleting}
            >
              {deleting ? '删除中...' : `批量删除(${selectedIds.length})`}
            </button>
            <button style={btnPrimary} onClick={() => setShowForm(v => !v)}>+ 注册模型</button>
          </div>
        )}
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {syncResult && <div style={{ color: '#389e0d', marginBottom: 12 }}>{syncResult}</div>}
      {focus === 'blocking_failed' && (
        <div style={{ marginBottom: 12, border: '1px solid #ffd591', background: '#fff7e6', color: '#ad6800', borderRadius: 8, padding: '10px 12px', fontSize: 13 }}>
          来自运行时阻断告警：请确认关键聊天模型和 embedding 模型均已注册且为可用状态，然后执行“同步到网关”。
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid #f0f0f0' }}>
        {([['registry', '模型注册表'], ['aliases', '模型别名']] as [ModelTab, string][]).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={tabBtn(tab === key)}>{label}</button>
        ))}
      </div>

      {tab === 'registry' && (
        <>
          {showForm && (
            <form onSubmit={handleRegister} style={{ background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <input style={inputStyle} placeholder="厂商（如 openai）" value={form.provider} onChange={e => setForm(f => ({ ...f, provider: e.target.value }))} required />
                <input style={inputStyle} placeholder="供应商ID（可选）" value={form.provider_id} onChange={e => setForm(f => ({ ...f, provider_id: e.target.value }))} />
                <input style={inputStyle} placeholder="上游模型ID（可选）" value={form.upstream_model} onChange={e => setForm(f => ({ ...f, upstream_model: e.target.value }))} />
                <input style={inputStyle} placeholder="模型名（如 gpt-4o）" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
                <input style={{ ...inputStyle, width: 240 }} placeholder="Endpoint URL" value={form.endpoint} onChange={e => setForm(f => ({ ...f, endpoint: e.target.value }))} required />
                <input style={{ ...inputStyle, width: 110 }} placeholder="上下文窗口" type="number" value={form.context_window} onChange={e => setForm(f => ({ ...f, context_window: e.target.value }))} required />
                <select style={inputStyle} value={form.cost_tier} onChange={e => setForm(f => ({ ...f, cost_tier: e.target.value }))}>
                  {['economy', 'medium', 'high'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <select style={inputStyle} value={form.deployment_status} onChange={e => setForm(f => ({ ...f, deployment_status: e.target.value }))}>
                  {['active', 'pending', 'failed', 'disabled'].map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '注册中...' : '确认注册'}</button>
                <button type="button" style={{ ...btnPrimary, background: '#fff', color: '#666', border: '1px solid #d9d9d9' }} onClick={() => setShowForm(false)}>取消</button>
              </div>
            </form>
          )}

          <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
            <span style={{ fontSize: 13, color: '#888' }}>共 {total} 条</span>
            <select
              style={inputStyle}
              value={providerFilter}
              onChange={e => {
                setProviderFilter(e.target.value);
                setPage(1);
              }}
            >
              <option value="">全部厂商</option>
              {providers.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
            <select
              style={inputStyle}
              value={String(pageSize)}
              onChange={e => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
            >
              {[20, 50, 100].map(size => <option key={size} value={String(size)}>每页 {size} 条</option>)}
            </select>
          </div>

          <table style={tableStyle}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                <th style={thStyle}>
                  <input
                    type="checkbox"
                    checked={models.length > 0 && selectedIds.length === models.length}
                    onChange={toggleSelectAll}
                  />
                </th>
                {['模型名', '厂商', '供应商ID', '上游模型', '上下文窗口', '费用档次', '可用性', '部署状态', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {models.map(m => (
                <tr key={m.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={tdStyle}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(m.id)}
                      onChange={() => toggleSelectOne(m.id)}
                    />
                  </td>
                  <td style={tdStyle}>
                    <span style={{ fontWeight: 500 }}>{m.name}</span><br />
                    <span style={{ fontSize: 11, color: '#aaa', fontFamily: 'monospace' }}>{m.id}</span>
                  </td>
                  <td style={tdStyle}>
                    <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: '#f0f5ff', color: '#1677ff' }}>{m.provider}</span>
                  </td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{m.provider_id || '-'}</td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{m.upstream_model || '-'}</td>
                  <td style={tdStyle}>{((m.context_window ?? 0) / 1000).toFixed(0)}K</td>
                  <td style={tdStyle}>{m.cost_tier}</td>
                  <td style={tdStyle}>
                    <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: m.availability === 'active' ? '#f6ffed' : '#f5f5f5', color: m.availability === 'active' ? '#52c41a' : '#aaa' }}>
                      {m.availability === 'active' ? '可用' : '停用'}
                    </span>
                  </td>
                  <td style={tdStyle}>{m.deployment_status || '-'}</td>
                  <td style={tdStyle}>
                    <button style={{ fontSize: 12, padding: '4px 10px', border: '1px solid #d9d9d9', borderRadius: 4, background: '#fff', cursor: 'pointer' }} onClick={() => toggleAvailability(m.id, m.availability)}>
                      {m.availability === 'active' ? '停用' : '启用'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12 }}>
            <span style={{ fontSize: 12, color: '#888' }}>第 {page} / {totalPages} 页</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                style={pagerBtn}
                disabled={page <= 1}
                onClick={() => setPage(1)}
              >
                首页
              </button>
              <button
                style={pagerBtn}
                disabled={page <= 1}
                onClick={() => setPage(prev => Math.max(1, prev - 1))}
              >
                上一页
              </button>
              <button
                style={pagerBtn}
                disabled={page >= totalPages}
                onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
              >
                下一页
              </button>
              <button
                style={pagerBtn}
                disabled={page >= totalPages}
                onClick={() => setPage(totalPages)}
              >
                末页
              </button>
            </div>
          </div>
          {models.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无注册模型</div>}
        </>
      )}

      {tab === 'aliases' && (
        <div>
          {aliases?.providers?.length > 0 && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
              {aliases.providers.map((p: string) => (
                <span key={p} style={{ padding: '4px 12px', background: '#f0f5ff', color: '#1677ff', borderRadius: 12, fontSize: 13 }}>{p}</span>
              ))}
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 12 }}>
            {(aliases?.aliases ?? []).map((a: any) => (
              <div key={a.alias} style={{ background: '#fff', borderRadius: 8, padding: 14, boxShadow: '0 1px 3px rgba(0,0,0,.08)' }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{a.alias}</div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>{a.description}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                  <span style={tagStyle}>{a.provider}</span>
                  <span style={tagStyle}>{a.tier}</span>
                  <span style={tagStyle}>{((a.context_window ?? 0) / 1000).toFixed(0)}K ctx</span>
                  {a.real_model_id && <span style={{ ...tagStyle, fontFamily: 'monospace', color: '#555' }}>{a.real_model_id}</span>}
                </div>
              </div>
            ))}
          </div>
          {!aliases?.aliases?.length && <div style={{ color: '#aaa', marginTop: 20 }}>暂无别名配置</div>}
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
const tagStyle: React.CSSProperties = { fontSize: 11, padding: '2px 8px', borderRadius: 3, background: '#f5f5f5', color: '#666' };
const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14 };
const tableStyle: React.CSSProperties = { width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' };
const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
const pagerBtn: React.CSSProperties = {
  padding: '6px 12px',
  border: '1px solid #d9d9d9',
  borderRadius: 4,
  background: '#fff',
  cursor: 'pointer',
  fontSize: 12,
};
