import React, { useEffect, useState } from 'react';

import { modelsApi, providersApi } from '../../lib/api';

type WizardProps = {
  embedded?: boolean;
  onDone?: (providerId: string) => void;
  onCancel?: () => void;
};

export default function ProviderWizard({ embedded = false, onDone, onCancel }: WizardProps) {
  const [presets, setPresets] = useState<any[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<any | null>(null);
  const [form, setForm] = useState({ name: '', provider_type: '', base_url: '', api_key: '', scope: 'app' });
  const [creating, setCreating] = useState(false);
  const [provider, setProvider] = useState<any | null>(null);
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [selectedModels, setSelectedModels] = useState<Record<string, boolean>>({});
  const [loadingModels, setLoadingModels] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    providersApi.presets().then(setPresets).catch(() => {});
  }, []);

  const selectPreset = (preset: any) => {
    setSelectedPreset(preset);
    setForm((prev) => ({
      ...prev,
      name: preset.name,
      provider_type: preset.provider_type,
      base_url: preset.default_base_url,
    }));
  };

  const discoverModels = async (providerId: string) => {
    setLoadingModels(true);
    setError('');
    try {
      const resp = await providersApi.discoverModels(providerId);
      const list = (resp.models || []).filter(Boolean);
      setDiscoveredModels(list);
      const defaults: Record<string, boolean> = {};
      for (const name of list) {
        defaults[name] = true;
      }
      setSelectedModels(defaults);
      setNotice(`已发现 ${list.length} 个模型，请勾选需要注册的模型。`);
    } catch (err: any) {
      setError(err.message || '模型发现失败');
      setDiscoveredModels([]);
      setSelectedModels({});
    } finally {
      setLoadingModels(false);
    }
  };

  const createProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    setNotice('');
    try {
      const created = await providersApi.create({ ...form, preset_key: selectedPreset?.key });
      setProvider(created);
      setNotice('服务商已创建，正在获取模型列表...');
      await discoverModels(created.id);
    } catch (err: any) {
      setError(err.message || '创建服务商失败');
    } finally {
      setCreating(false);
    }
  };

  const toggleModel = (name: string) => {
    setSelectedModels((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const selectAllModels = () => {
    const next: Record<string, boolean> = {};
    for (const name of discoveredModels) {
      next[name] = true;
    }
    setSelectedModels(next);
  };

  const clearAllModels = () => {
    setSelectedModels({});
  };

  const invertAllModels = () => {
    const next: Record<string, boolean> = {};
    for (const name of discoveredModels) {
      next[name] = !selectedModels[name];
    }
    setSelectedModels(next);
  };

  const finish = () => {
    if (provider?.id) onDone?.(provider.id);
  };

  const registerSelectedModels = async () => {
    if (!provider) {
      setError('请先创建服务商。');
      return;
    }
    const picked = discoveredModels.filter((name) => selectedModels[name]);
    if (picked.length === 0) {
      setError('请先选择至少一个模型。');
      return;
    }

    setRegistering(true);
    setError('');
    setNotice('');
    let okCount = 0;
    const endpoint = `${provider.base_url.replace(/\/$/, '')}/v1/chat/completions`;

    try {
      const payloads = picked.map((name) => ({
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
            source: 'provider_wizard',
          },
        }));
      if (payloads.length > 0) {
        const result = await modelsApi.batchRegister(payloads);
        okCount = result.registered || payloads.length;
      }
      setNotice(`已注册 ${okCount} 个模型。`);
      finish();
    } catch (err: any) {
      setError(err.message || '注册模型失败');
    } finally {
      setRegistering(false);
    }
  };

  return embedded ? (
    <div style={pageStyle}>
      <div style={contentStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <div style={{ fontSize: 13, color: '#1677ff', fontWeight: 600 }}>添加 AI 服务商</div>
          {onCancel && (
            <button type="button" onClick={onCancel} style={linkButtonStyle}>关闭</button>
          )}
        </div>
        {renderBody()}
      </div>
    </div>
  ) : (
    <div>
      <div style={{ marginBottom: 12 }}>
        <button type="button" onClick={onCancel} style={linkButtonStyle}>← 返回服务商列表</button>
      </div>
      {renderBody()}
    </div>
  );

  function renderBody() {
    return (
      <>
        <h1 style={{ marginTop: 0 }}>添加 AI 服务商</h1>
        <div style={{ color: '#666', marginBottom: 16 }}>先填写服务商信息，保存后会自动拉取该服务商的模型列表供你选择。</div>

        {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
        {notice && <div style={{ color: '#1677ff', marginBottom: 12 }}>{notice}</div>}

        {!provider ? (
          <div style={cardStyle}>
            <div style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>从预设快速选取：</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              {presets.map((preset) => (
                <button
                  key={preset.key}
                  type="button"
                  onClick={() => selectPreset(preset)}
                  style={{
                    padding: '6px 14px',
                    border: selectedPreset?.key === preset.key ? '2px solid #1677ff' : '1px solid #d9d9d9',
                    borderRadius: 4,
                    background: selectedPreset?.key === preset.key ? '#e6f4ff' : '#fff',
                    cursor: 'pointer',
                    fontSize: 13,
                  }}
                >
                  {preset.name}
                </button>
              ))}
            </div>

            <form onSubmit={createProvider}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <input style={inputStyle} placeholder="名称" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} required />
                <input style={inputStyle} placeholder="类型（如 openai、anthropic）" value={form.provider_type} onChange={(e) => setForm((f) => ({ ...f, provider_type: e.target.value }))} required />
                <input style={{ ...inputStyle, width: 260 }} placeholder="Base URL" value={form.base_url} onChange={(e) => setForm((f) => ({ ...f, base_url: e.target.value }))} required />
                <input style={{ ...inputStyle, width: 200 }} placeholder="API Key" type="password" value={form.api_key} onChange={(e) => setForm((f) => ({ ...f, api_key: e.target.value }))} />
                <select style={inputStyle} value={form.scope} onChange={(e) => setForm((f) => ({ ...f, scope: e.target.value }))}>
                  <option value="app">app（应用级）</option>
                  <option value="unified">unified（统一网关）</option>
                </select>
                <button style={btnPrimary} type="submit" disabled={creating}>{creating ? '创建中...' : '确认添加'}</button>
                {embedded && onCancel && (
                  <button type="button" style={btnGhost} onClick={onCancel}>取消</button>
                )}
              </div>
            </form>
          </div>
        ) : (
          <div style={cardStyle}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 18 }}>选择该服务商的模型</h2>
                <div style={{ fontSize: 12, color: '#888' }}>{provider.name} · {provider.base_url}</div>
              </div>
              <button type="button" style={btnSecondary} onClick={() => discoverModels(provider.id)} disabled={loadingModels}>
                {loadingModels ? '重新发现中...' : '重新发现模型'}
              </button>
            </div>

            {loadingModels ? (
              <div style={{ color: '#888' }}>正在发现模型...</div>
            ) : discoveredModels.length > 0 ? (
              <>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
                  <button type="button" style={btnSecondary} onClick={selectAllModels}>全选</button>
                  <button type="button" style={btnSecondary} onClick={invertAllModels}>反选</button>
                  <button type="button" style={btnSecondary} onClick={clearAllModels}>清空</button>
                  <span style={{ marginLeft: 'auto', color: '#666', fontSize: 13 }}>
                    已选 {Object.values(selectedModels).filter(Boolean).length} / {discoveredModels.length}
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
                      {discoveredModels.map((name) => (
                        <tr key={name} style={{ borderBottom: '1px solid #f9f9f9' }}>
                          <td style={tdStyle}>
                            <input type="checkbox" checked={!!selectedModels[name]} onChange={() => toggleModel(name)} />
                          </td>
                          <td style={{ ...tdStyle, fontFamily: 'monospace' }}>{name}</td>
                          <td style={tdStyle}>
                            <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: selectedModels[name] ? '#e6f4ff' : '#fafafa', color: selectedModels[name] ? '#1677ff' : '#999' }}>
                              {selectedModels[name] ? '已选中' : '未选中'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
                  <button type="button" style={btnPrimary} onClick={registerSelectedModels} disabled={registering}>
                    {registering ? '注册中...' : '注册选中模型'}
                  </button>
                  {onCancel && <button type="button" style={btnGhost} onClick={onCancel}>关闭</button>}
                </div>
              </>
            ) : (
              <div style={{ color: '#999' }}>没有发现可用模型，请检查 API Key 或 Base URL。</div>
            )}
          </div>
        )}
      </>
    );
  }
}

const pageStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 1000,
  background: 'rgba(15, 23, 42, 0.45)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: 24,
};

const contentStyle: React.CSSProperties = {
  width: 'min(1200px, 100%)',
  maxHeight: 'calc(100vh - 48px)',
  overflow: 'auto',
  background: '#f7f9fc',
  borderRadius: 16,
  padding: 24,
  boxShadow: '0 24px 80px rgba(0,0,0,.25)',
};

const cardStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  boxShadow: '0 1px 4px rgba(0,0,0,.08)',
  padding: 16,
  marginBottom: 16,
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

const btnGhost: React.CSSProperties = {
  padding: '7px 16px',
  background: '#fff',
  color: '#666',
  border: '1px solid #d9d9d9',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 14,
};

const linkButtonStyle: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  color: '#1677ff',
  cursor: 'pointer',
  padding: 0,
  fontSize: 13,
};

const inputStyle: React.CSSProperties = {
  padding: '7px 10px',
  border: '1px solid #d9d9d9',
  borderRadius: 4,
  fontSize: 14,
};