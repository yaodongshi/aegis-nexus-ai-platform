import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { providersApi } from '../../lib/api';
import ProviderWizard from './wizard';

export default function ProvidersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [providers, setProviders] = useState<any[]>([]);
  const [showWizard, setShowWizard] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const focus = new URLSearchParams(location.search).get('focus');

  const load = () =>
    providersApi.list()
      .then(r => setProviders(r.items))
      .catch(e => setError(e.message));

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleEnabled = async (id: string, enabled: boolean) => {
    setError('');
    setNotice('');
    try {
      await providersApi.update(id, { enabled: !enabled });
      setNotice(!enabled ? '服务商已启用。' : '服务商已停用。');
      load();
    } catch (e: any) { setError(e.message); }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`确认删除服务商「${name}」？`)) return;
    setError('');
    setNotice('');
    try {
      await providersApi.delete(id);
      setNotice('服务商已删除。');
      load();
    } catch (e: any) { setError(e.message); }
  };

  const groupedProviders = providers.reduce((acc: Record<string, any[]>, item) => {
    const key = (item.provider_type || 'others').toLowerCase();
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  const providerGroups = Object.entries(groupedProviders).sort((a, b) => a[0].localeCompare(b[0]));

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1>AI 服务商管理</h1>
        <button style={btnPrimary} onClick={() => setShowWizard(true)}>+ 添加服务商</button>
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      {notice && <div style={{ color: '#1677ff', marginBottom: 12 }}>{notice}</div>}
      {focus === 'blocking_failed' && (
        <div style={{ marginBottom: 12, border: '1px solid #ffd591', background: '#fff7e6', color: '#ad6800', borderRadius: 8, padding: '10px 12px', fontSize: 13 }}>
          来自运行时阻断告警：请优先检查服务商密钥、Base URL 与启用状态，然后在模型页再次同步网关。
        </div>
      )}

      {showWizard && (
        <ProviderWizard
          embedded
          onCancel={() => setShowWizard(false)}
          onDone={(providerId) => {
            setShowWizard(false);
            navigate(`/providers/${providerId}`);
          }}
        />
      )}

      {/* 服务商列表（按供应商类型分组） */}
      {providerGroups.map(([groupName, groupItems]) => (
        <section key={groupName} style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', marginBottom: 8, gap: 10 }}>
            <h3 style={{ margin: 0, fontSize: 16 }}>{groupName}</h3>
            <span style={{ fontSize: 12, color: '#888' }}>{groupItems.length} 个服务商</span>
          </div>
          <table style={tableStyle}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                {['名称', 'Base URL', '启用状态', '创建时间', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {groupItems.map((p) => (
                <tr key={p.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={tdStyle}><span style={{ fontWeight: 500 }}>{p.name}</span></td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12, color: '#555', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.base_url}</td>
                  <td style={tdStyle}>
                    <button
                      onClick={() => toggleEnabled(p.id, p.enabled)}
                      style={{ fontSize: 12, padding: '4px 12px', border: 'none', borderRadius: 12, cursor: 'pointer', background: p.enabled ? '#f6ffed' : '#f5f5f5', color: p.enabled ? '#52c41a' : '#aaa' }}
                    >
                      {p.enabled ? '● 已启用' : '○ 已停用'}
                    </button>
                  </td>
                  <td style={{ ...tdStyle, fontSize: 12, color: '#aaa' }}>{new Date(p.created_at).toLocaleDateString()}</td>
                  <td style={{ ...tdStyle, display: 'flex', gap: 8 }}>
                    <button
                      style={{ fontSize: 12, padding: '4px 10px', background: '#f0f5ff', color: '#1677ff', border: '1px solid #adc6ff', borderRadius: 4, cursor: 'pointer' }}
                      onClick={() => navigate(`/providers/${p.id}`)}
                    >
                      详情
                    </button>
                    <button style={{ fontSize: 12, padding: '4px 10px', background: '#fff2f0', color: '#ff4d4f', border: '1px solid #ffccc7', borderRadius: 4, cursor: 'pointer' }} onClick={() => handleDelete(p.id, p.name)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      {providers.length === 0 && (
        <div style={{ color: '#aaa', marginTop: 20 }}>暂无服务商，点击「添加服务商」从预设快速接入</div>
      )}
    </div>
  );
}

const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14 };
const tableStyle: React.CSSProperties = { width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' };
const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
