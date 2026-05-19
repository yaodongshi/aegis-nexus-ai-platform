import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { learningApi, skillsApi } from '../../lib/api';

type Tab = 'edit' | 'proposals' | 'timeline' | 'export';

const STATUS_COLOR: Record<string, string> = {
  draft: '#faad14',
  applied: '#52c41a',
  synced: '#1677ff',
  rejected: '#ff4d4f',
};

const STATUS_LABEL: Record<string, string> = {
  draft: '待审批',
  applied: '已应用',
  synced: '已同步',
  rejected: '已拒绝',
};

function formatDate(dt: string | null | undefined): string {
  if (!dt) return '-';
  return new Date(dt).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' });
}

const cardStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, boxShadow: '0 1px 4px rgba(0,0,0,.08)', padding: 16 };
const labelStyle: React.CSSProperties = { fontSize: 12, color: '#666', marginTop: 2 };
const inputStyle: React.CSSProperties = { border: '1px solid #d9d9d9', borderRadius: 4, padding: '8px 10px', fontSize: 14, width: '100%', boxSizing: 'border-box' };
const btnPrimary: React.CSSProperties = { border: 'none', borderRadius: 4, background: '#1677ff', color: '#fff', cursor: 'pointer', padding: '8px 14px', fontSize: 13 };
const btnSecondary: React.CSSProperties = { border: '1px solid #d9d9d9', borderRadius: 4, background: '#fff', color: '#444', cursor: 'pointer', padding: '8px 14px', fontSize: 13 };
const pillStyle: React.CSSProperties = { padding: '1px 8px', borderRadius: 10, fontSize: 12 };
const tabBtn: React.CSSProperties = { border: 'none', background: 'transparent', padding: '10px 16px', cursor: 'pointer', fontSize: 13, color: '#666', borderBottom: '2px solid transparent', marginBottom: -2 };
const tabBtnActive: React.CSSProperties = { color: '#1677ff', borderBottom: '2px solid #1677ff', fontWeight: 600 };

export default function SkillDetailPage() {
  const { skillId } = useParams<{ skillId: string }>();
  const [skill, setSkill] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<Tab>('edit');

  const [updates, setUpdates] = useState<any[]>([]);
  const [updatesLoading, setUpdatesLoading] = useState(false);
  const [applying, setApplying] = useState<string | null>(null);

  const [packTarget, setPackTarget] = useState<'claude-code' | 'opencode'>('claude-code');
  const [pack, setPack] = useState<any | null>(null);
  const [copyTip, setCopyTip] = useState('');

  const load = async () => {
    if (!skillId) return;
    setLoading(true);
    setError('');
    try {
      const data = await skillsApi.get(skillId);
      setSkill(data);
    } catch (e: any) {
      setError(e.message || '加载技能详情失败');
    } finally {
      setLoading(false);
    }
  };

  const loadUpdates = async () => {
    if (!skillId) return;
    setUpdatesLoading(true);
    try {
      const resp = await learningApi.skillUpdates({ skill_id: skillId, limit: 50 });
      setUpdates(resp.items || []);
    } catch (e: any) {
      setError(e.message || '加载演化记录失败');
    } finally {
      setUpdatesLoading(false);
    }
  };

  useEffect(() => { load(); }, [skillId]);

  useEffect(() => {
    if (tab === 'proposals' || tab === 'timeline') loadUpdates();
  }, [tab, skillId]);

  const save = async () => {
    if (!skillId || !skill) return;
    setSaving(true);
    setError('');
    try {
      const updated = await skillsApi.update(skillId, {
        name: skill.name,
        description: skill.description,
        category: skill.category,
        system_prompt: skill.system_prompt,
        tags: skill.tags || [],
        status: skill.status,
      });
      setSkill(updated);
    } catch (e: any) {
      setError(e.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const applyUpdate = async (updateId: string) => {
    if (!confirm('确认应用此提案？将会用提案内容覆盖技能的 System Prompt。')) return;
    setApplying(updateId);
    setError('');
    try {
      await learningApi.applySkillUpdate(updateId);
      await load();
      await loadUpdates();
    } catch (e: any) {
      setError(e.message || '应用失败');
    } finally {
      setApplying(null);
    }
  };

  const loadPack = async () => {
    if (!skillId) return;
    setError('');
    try {
      const payload = await skillsApi.exportPack(skillId, packTarget);
      setPack(payload);
    } catch (e: any) {
      setError(e.message || '导出失败');
    }
  };

  const copyAllFiles = async () => {
    if (!pack || !Array.isArray(pack.files) || pack.files.length === 0) return;
    const merged = (pack.files as any[]).map((f) => `### ${f.path}\n${f.content}`).join('\n\n');
    try {
      await navigator.clipboard.writeText(merged);
      setCopyTip('已复制全部文件内容');
    } catch {
      setCopyTip('复制失败，请检查浏览器权限');
    }
  };

  const downloadPackZip = async () => {
    if (!skillId) return;
    try {
      const blob = await skillsApi.exportPackZip(skillId, packTarget);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `skill-pack-${packTarget}-${skillId}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || '下载 zip 失败');
    }
  };

  if (loading) return <div style={{ padding: 24 }}>加载中...</div>;
  if (!skill) return <div style={{ color: '#ff4d4f', padding: 24 }}>技能不存在或已删除</div>;

  const draftUpdates = updates.filter((u) => u.status === 'draft');

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Link to="/skills" style={{ color: '#1677ff', textDecoration: 'none' }}>← 返回技能列表</Link>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>{skill.name}</h1>
        <span style={{ ...pillStyle, background: skill.status === 'active' ? '#f6ffed' : '#fff7e6', color: skill.status === 'active' ? '#52c41a' : '#fa8c16', border: `1px solid ${skill.status === 'active' ? '#b7eb8f' : '#ffd591'}` }}>
          {skill.status}
        </span>
        {draftUpdates.length > 0 && (
          <span style={{ ...pillStyle, background: '#fff7e6', color: '#fa8c16', border: '1px solid #ffd591' }}>
            {draftUpdates.length} 个待审提案
          </span>
        )}
      </div>

      {error && <div style={{ color: '#ff4d4f', marginBottom: 12 }}>{error}</div>}

      <div style={{ display: 'flex', gap: 0, borderBottom: '2px solid #f0f0f0', marginBottom: 20 }}>
        {(['edit', 'proposals', 'timeline', 'export'] as Tab[]).map((t) => {
          const labels: Record<Tab, string> = {
            edit: '📝 编辑',
            proposals: `💡 提案${draftUpdates.length > 0 ? ` (${draftUpdates.length})` : ''}`,
            timeline: '⏱ 演化历史',
            export: '📦 导出',
          };
          return (
            <button key={t} style={{ ...tabBtn, ...(tab === t ? tabBtnActive : {}) }} onClick={() => setTab(t)}>
              {labels[t]}
            </button>
          );
        })}
      </div>

      {tab === 'edit' && (
        <div style={cardStyle}>
          <div style={{ display: 'grid', gap: 8 }}>
            <label style={labelStyle}>名称</label>
            <input style={inputStyle} value={skill.name || ''} onChange={(e) => setSkill((s: any) => ({ ...s, name: e.target.value }))} />

            <label style={labelStyle}>描述</label>
            <input style={inputStyle} value={skill.description || ''} onChange={(e) => setSkill((s: any) => ({ ...s, description: e.target.value }))} />

            <label style={labelStyle}>分类</label>
            <select style={inputStyle} value={skill.category || 'general'} onChange={(e) => setSkill((s: any) => ({ ...s, category: e.target.value }))}>
              {['general', 'coding', 'writing', 'analysis', 'search', 'tool_use'].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>

            <label style={labelStyle}>标签（逗号分隔）</label>
            <input
              style={inputStyle}
              value={(skill.tags || []).join(', ')}
              onChange={(e) => setSkill((s: any) => ({ ...s, tags: e.target.value.split(',').map((x: string) => x.trim()).filter(Boolean) }))}
            />

            <label style={labelStyle}>System Prompt</label>
            <textarea
              style={{ ...inputStyle, minHeight: 200, resize: 'vertical', fontFamily: 'monospace', fontSize: 13 }}
              value={skill.system_prompt || ''}
              onChange={(e) => setSkill((s: any) => ({ ...s, system_prompt: e.target.value }))}
            />
          </div>
          <div style={{ marginTop: 12 }}>
            <button style={btnPrimary} onClick={save} disabled={saving}>{saving ? '保存中...' : '保存修改'}</button>
          </div>
        </div>
      )}

      {tab === 'proposals' && (
        <div>
          {updatesLoading && <div style={{ color: '#999' }}>加载中...</div>}
          {!updatesLoading && draftUpdates.length === 0 && (
            <div style={{ ...cardStyle, textAlign: 'center', color: '#aaa', padding: 40 }}>
              <div style={{ fontSize: 32 }}>✅</div>
              <div style={{ marginTop: 8 }}>暂无待审批的演化提案</div>
              <div style={{ fontSize: 12, marginTop: 4, color: '#ccc' }}>当 AI 学习循环检测到改进机会时，会在这里生成提案</div>
            </div>
          )}
          <div style={{ display: 'grid', gap: 12 }}>
            {draftUpdates.map((u) => (
              <div key={u.id} style={{ ...cardStyle, borderLeft: '3px solid #faad14' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <strong>{u.proposed_skill_name || skill.name}</strong>
                    <span style={{ ...pillStyle, background: '#fffbe6', color: STATUS_COLOR[u.status], border: `1px solid ${STATUS_COLOR[u.status]}` }}>
                      {STATUS_LABEL[u.status] || u.status}
                    </span>
                  </div>
                  <span style={{ fontSize: 12, color: '#999' }}>{formatDate(u.created_at)}</span>
                </div>
                <div style={{ fontSize: 13, color: '#666', marginBottom: 8, lineHeight: 1.6 }}>
                  <strong>改进理由：</strong>{u.rationale}
                </div>
                {u.proposed_system_prompt && (
                  <details style={{ marginBottom: 8 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 12, color: '#1677ff', userSelect: 'none' }}>查看建议的 System Prompt</summary>
                    <pre style={{ marginTop: 8, background: '#fafafa', padding: 10, borderRadius: 4, fontSize: 12, whiteSpace: 'pre-wrap', border: '1px solid #f0f0f0' }}>
                      {u.proposed_system_prompt}
                    </pre>
                  </details>
                )}
                {u.git_commit_hash && (
                  <div style={{ fontSize: 12, color: '#999', marginBottom: 8 }}>
                    Git commit: <code style={{ background: '#f5f5f5', padding: '1px 4px', borderRadius: 3 }}>{u.git_commit_hash.slice(0, 8)}</code>
                  </div>
                )}
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <button style={btnPrimary} onClick={() => applyUpdate(u.id)} disabled={applying === u.id}>
                    {applying === u.id ? '应用中...' : '✅ 应用提案'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'timeline' && (
        <div>
          {updatesLoading && <div style={{ color: '#999' }}>加载中...</div>}
          {!updatesLoading && updates.length === 0 && (
            <div style={{ ...cardStyle, textAlign: 'center', color: '#aaa', padding: 40 }}>
              <div style={{ fontSize: 32 }}>📜</div>
              <div style={{ marginTop: 8 }}>暂无演化记录</div>
              <div style={{ fontSize: 12, marginTop: 4, color: '#ccc' }}>技能的所有变更历史将在这里展示</div>
            </div>
          )}
          {updates.length > 0 && (
            <div style={{ position: 'relative', paddingLeft: 32 }}>
              <div style={{ position: 'absolute', left: 12, top: 0, bottom: 0, width: 2, background: '#f0f0f0' }} />
              {updates.map((u, idx) => (
                <div key={u.id} style={{ position: 'relative', marginBottom: 20 }}>
                  <div style={{
                    position: 'absolute', left: -26, top: 14, width: 12, height: 12,
                    borderRadius: '50%', background: STATUS_COLOR[u.status] || '#d9d9d9',
                    border: '2px solid #fff', boxShadow: '0 0 0 2px ' + (STATUS_COLOR[u.status] || '#d9d9d9'),
                  }} />
                  <div style={{ ...cardStyle, padding: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, alignItems: 'center' }}>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>
                          {idx === 0 ? '🔥 最新' : `#${updates.length - idx}`} — {u.proposed_skill_name || skill.name}
                        </span>
                        <span style={{ ...pillStyle, background: '#fff', color: STATUS_COLOR[u.status], border: `1px solid ${STATUS_COLOR[u.status]}` }}>
                          {STATUS_LABEL[u.status] || u.status}
                        </span>
                      </div>
                      <span style={{ fontSize: 11, color: '#bbb' }}>{formatDate(u.created_at)}</span>
                    </div>
                    <div style={{ fontSize: 12, color: '#666', lineHeight: 1.5 }}>{u.rationale}</div>
                    {u.proposed_system_prompt && (
                      <details style={{ marginTop: 6 }}>
                        <summary style={{ cursor: 'pointer', fontSize: 11, color: '#1677ff', userSelect: 'none' }}>查看 Prompt 变更</summary>
                        <pre style={{ marginTop: 6, background: '#fafafa', padding: 8, borderRadius: 4, fontSize: 11, whiteSpace: 'pre-wrap', border: '1px solid #f0f0f0' }}>
                          {u.proposed_system_prompt}
                        </pre>
                      </details>
                    )}
                    {u.git_commit_hash && (
                      <div style={{ marginTop: 6, fontSize: 11, color: '#aaa' }}>
                        🔗 Git: <code style={{ background: '#f5f5f5', padding: '1px 3px', borderRadius: 2 }}>{u.git_commit_hash.slice(0, 8)}</code>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {tab === 'export' && (
        <div style={cardStyle}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Skill Pack 导出（兼容文件结构）</div>
          <div style={{ fontSize: 13, color: '#888', marginBottom: 12 }}>
            导出为 Claude Code 或 OpenCode 兼容的文件结构，可直接用于 AI 工具配置。
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
            <select style={inputStyle} value={packTarget} onChange={(e) => setPackTarget(e.target.value as 'claude-code' | 'opencode')}>
              <option value="claude-code">Claude Code</option>
              <option value="opencode">OpenCode</option>
            </select>
            <button style={btnPrimary} onClick={loadPack}>生成文件结构</button>
            <button style={btnSecondary} onClick={downloadPackZip}>下载 ZIP</button>
            <button style={btnSecondary} onClick={copyAllFiles}>复制全部</button>
          </div>
          {pack && (
            <div>
              <div style={{ fontSize: 12, color: '#999', marginBottom: 6 }}>协议版本：{pack.protocol_version || '1.0'}</div>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>{pack.install_hint}</div>
              {copyTip && <div style={{ fontSize: 12, color: '#52c41a', marginBottom: 8 }}>{copyTip}</div>}
              <div style={{ display: 'grid', gap: 10 }}>
                {(pack.files || []).map((f: any) => (
                  <div key={f.path} style={{ border: '1px solid #f0f0f0', borderRadius: 6, padding: 10, background: '#fafafa' }}>
                    <div style={{ fontFamily: 'monospace', fontSize: 12, marginBottom: 6 }}>{f.path}</div>
                    <div style={{ fontSize: 12, color: '#888', marginBottom: 6 }}>{f.description}</div>
                    <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.5 }}>{f.content}</pre>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
