import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { modelsApi, providersApi } from '../../lib/api';

export default function ProviderDetailPage() {
  const { providerId = '' } = useParams();
  const [provider, setProvider] = useState<any | null>(null);
  const [registeredModels, setRegisteredModels] = useState<any[]>([]);
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [selectedModels, setSelectedModels] = useState<Record<string, boolean>>({});
  const [modelMappings, setModelMappings] = useState<Array<{ alias: string; upstream_model: string; note: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [discovering, setDiscovering] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncingGateway, setSyncingGateway] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editingKey, setEditingKey] = useState(false);
  const [newApiKey, setNewApiKey] = useState('');
  const [savingKey, setSavingKey] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const p = await providersApi.get(providerId);
      setProvider(p);
      setModelMappings(Array.isArray(p.model_mappings)
        ? p.model_mappings
        : Array.isArray(p.metadata?.model_mapping)
          ? p.metadata.model_mapping
          : []);
      const modelResp = await modelsApi.list(undefined, p.id);
      setRegisteredModels(modelResp.items || []);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  const refreshDiscoveredModels = async (silent = false) => {
    if (!providerId) return;
    if (!silent) {
      setDiscovering(true);
      setError('');
      setNotice('');
    }
    try {
      const resp = await providersApi.discoverModels(providerId);
      const list = (resp.models || []).filter(Boolean);
      setDiscoveredModels(list);
      const defaults: Record<string, boolean> = {};
      for (const name of list) {
        if (!registeredNameSet.has(name.toLowerCase())) {
          defaults[name] = true;
        }
      }
      setSelectedModels(defaults);
      if (!silent) {
        setNotice(`已发现 ${list.length} 个模型。`);
      }
      return list;
    } catch (e: any) {
      if (!silent) {
        setError(e.message || '模型发现失败');
      }
      return [];
    } finally {
      if (!silent) {
        setDiscovering(false);
      }
    }
  };

  useEffect(() => {
    if (providerId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providerId]);

  const registeredNameSet = useMemo(() => {
    const set = new Set<string>();
    for (const m of registeredModels) set.add((m.name || '').toLowerCase());
    return set;
  }, [registeredModels]);

  useEffect(() => {
    if (!provider?.api_key_masked || discoveredModels.length > 0) return;
    refreshDiscoveredModels(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider?.id, provider?.api_key_masked, discoveredModels.length, registeredNameSet]);

  const discoverModels = async () => {
    await refreshDiscoveredModels(false);
  };

  const syncProvider = async () => {
    if (!provider) return;
    setSyncing(true);
    setError('');
    setNotice('');
    try {
      await providersApi.sync(provider.id, {
        target_apps: provider.apps || [],
        sync_models: true,
      });
      setNotice('服务商已同步到网关配置。');
      await load();
    } catch (e: any) {
      setError(e.message || '同步服务商失败');
    } finally {
      setSyncing(false);
    }
  };

  const syncGateway = async () => {
    setSyncingGateway(true);
    setError('');
    setNotice('');
    try {
      await providersApi.syncGateway();
      setNotice('已触发网关配置刷新。');
    } catch (e: any) {
      setError(e.message || '网关同步失败');
    } finally {
      setSyncingGateway(false);
    }
  };

  const addMappingRow = () => {
    setModelMappings((prev) => [...prev, { alias: '', upstream_model: '', note: '' }]);
  };

  const updateMappingRow = (index: number, patch: Partial<{ alias: string; upstream_model: string; note: string }>) => {
    setModelMappings((prev) => prev.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  };

  const removeMappingRow = (index: number) => {
    setModelMappings((prev) => prev.filter((_, rowIndex) => rowIndex !== index));
  };

  const saveMappings = async () => {
    if (!provider) return;
    setError('');
    setNotice('');

    const cleanedMappings = modelMappings
      .map((row) => ({
        alias: row.alias.trim(),
        upstream_model: row.upstream_model.trim(),
        note: row.note.trim(),
      }))
      .filter((row) => row.alias && row.upstream_model);

    try {
      await providersApi.update(provider.id, {
        model_mappings: cleanedMappings,
        metadata: {
          ...(provider.metadata || {}),
          model_mapping: cleanedMappings,
          model_mapping_updated_at: new Date().toISOString(),
        },
      });
      setNotice(`已保存 ${cleanedMappings.length} 条模型映射。`);
      await load();
    } catch (e: any) {
      setError(e.message || '保存映射失败');
    }
  };

  const saveApiKey = async () => {
    if (!provider || !newApiKey.trim()) return;
    setSavingKey(true);
    setError('');
    setNotice('');
    try {
      await providersApi.update(provider.id, { api_key: newApiKey.trim() });
      setNotice('API Key 已保存，请点击"同步服务商"使网关生效。');
      setEditingKey(false);
      setNewApiKey('');
      await load();
    } catch (e: any) {
      setError(e.message || '保存 API Key 失败');
    } finally {
      setSavingKey(false);
    }
  };

  const registerModelsFromMappings = async () => {
    if (!provider) return;
    const usableMappings = modelMappings
      .map((row) => ({
        alias: row.alias.trim(),
        upstream_model: row.upstream_model.trim(),
      }))
      .filter((row) => row.alias && row.upstream_model);

    if (usableMappings.length === 0) {
      setError('请先保存至少一条有效映射。');
      return;
    }

    setRegistering(true);
    setError('');
    setNotice('');
    const endpoint = `${provider.base_url.replace(/\/$/, '')}/v1/chat/completions`;
    let okCount = 0;

    try {
      const payloads = usableMappings
        .filter((mapping) => !registeredNameSet.has(mapping.alias.toLowerCase()))
        .map((mapping) => ({
          provider: provider.provider_type,
          provider_id: provider.id,
          upstream_model: mapping.upstream_model,
          name: mapping.alias,
          endpoint,
          context_window: 8192,
          cost_tier: 'medium',
          deployment_status: 'active',
          labels: {
            provider_name: provider.name,
            source: 'mapping_rule',
          },
        }));

      if (payloads.length > 0) {
        const result = await modelsApi.batchRegister(payloads);
        okCount = result.registered || payloads.length;
      }
      setNotice(`已按映射规则注册 ${okCount} 个模型。`);
      await load();
    } catch (e: any) {
      setError(e.message || '按映射注册失败');
    } finally {
      setRegistering(false);
    }
  };

  const toggleSelect = (name: string) => {
    setSelectedModels((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const selectAllDiscovered = () => {
    const next: Record<string, boolean> = {};
    for (const name of discoveredModels) {
      if (!registeredNameSet.has(name.toLowerCase())) {
        next[name] = true;
      }
    }
    setSelectedModels(next);
  };

  const clearSelectedDiscovered = () => {
    setSelectedModels({});
  };

  const invertSelectedDiscovered = () => {
    const next: Record<string, boolean> = {};
    for (const name of discoveredModels) {
      if (registeredNameSet.has(name.toLowerCase())) continue;
      next[name] = !selectedModels[name];
    }
    setSelectedModels(next);
  };

  const registerSelectedModels = async () => {
    const picked = discoveredModels.filter((name) => selectedModels[name]);
    if (!provider || picked.length === 0) {
      setError('请先选择至少一个模型。');
      return;
    }

    setRegistering(true);
    setError('');
    setNotice('');
    let okCount = 0;
    const endpoint = `${provider.base_url.replace(/\/$/, '')}/v1/chat/completions`;

    try {
      const payloads = picked
        .filter((name) => !registeredNameSet.has(name.toLowerCase()))
        .map((name) => ({
          provider: provider.provider_type,
          provider_id: provider.id,
          upstream_model: name,
          name,
          endpoint,
          context_window: 8192,
          cost_tier: 'medium',
          deployment_status: 'active',
          labels: {
            provider_name: provider.name,
          },
        }));

      if (payloads.length > 0) {
        const result = await modelsApi.batchRegister(payloads);
        okCount = result.registered || payloads.length;
      }
      setNotice(`成功注册 ${okCount} 个模型到模型注册表。`);
      await load();
    } catch (e: any) {
      setError(e.message || '注册模型失败');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Link to="/providers" style={{ color: '#1677ff', textDecoration: 'none', fontSize: 13 }}>
          {'<- 返回服务商列表'}
        </Link>
      </div>

      <h1 style={{ marginTop: 0 }}>服务商详情</h1>

      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {notice && <div style={{ color: '#1677ff', marginBottom: 12 }}>{notice}</div>}

      {loading ? (
        <div style={{ color: '#666' }}>加载中...</div>
      ) : provider ? (
        <>
          <div style={cardStyle}>
            <div style={rowStyle}><strong>名称：</strong>{provider.name}</div>
            <div style={rowStyle}><strong>类型：</strong>{provider.provider_type}</div>
            <div style={rowStyle}><strong>Scope：</strong>{provider.scope}</div>
            <div style={rowStyle}><strong>Base URL：</strong><span style={{ fontFamily: 'monospace' }}>{provider.base_url}</span></div>
            <div style={rowStyle}><strong>状态：</strong>{provider.enabled ? '已启用' : '已停用'}</div>
            <div style={{ ...rowStyle, alignItems: 'flex-start', gap: 8 }}>
              <strong style={{ flexShrink: 0 }}>API Key：</strong>
              {editingKey ? (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center', flex: 1 }}>
                  <input
                    style={{ ...inputStyle, flex: 1, fontFamily: 'monospace' }}
                    type="password"
                    placeholder="输入新的 API Key（如 sk-xxx...）"
                    value={newApiKey}
                    onChange={(e) => setNewApiKey(e.target.value)}
                    autoFocus
                  />
                  <button style={btnPrimary} onClick={saveApiKey} disabled={savingKey || !newApiKey.trim()}>
                    {savingKey ? '保存中...' : '确认保存'}
                  </button>
                  <button style={btnSecondary} onClick={() => { setEditingKey(false); setNewApiKey(''); }}>
                    取消
                  </button>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontFamily: 'monospace', color: provider.api_key_masked ? '#333' : '#999' }}>
                    {provider.api_key_masked || '❌ 未配置'}
                  </span>
                  <button style={btnSecondary} onClick={() => setEditingKey(true)}>
                    {provider.api_key_masked ? '更换 Key' : '配置 Key'}
                  </button>
                </div>
              )}
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
              <button style={btnSecondary} onClick={discoverModels} disabled={discovering}>
                {discovering ? '发现中...' : '发现模型'}
              </button>
              <button style={btnSecondary} onClick={syncProvider} disabled={syncing}>
                {syncing ? '同步中...' : '同步服务商'}
              </button>
              <button style={btnSecondary} onClick={syncGateway} disabled={syncingGateway}>
                {syncingGateway ? '刷新中...' : '刷新网关'}
              </button>
            </div>
          </div>

          <div style={cardStyle}>
            <div style={sectionHeaderStyle}>
              <h2 style={{ margin: 0, fontSize: 18 }}>模型映射规则</h2>
              <button style={btnSecondary} onClick={addMappingRow}>+ 新增映射</button>
            </div>
            <div style={{ color: '#666', fontSize: 13, marginBottom: 12 }}>
              这里维护“业务模型名 -&gt; 上游模型名”的映射，保存后会写入 provider.metadata.model_mapping。
            </div>
            {modelMappings.length > 0 ? (
              <div style={{ display: 'grid', gap: 10 }}>
                {modelMappings.map((row, index) => (
                  <div key={`${index}-${row.alias}`} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8, alignItems: 'center' }}>
                    <input
                      style={inputStyle}
                      placeholder="业务模型名（alias）"
                      value={row.alias}
                      onChange={(e) => updateMappingRow(index, { alias: e.target.value })}
                    />
                    <input
                      style={inputStyle}
                      placeholder="上游模型名"
                      value={row.upstream_model}
                      onChange={(e) => updateMappingRow(index, { upstream_model: e.target.value })}
                    />
                    <input
                      style={inputStyle}
                      placeholder="备注"
                      value={row.note}
                      onChange={(e) => updateMappingRow(index, { note: e.target.value })}
                    />
                    <button style={btnDanger} onClick={() => removeMappingRow(index)}>删除</button>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ color: '#999', fontSize: 13 }}>暂无映射规则，点击“新增映射”开始配置。</div>
            )}
            <div style={{ marginTop: 12 }}>
              <button style={btnPrimary} onClick={saveMappings}>保存映射规则</button>
              <button style={{ ...btnSecondary, marginLeft: 8 }} onClick={registerModelsFromMappings} disabled={registering}>
                {registering ? '注册中...' : '按映射注册模型'}
              </button>
            </div>
          </div>

          <div style={sectionHeaderStyle}>
            <h2 style={{ margin: 0, fontSize: 18 }}>可用模型（来自该服务商）</h2>
          </div>

          {discoveredModels.length > 0 ? (
            <div style={cardStyle}>
              <div style={{ marginBottom: 10, color: '#666', fontSize: 13 }}>
                勾选后可一键注册到模型注册表，并自动关联该服务商。
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                <button style={btnSecondary} onClick={selectAllDiscovered}>全选</button>
                <button style={btnSecondary} onClick={invertSelectedDiscovered}>反选</button>
                <button style={btnSecondary} onClick={clearSelectedDiscovered}>清空</button>
                <span style={{ marginLeft: 'auto', color: '#666', fontSize: 13 }}>
                  已选 {Object.keys(selectedModels).filter((name) => selectedModels[name]).length} / {discoveredModels.length}
                </span>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ ...tableStyle, boxShadow: 'none', border: '1px solid #f0f0f0' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <th style={thStyle}>选择</th>
                      <th style={thStyle}>模型名</th>
                      <th style={thStyle}>状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {discoveredModels.map((name) => {
                      const alreadyRegistered = registeredNameSet.has(name.toLowerCase());
                      return (
                        <tr key={name} style={{ borderBottom: '1px solid #f9f9f9' }}>
                          <td style={tdStyle}>
                            <input
                              type="checkbox"
                              checked={!!selectedModels[name]}
                              disabled={alreadyRegistered}
                              onChange={() => toggleSelect(name)}
                            />
                          </td>
                          <td style={{ ...tdStyle, fontFamily: 'monospace' }}>{name}</td>
                          <td style={tdStyle}>
                            {alreadyRegistered ? (
                              <span style={{ fontSize: 12, color: '#999' }}>已注册</span>
                            ) : selectedModels[name] ? (
                              <span style={{ fontSize: 12, color: '#1677ff' }}>已选中</span>
                            ) : (
                              <span style={{ fontSize: 12, color: '#999' }}>未选中</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: 12 }}>
                <button style={btnPrimary} onClick={registerSelectedModels} disabled={registering}>
                  {registering ? '注册中...' : '注册选中模型'}
                </button>
              </div>
            </div>
          ) : (
            <div style={{ color: '#999', marginBottom: 16 }}>尚未拉取模型，请先点击“发现模型”。</div>
          )}

          <div style={sectionHeaderStyle}>
            <h2 style={{ margin: 0, fontSize: 18 }}>已注册模型（关联该供应商）</h2>
            <span style={{ color: '#888', fontSize: 12 }}>provider_id = {provider?.id || '-'}</span>
          </div>

          <table style={tableStyle}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                {['模型名', 'Endpoint', '可用性', '上下文', '费用档'].map((h) => (
                  <th key={h} style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {registeredModels.map((m) => (
                <tr key={m.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={tdStyle}><span style={{ fontFamily: 'monospace' }}>{m.name}</span></td>
                  <td style={{ ...tdStyle, maxWidth: 380, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'monospace', fontSize: 12 }}>{m.endpoint}</td>
                  <td style={tdStyle}>{m.availability}</td>
                  <td style={tdStyle}>{m.context_window}</td>
                  <td style={tdStyle}>{m.cost_tier}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {registeredModels.length === 0 && <div style={{ color: '#999', marginTop: 12 }}>该供应商类型下暂无注册模型。</div>}
        </>
      ) : (
        <div style={{ color: 'red' }}>未找到该服务商。</div>
      )}
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  boxShadow: '0 1px 4px rgba(0,0,0,.08)',
  padding: 16,
  marginBottom: 16,
};

const sectionHeaderStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: 10,
};

const rowStyle: React.CSSProperties = { marginBottom: 6, fontSize: 14 };

const inputStyle: React.CSSProperties = {
  padding: '6px 10px',
  border: '1px solid #d9d9d9',
  borderRadius: 4,
  fontSize: 14,
  outline: 'none',
};

const btnPrimary: React.CSSProperties = {
  padding: '7px 16px',
  background: '#1677ff',
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 14,
};

const btnSecondary: React.CSSProperties = {
  padding: '7px 16px',
  background: '#fff',
  color: '#666',
  border: '1px solid #d9d9d9',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 14,
};

const btnDanger: React.CSSProperties = {
  padding: '7px 14px',
  background: '#fff1f0',
  color: '#ff4d4f',
  border: '1px solid #ffccc7',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 14,
};

const tableStyle: React.CSSProperties = {
  width: '100%',
  background: '#fff',
  borderRadius: 8,
  borderCollapse: 'collapse',
  boxShadow: '0 1px 4px rgba(0,0,0,.08)',
};
const thStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontSize: 13,
  color: '#888',
  fontWeight: 500,
};
const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: 14,
};
