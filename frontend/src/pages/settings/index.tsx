import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { authApi, clearToken, settingsApi, runtimeApi, usersAdminApi } from '../../lib/api';

type SettingsTab = 'personal' | 'runtime' | 'users';

const TOOL_OPTIONS = [
  { value: 'opencode', label: 'OpenCode', hint: '将生成的 JSON 保存到 ~/.config/opencode/config.json' },
  { value: 'claude-code', label: 'Claude Code', hint: '将 env 字段合并到 ~/.claude/settings.json，重启 claude 生效' },
  { value: 'continue', label: 'Continue.dev', hint: '将 models 数组合并到 ~/.continue/config.json' },
  { value: 'cursor', label: 'Cursor', hint: '在 Cursor Settings > Models 填入 api_key 和 base_url' },
];

export default function SettingsPage() {
  const location = useLocation();
  const [tab, setTab] = useState<SettingsTab>('personal');

  // ── 个人偏好 ──
  const [settings, setSettings] = useState<any>(null);
  const [locales, setLocales] = useState<any[]>([]);
  const [saved, setSaved] = useState(false);
  const [settingsLoading, setSettingsLoading] = useState(true);

  // ── 运行时配置 ──
  const [runtimeConfig, setRuntimeConfig] = useState<any>(null);
  const [runtimeLoading, setRuntimeLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState<any>(null);
  const [clientApp, setClientApp] = useState('opencode');
  const [clientConfig, setClientConfig] = useState<any>(null);
  const [copied, setCopied] = useState(false);
  const [virtualKey, setVirtualKey] = useState('');
  const [gatewayUrl, setGatewayUrl] = useState('');

  const [error, setError] = useState('');
  const [runtimeError, setRuntimeError] = useState('');

  // ── 用户管理（管理员） ──
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [creatingUser, setCreatingUser] = useState(false);
  const [userForm, setUserForm] = useState({ username: '', email: '', password: '', role: 'member' });

  const isAdmin = currentUser?.role === 'admin';

  const loadUsers = async () => {
    if (!isAdmin) return;
    setUsersLoading(true);
    try {
      const items = await usersAdminApi.list();
      setUsers(items);
    } catch (e: any) {
      setError(e?.message || '用户列表加载失败');
    } finally {
      setUsersLoading(false);
    }
  };

  const loadRuntimeConfig = async () => {
    setRuntimeLoading(true);
    setRuntimeError('');
    try {
      const preview = await runtimeApi.previewLitellm();
      setRuntimeConfig(preview);
    } catch (e: any) {
      setRuntimeConfig(null);
      setRuntimeError(e?.message || '运行时配置加载失败');
    } finally {
      setRuntimeLoading(false);
    }
  };

  useEffect(() => {
    authApi.me().then(setCurrentUser).catch(() => setCurrentUser(null));
    settingsApi
      .getMe()
      .then(setSettings)
      .catch(e => {
        const message = e?.message || '';
        if (
          message.includes('User not found')
          || message.includes('401')
          || message.includes('Token expired')
          || message.includes('Invalid token')
        ) {
          clearToken();
          window.location.assign('/login');
          return;
        }
        setError(message);
      })
      .finally(() => setSettingsLoading(false));
    settingsApi.locales().then(setLocales).catch(() => setLocales([]));
    loadRuntimeConfig();
  }, []);

  useEffect(() => {
    if (isAdmin) {
      loadUsers();
    }
  }, [isAdmin]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const queryTab = new URLSearchParams(location.search).get('tab');
    if (location.pathname === '/users' || queryTab === 'users') {
      setTab('users');
      return;
    }
    if (queryTab === 'runtime') {
      setTab('runtime');
      return;
    }
    if (queryTab === 'personal') {
      setTab('personal');
    }
  }, [location.pathname, location.search]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const updated = await settingsApi.updateMe({
        language: settings.language,
        theme: settings.theme,
        timezone: settings.timezone,
        notifications_enabled: settings.notifications_enabled,
      });
      setSettings(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) { setError(e.message); }
  };

  const handleApplyLitellm = async () => {
    if (!confirm('确认将当前配置推送到 LiteLLM 网关？')) return;
    setApplying(true);
    try {
      const result = await runtimeApi.applyLitellm();
      setApplyResult(result);
    } catch (e: any) { setError(e.message); }
    finally { setApplying(false); }
  };

  const handleLoadClientConfig = async () => {
    try {
      const cfg = await runtimeApi.clientConfig(clientApp, {
        apiKey: virtualKey.trim() || undefined,
        baseUrl: gatewayUrl.trim() || undefined,
      });
      setClientConfig(cfg);
      setCopied(false);
    } catch (e: any) { setError(e.message); }
  };

  const handleCopy = () => {
    if (!clientConfig) return;
    const text = JSON.stringify(clientConfig.config ?? clientConfig, null, 2);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingUser(true);
    try {
      await usersAdminApi.create({
        username: userForm.username,
        email: userForm.email,
        password: userForm.password,
        role: userForm.role,
      });
      setUserForm({ username: '', email: '', password: '', role: 'member' });
      await loadUsers();
    } catch (e: any) {
      setError(e?.message || '创建用户失败');
    } finally {
      setCreatingUser(false);
    }
  };

  const handleToggleUser = async (userId: string, isActive: boolean) => {
    try {
      await usersAdminApi.updateStatus(userId, !isActive);
      await loadUsers();
    } catch (e: any) {
      setError(e?.message || '更新用户状态失败');
    }
  };

  const handleEditUser = async (user: any) => {
    const username = prompt('用户名', user.username);
    if (username === null) return;
    const email = prompt('邮箱', user.email);
    if (email === null) return;
    const role = prompt('角色（admin/member）', user.role);
    if (role === null) return;

    try {
      await usersAdminApi.update(user.id, {
        username: username.trim(),
        email: email.trim(),
        role: role.trim(),
      });
      await loadUsers();
    } catch (e: any) {
      setError(e?.message || '更新用户失败');
    }
  };

  const handleResetUserPassword = async (user: any) => {
    const nextPassword = prompt(`为用户 ${user.username} 设置新密码（至少8位）`);
    if (nextPassword === null) return;
    if (nextPassword.trim().length < 8) {
      setError('密码长度至少8位');
      return;
    }

    try {
      await usersAdminApi.resetPassword(user.id, nextPassword.trim());
      alert('密码已重置');
    } catch (e: any) {
      setError(e?.message || '重置密码失败');
    }
  };

  if (settingsLoading) return <div>加载中...</div>;
  if (!settings) {
    return (
      <div>
        <div style={{ color: '#ff4d4f', marginBottom: 12 }}>设置加载失败：{error || '请重新登录后重试'}</div>
        <button style={btnPrimary} onClick={() => window.location.reload()}>刷新重试</button>
      </div>
    );
  }

  const selectedTool = TOOL_OPTIONS.find(t => t.value === clientApp);

  return (
    <div>
      <h1 style={{ marginBottom: 20 }}>设置中心</h1>
      {error && <div style={{ color: 'red', marginBottom: 12, padding: '8px 12px', background: '#fff2f0', borderRadius: 4 }}>{error}<button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer', color: '#ff4d4f' }}>✕</button></div>}

      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: '2px solid #f0f0f0' }}>
        {([
          ['personal', '个人偏好'],
          ['runtime', '运行时配置'],
          ['users', '用户管理'],
        ] as [SettingsTab, string][]).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={tabBtn(tab === key)}>{label}</button>
        ))}
      </div>

      {tab === 'users' && !isAdmin && (
        <div style={{ background: '#fff7e6', color: '#ad6800', border: '1px solid #ffd591', borderRadius: 8, padding: 16, marginBottom: 16 }}>
          当前账号不是管理员，无法访问用户管理。请使用管理员账号登录后重试。
        </div>
      )}

      {/* ── 个人偏好 ── */}
      {tab === 'personal' && (
        <div style={{ background: '#fff', borderRadius: 8, padding: 24, maxWidth: 540, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
          <form onSubmit={handleSave}>
            <FormRow label="界面语言">
              <select style={inputStyle} value={settings.language} onChange={e => setSettings((s: any) => ({ ...s, language: e.target.value }))}>
                {locales.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
              </select>
            </FormRow>
            <FormRow label="界面主题">
              <select style={inputStyle} value={settings.theme} onChange={e => setSettings((s: any) => ({ ...s, theme: e.target.value }))}>
                <option value="light">亮色模式</option>
                <option value="dark">暗色模式</option>
              </select>
            </FormRow>
            <FormRow label="时区">
              <input style={inputStyle} value={settings.timezone} onChange={e => setSettings((s: any) => ({ ...s, timezone: e.target.value }))} />
            </FormRow>
            <FormRow label="推送通知">
              <label style={{ cursor: 'pointer', fontSize: 14 }}>
                <input type="checkbox" checked={settings.notifications_enabled} onChange={e => setSettings((s: any) => ({ ...s, notifications_enabled: e.target.checked }))} style={{ marginRight: 6 }} />
                开启推送通知
              </label>
            </FormRow>
            <div style={{ marginTop: 20 }}>
              <button style={btnPrimary} type="submit">保存设置</button>
              {saved && <span style={{ marginLeft: 12, color: '#52c41a', fontSize: 14 }}>已保存 ✓</span>}
            </div>
          </form>
        </div>
      )}

      {/* ── 运行时配置 ── */}
      {tab === 'runtime' && (
        <div>
          {/* LiteLLM Config */}
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>LiteLLM 网关配置</div>
                <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>预览当前配置并推送到网关容器</div>
              </div>
              <button style={btnPrimary} onClick={handleApplyLitellm} disabled={applying}>
                {applying ? '推送中...' : '推送到网关'}
              </button>
            </div>
            {applyResult && (
              <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6, padding: '10px 14px', marginBottom: 12, fontSize: 13 }}>
                ✅ 推送结果：{applyResult.message ?? JSON.stringify(applyResult)}
              </div>
            )}
            {runtimeConfig ? (
              <pre style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: 14, fontSize: 12, overflowX: 'auto', maxHeight: 320, lineHeight: 1.6 }}>
                {JSON.stringify(runtimeConfig, null, 2)}
              </pre>
            ) : (
              <div style={{ color: '#aaa' }}>
                {runtimeLoading
                  ? '配置加载中...'
                  : `配置不可用：${runtimeError || '请检查登录态或网关配置'}`}
                {!runtimeLoading && (
                  <button
                    style={{ ...btnPrimary, marginLeft: 10, padding: '4px 12px', fontSize: 12 }}
                    onClick={loadRuntimeConfig}
                  >
                    重试
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Client Config */}
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 4 }}>客户端配置生成</div>
            <div style={{ fontSize: 12, color: '#888', marginBottom: 14 }}>
              为你的 IDE/AI 工具生成接入团队网关的配置，使用你自己的虚拟 Key 即可直接使用
            </div>

            {/* 工具选择卡片 */}
            <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
              {TOOL_OPTIONS.map(t => (
                <button
                  key={t.value}
                  onClick={() => { setClientApp(t.value); setClientConfig(null); setCopied(false); }}
                  style={{
                    padding: '6px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13,
                    border: clientApp === t.value ? '2px solid #1677ff' : '1px solid #d9d9d9',
                    background: clientApp === t.value ? '#e6f4ff' : '#fff',
                    color: clientApp === t.value ? '#1677ff' : '#333',
                    fontWeight: clientApp === t.value ? 600 : 400,
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>

            {/* 工具提示 */}
            {selectedTool && (
              <div style={{ fontSize: 12, color: '#888', marginBottom: 12, padding: '6px 10px', background: '#f5f5f5', borderRadius: 4 }}>
                💡 {selectedTool.hint}
              </div>
            )}

            {/* 虚拟 Key 和网关地址输入 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ fontSize: 13, color: '#555', width: 90, flexShrink: 0 }}>虚拟 Key</label>
                <input
                  style={{ ...inputStyle, flex: 1, fontFamily: 'monospace', fontSize: 12 }}
                  placeholder="sk-... （不填则使用 Master Key，建议填入虚拟 Key）"
                  value={virtualKey}
                  onChange={e => setVirtualKey(e.target.value)}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <label style={{ fontSize: 13, color: '#555', width: 90, flexShrink: 0 }}>网关地址</label>
                <input
                  style={{ ...inputStyle, flex: 1, fontFamily: 'monospace', fontSize: 12 }}
                  placeholder="http://127.0.0.1:3000/v1（留空使用默认值）"
                  value={gatewayUrl}
                  onChange={e => setGatewayUrl(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
              <button style={btnPrimary} onClick={handleLoadClientConfig}>生成配置</button>
              {clientConfig && (
                <button
                  style={{ ...btnPrimary, background: copied ? '#52c41a' : '#52c41a' }}
                  onClick={handleCopy}
                >
                  {copied ? '已复制 ✓' : '复制到剪贴板'}
                </button>
              )}
            </div>

            {clientConfig && (
              <pre style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: 14, fontSize: 12, overflowX: 'auto', maxHeight: 360, lineHeight: 1.6 }}>
                {JSON.stringify(clientConfig.config ?? clientConfig, null, 2)}
              </pre>
            )}

            {/* 模型列表徽章 */}
            {clientConfig?.models && clientConfig.models.length > 0 && (
              <div style={{ marginTop: 10 }}>
                <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>可用模型（{clientConfig.model_count ?? clientConfig.models.length} 个）：</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {clientConfig.models.map((m: string) => (
                    <span key={m} style={{ padding: '2px 8px', background: '#f0f0f0', borderRadius: 3, fontSize: 11, color: '#555' }}>{m}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'users' && isAdmin && (
        <div>
          <div style={{ background: '#fff', borderRadius: 8, padding: 24, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
            <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 12 }}>创建用户</div>
            <form onSubmit={handleCreateUser} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <input
                style={inputStyle}
                placeholder="用户名"
                value={userForm.username}
                onChange={e => setUserForm(v => ({ ...v, username: e.target.value }))}
                required
              />
              <input
                style={inputStyle}
                placeholder="邮箱"
                type="email"
                value={userForm.email}
                onChange={e => setUserForm(v => ({ ...v, email: e.target.value }))}
                required
              />
              <input
                style={inputStyle}
                placeholder="密码（至少8位）"
                type="password"
                value={userForm.password}
                onChange={e => setUserForm(v => ({ ...v, password: e.target.value }))}
                required
              />
              <select
                style={inputStyle}
                value={userForm.role}
                onChange={e => setUserForm(v => ({ ...v, role: e.target.value }))}
              >
                <option value="member">member</option>
                <option value="admin">admin</option>
              </select>
              <button style={btnPrimary} type="submit" disabled={creatingUser}>
                {creatingUser ? '创建中...' : '创建用户'}
              </button>
            </form>
          </div>

          <div style={{ background: '#fff', borderRadius: 8, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div style={{ fontWeight: 600, fontSize: 15 }}>用户列表</div>
              <button style={{ ...btnPrimary, padding: '6px 14px' }} onClick={loadUsers}>刷新</button>
            </div>
            {usersLoading ? (
              <div style={{ color: '#888' }}>加载中...</div>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                    {['用户名', '邮箱', '角色', '状态', '操作'].map(h => (
                      <th key={h} style={{ textAlign: 'left', padding: '10px 8px', fontSize: 13, color: '#888' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id} style={{ borderBottom: '1px solid #fafafa' }}>
                      <td style={{ padding: '10px 8px', fontSize: 14 }}>{u.username}</td>
                      <td style={{ padding: '10px 8px', fontSize: 13 }}>{u.email}</td>
                      <td style={{ padding: '10px 8px', fontSize: 13 }}>{u.role}</td>
                      <td style={{ padding: '10px 8px', fontSize: 13, color: u.is_active ? '#52c41a' : '#aaa' }}>
                        {u.is_active ? 'active' : 'inactive'}
                      </td>
                      <td style={{ padding: '10px 8px', display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                        <button
                          style={{ ...btnPrimary, padding: '4px 10px', background: '#f0f5ff', color: '#1677ff', border: '1px solid #adc6ff' }}
                          onClick={() => handleEditUser(u)}
                        >
                          编辑
                        </button>
                        <button
                          style={{ ...btnPrimary, padding: '4px 10px', background: '#fffbe6', color: '#ad8b00', border: '1px solid #ffe58f' }}
                          onClick={() => handleResetUserPassword(u)}
                        >
                          重置密码
                        </button>
                        <button
                          style={{
                            ...btnPrimary,
                            padding: '4px 10px',
                            background: u.is_active ? '#fff2f0' : '#f6ffed',
                            color: u.is_active ? '#ff4d4f' : '#389e0d',
                            border: '1px solid ' + (u.is_active ? '#ffccc7' : '#b7eb8f'),
                          }}
                          onClick={() => handleToggleUser(u.id, u.is_active)}
                        >
                          {u.is_active ? '停用' : '启用'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function FormRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
      <label style={{ width: 100, fontSize: 14, color: '#555' }}>{label}</label>
      <div style={{ flex: 1 }}>{children}</div>
    </div>
  );
}

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: '8px 20px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 14,
  fontWeight: active ? 700 : 400, color: active ? '#1677ff' : '#666',
  borderBottom: active ? '2px solid #1677ff' : '2px solid transparent', marginBottom: -2,
});
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14, minWidth: 200 };
const btnPrimary: React.CSSProperties = { padding: '7px 24px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
