import React, { useEffect, useRef, useState } from 'react';
import { feedbacksApi, learningApi, pluginsApi, sessionsApi } from '../../lib/api';

type Tab = 'obsLogs' | 'auditLogs' | 'sessions' | 'hookEvents';
type FailedBulkRepo = { repo: any; reason: 'timeout' | 'api' };
type BulkRunSummary = {
  startedAt: string;
  endedAt: string;
  total: number;
  success: number;
  failed: number;
  timeout: number;
  api: number;
  canceled: boolean;
  failedRepos: string[];
};

const BULK_PULL_CONCURRENCY = 3;
const BULK_PULL_TIMEOUT_MS = 60_000;

export default function ObservePage() {
  const bulkCancelRef = useRef(false);
  const [tab, setTab] = useState<Tab>('obsLogs');
  const [obsLogs, setObsLogs] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [hookEvents, setHookEvents] = useState<any[]>([]);
  const [gitRepos, setGitRepos] = useState<any[]>([]);
  const [hookLoading, setHookLoading] = useState(false);
  const [pullingRepoId, setPullingRepoId] = useState('');
  const [bulkPulling, setBulkPulling] = useState(false);
  const [failedBulkRepos, setFailedBulkRepos] = useState<FailedBulkRepo[]>([]);
  const [lastBulkSummary, setLastBulkSummary] = useState<BulkRunSummary | null>(null);
  const [hookActionTip, setHookActionTip] = useState('');
  const [repoFilter, setRepoFilter] = useState('all');
  const [keywordFilter, setKeywordFilter] = useState('');
  const [onlyPullable, setOnlyPullable] = useState(false);
  const [failedReasonFilter, setFailedReasonFilter] = useState<'all' | 'timeout' | 'api'>('all');
  const [timeRange, setTimeRange] = useState<'all' | '24h' | '7d' | '30d'>('7d');
  const [sortOrder, setSortOrder] = useState<'desc' | 'asc'>('desc');
  const [selectedHookEvent, setSelectedHookEvent] = useState<any | null>(null);
  const [copyTip, setCopyTip] = useState('');
  const [error, setError] = useState('');

  const loadHookEvents = async () => {
    setHookLoading(true);
    try {
      const resp = await learningApi.hookEvents(100, 0);
      setHookEvents(resp.items || []);
    } catch (e: any) {
      setError(e.message || '加载 Hook 事件失败');
    } finally {
      setHookLoading(false);
    }
  };

  const loadGitRepos = async () => {
    try {
      const resp = await learningApi.gitRepos(100, 0);
      setGitRepos(resp.items || []);
    } catch (e: any) {
      setError(e.message || '加载 Git 仓库失败');
    }
  };

  const handlePullRepo = async (repoId: string) => {
    setPullingRepoId(repoId);
    try {
      await learningApi.pullRepo(repoId);
      await loadHookEvents();
      await loadGitRepos();
    } catch (e: any) {
      setError(e.message || '仓库拉取失败');
    } finally {
      setPullingRepoId('');
    }
  };

  const handleBulkPull = async (repos: any[]) => {
    if (!repos.length) return;
    if (!window.confirm(`确认批量 Pull ${repos.length} 个仓库并执行 Ingest？`)) return;
    const startedAt = new Date().toISOString();

    bulkCancelRef.current = false;
    setBulkPulling(true);
    setError('');
    setHookActionTip('');

    const pullWithTimeout = async (repoId: string) => {
      await Promise.race([
        learningApi.pullRepo(repoId),
        new Promise<never>((_, reject) => {
          setTimeout(() => reject(new Error('timeout')), BULK_PULL_TIMEOUT_MS);
        }),
      ]);
    };

    let success = 0;
    const failed: FailedBulkRepo[] = [];
    let started = 0;
    const queue = [...repos];
    const workers = Array.from({ length: Math.min(BULK_PULL_CONCURRENCY, repos.length) }, () => (
      async () => {
        while (queue.length > 0 && !bulkCancelRef.current) {
          const repo = queue.shift();
          if (!repo) return;

          started += 1;
          setPullingRepoId(repo.id);
          setHookActionTip(`批量执行中 ${started}/${repos.length}：${repo.name}`);
          try {
            await pullWithTimeout(repo.id);
            success += 1;
            } catch (e: any) {
              failed.push({
                repo,
                reason: e?.message === 'timeout' ? 'timeout' : 'api',
              });
          }
        }
      }
    ));

    await Promise.all(workers.map((worker) => worker()));

    const canceled = bulkCancelRef.current;
    bulkCancelRef.current = false;
    setPullingRepoId('');
    setBulkPulling(false);
    setFailedBulkRepos(failed);

    await loadHookEvents();
    await loadGitRepos();

    const timeoutCount = failed.filter((item) => item.reason === 'timeout').length;
    const apiCount = failed.filter((item) => item.reason === 'api').length;
    setLastBulkSummary({
      startedAt,
      endedAt: new Date().toISOString(),
      total: repos.length,
      success,
      failed: failed.length,
      timeout: timeoutCount,
      api: apiCount,
      canceled,
      failedRepos: failed.map((item) => item.repo?.name || item.repo?.id || 'unknown'),
    });

    if (!failed.length) {
      if (canceled) {
        setHookActionTip(`批量 Pull 已取消：已完成 ${success}/${repos.length}`);
        return;
      }
      setHookActionTip(`批量 Pull 完成：${success}/${repos.length} 成功（并发 ${BULK_PULL_CONCURRENCY}）`);
      return;
    }

    if (canceled) {
      setHookActionTip(`批量 Pull 已取消：成功 ${success}/${repos.length}，失败 ${failed.length}`);
      return;
    }
    setHookActionTip(
      `批量 Pull 完成：${success}/${repos.length} 成功，失败 ${failed.length}（超时 ${timeoutCount}，接口 ${apiCount}）`
    );
  };

  const cancelBulkPull = () => {
    bulkCancelRef.current = true;
    setHookActionTip('正在取消批量任务，等待进行中的请求完成...');
  };

  const exportFailedCsv = () => {
    if (!filteredFailedBulkRepos.length) return;
    const escapeCsv = (value: string) => `"${String(value).replace(/"/g, '""')}"`;
    const header = ['repo_id', 'repo_name', 'repo_path', 'reason'];
    const rows = filteredFailedBulkRepos.map((item) => [
      item.repo?.id || '',
      item.repo?.name || '',
      item.repo?.path || '',
      item.reason,
    ]);
    const csv = [header, ...rows].map((row) => row.map((cell) => escapeCsv(String(cell))).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const ts = new Date().toISOString().replace(/[:.]/g, '-');
    a.href = url;
    a.download = `failed-hook-pull-${ts}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setHookActionTip(`已导出失败清单 CSV（${filteredFailedBulkRepos.length} 条）`);
  };

  const copyLastBulkSummary = async () => {
    if (!lastBulkSummary) return;
    const lines = [
      `started_at: ${lastBulkSummary.startedAt}`,
      `ended_at: ${lastBulkSummary.endedAt}`,
      `status: ${lastBulkSummary.canceled ? 'canceled' : 'done'}`,
      `total: ${lastBulkSummary.total}`,
      `success: ${lastBulkSummary.success}`,
      `failed: ${lastBulkSummary.failed}`,
      `timeout: ${lastBulkSummary.timeout}`,
      `api: ${lastBulkSummary.api}`,
      `failed_repos: ${lastBulkSummary.failedRepos.join(', ') || '-'}`,
    ];
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      setHookActionTip('已复制最近批次摘要');
    } catch {
      setHookActionTip('复制批次摘要失败，请检查浏览器权限');
    }
  };

  useEffect(() => {
    pluginsApi.obsLogs().then(setObsLogs).catch(e => setError(e.message));
    feedbacksApi.auditLogs().then(setAuditLogs).catch(e => setError(e.message));
    sessionsApi.list().then(r => setSessions(r.items)).catch(e => setError(e.message));
    loadHookEvents();
    loadGitRepos();
  }, []);

  const findRepoByEvent = (event: any) => {
    if (event?.repo_id) {
      const byId = gitRepos.find((repo) => repo.id === event.repo_id);
      if (byId) return byId;
    }
    const normalizedRepository = String(event?.repository || '').trim();
    if (!normalizedRepository) return null;
    return gitRepos.find((repo) => {
      const name = String(repo?.name || '').trim();
      const path = String(repo?.path || '').trim();
      return name === normalizedRepository || path.endsWith(`/${normalizedRepository}`);
    }) || null;
  };

  const copyText = async (text: string, successTip: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyTip(successTip);
      setTimeout(() => setCopyTip(''), 1800);
    } catch {
      setCopyTip('复制失败，请检查浏览器权限');
      setTimeout(() => setCopyTip(''), 1800);
    }
  };

  const hookRepos = Array.from(new Set(hookEvents.map((e) => e.repository).filter(Boolean)));
  const nowMs = Date.now();
  const minTimestamp =
    timeRange === '24h' ? nowMs - 24 * 60 * 60 * 1000
      : timeRange === '7d' ? nowMs - 7 * 24 * 60 * 60 * 1000
      : timeRange === '30d' ? nowMs - 30 * 24 * 60 * 60 * 1000
      : null;

  const filteredHookEvents = hookEvents.filter((e) => {
    if (repoFilter !== 'all' && e.repository !== repoFilter) return false;

    if (onlyPullable && !findRepoByEvent(e)) return false;

    if (minTimestamp != null) {
      const eventTs = new Date(e.created_at || e.event_time || 0).getTime();
      if (!Number.isFinite(eventTs) || eventTs < minTimestamp) return false;
    }

    if (!keywordFilter.trim()) return true;
    const kw = keywordFilter.trim().toLowerCase();
    return [
      e.repository,
      e.branch,
      e.commit_sha,
      e.author,
      ...(e.linked_skill_ids || []),
      ...(e.changed_files || []),
    ]
      .filter(Boolean)
      .some((field) => String(field).toLowerCase().includes(kw));
  }).sort((a, b) => {
    const tsA = new Date(a.created_at || a.event_time || 0).getTime();
    const tsB = new Date(b.created_at || b.event_time || 0).getTime();
    return sortOrder === 'desc' ? tsB - tsA : tsA - tsB;
  });

  const pullableRepoMap = new Map<string, any>();
  filteredHookEvents.forEach((e) => {
    const repo = findRepoByEvent(e);
    if (repo?.id && !pullableRepoMap.has(repo.id)) pullableRepoMap.set(repo.id, repo);
  });
  const pullableRepos = Array.from(pullableRepoMap.values());
  const pullableCount = filteredHookEvents.filter((e) => Boolean(findRepoByEvent(e))).length;
  const filteredFailedBulkRepos = failedBulkRepos.filter((item) => failedReasonFilter === 'all' || item.reason === failedReasonFilter);
  const failedTimeoutRepos = filteredFailedBulkRepos.filter((item) => item.reason === 'timeout').map((item) => item.repo);
  const failedTimeoutCount = failedBulkRepos.filter((item) => item.reason === 'timeout').length;
  const failedApiCount = failedBulkRepos.filter((item) => item.reason === 'api').length;

  return (
    <div>
      <h1 style={{ marginBottom: 20 }}>观测中心</h1>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid #f0f0f0' }}>
        {([
          ['obsLogs',   '插件观测日志'],
          ['auditLogs', '审计日志'],
          ['sessions',  'AI 会话'],
          ['hookEvents', 'Git Hooks 事件'],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{ padding: '8px 20px', border: 'none', background: 'transparent', cursor: 'pointer', fontSize: 14, fontWeight: tab === key ? 700 : 400, color: tab === key ? '#1677ff' : '#666', borderBottom: tab === key ? '2px solid #1677ff' : '2px solid transparent', marginBottom: -2 }}
          >{label}</button>
        ))}
      </div>

      {/* 插件观测日志 / 审计日志 */}
      {(tab === 'obsLogs' || tab === 'auditLogs') && (() => {
        const logs = tab === 'obsLogs' ? obsLogs : auditLogs;
        return (
          <>
            <table style={{ width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  {['操作', '资源类型', '资源 ID', '详情', '时间'].map(h => <th key={h} style={thStyle}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                    <td style={tdStyle}><span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: '#e6f4ff', color: '#1677ff' }}>{log.action}</span></td>
                    <td style={tdStyle}>{log.resource_type}</td>
                    <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12, color: '#888' }}>{log.resource_id}</td>
                    <td style={tdStyle}>{log.detail}</td>
                    <td style={{ ...tdStyle, color: '#aaa', fontSize: 12 }}>{new Date(log.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {logs.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无日志</div>}
          </>
        );
      })()}

      {/* AI 会话 Tab */}
      {tab === 'sessions' && (
        <>
          <table style={{ width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                {['用户', '项目', '标题', '状态', '摘要', '创建时间'].map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {sessions.map(s => (
                <tr key={s.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{s.user_id}</td>
                  <td style={tdStyle}>{s.project_id || <span style={{ color: '#ccc' }}>—</span>}</td>
                  <td style={tdStyle}>{s.title || <span style={{ color: '#ccc' }}>（无标题）</span>}</td>
                  <td style={tdStyle}>
                    <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: s.status === 'active' ? '#f6ffed' : '#f5f5f5', color: s.status === 'active' ? '#52c41a' : '#aaa' }}>
                      {s.status}
                    </span>
                  </td>
                  <td style={{ ...tdStyle, fontSize: 12, color: '#888', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.summary || '—'}</td>
                  <td style={{ ...tdStyle, color: '#aaa', fontSize: 12 }}>{new Date(s.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {sessions.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无 AI 会话记录</div>}
        </>
      )}

      {/* Git Hooks 事件 */}
      {tab === 'hookEvents' && (
        <>
          <div style={{ background: '#fff', borderRadius: 8, padding: 12, boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: 12, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button
              style={{ padding: '7px 14px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}
              onClick={loadHookEvents}
              disabled={hookLoading || bulkPulling}
            >
              {hookLoading ? '刷新中...' : '刷新事件'}
            </button>

            <button
              style={{ padding: '7px 14px', background: pullableRepos.length > 0 ? '#13c2c2' : '#f5f5f5', color: pullableRepos.length > 0 ? '#fff' : '#aaa', border: 'none', borderRadius: 4, cursor: pullableRepos.length > 0 ? 'pointer' : 'not-allowed', fontSize: 13 }}
              onClick={() => handleBulkPull(pullableRepos)}
              disabled={bulkPulling || hookLoading || pullableRepos.length === 0}
              title={pullableRepos.length > 0 ? `批量处理 ${pullableRepos.length} 个仓库` : '当前筛选无可执行仓库'}
            >
              {bulkPulling ? '批量执行中...' : `批量 Pull（${pullableRepos.length} 仓库）`}
            </button>

            <button
              style={{ padding: '7px 14px', background: filteredFailedBulkRepos.length > 0 ? '#fa8c16' : '#f5f5f5', color: filteredFailedBulkRepos.length > 0 ? '#fff' : '#aaa', border: 'none', borderRadius: 4, cursor: filteredFailedBulkRepos.length > 0 ? 'pointer' : 'not-allowed', fontSize: 13 }}
              onClick={() => handleBulkPull(filteredFailedBulkRepos.map((item) => item.repo))}
              disabled={bulkPulling || hookLoading || filteredFailedBulkRepos.length === 0}
              title={filteredFailedBulkRepos.length > 0 ? `重试失败仓库 ${filteredFailedBulkRepos.length} 个` : '暂无失败仓库'}
            >
              {bulkPulling ? '重试中...' : `重试失败（${filteredFailedBulkRepos.length}）`}
            </button>

            <button
              style={{ padding: '7px 14px', background: failedTimeoutRepos.length > 0 ? '#722ed1' : '#f5f5f5', color: failedTimeoutRepos.length > 0 ? '#fff' : '#aaa', border: 'none', borderRadius: 4, cursor: failedTimeoutRepos.length > 0 ? 'pointer' : 'not-allowed', fontSize: 13 }}
              onClick={() => handleBulkPull(failedTimeoutRepos)}
              disabled={bulkPulling || hookLoading || failedTimeoutRepos.length === 0}
              title={failedTimeoutRepos.length > 0 ? `仅重试超时仓库 ${failedTimeoutRepos.length} 个` : '暂无超时仓库'}
            >
              {bulkPulling ? '重试中...' : `仅重试超时（${failedTimeoutRepos.length}）`}
            </button>

            <button
              style={{ padding: '7px 14px', background: filteredFailedBulkRepos.length > 0 ? '#595959' : '#f5f5f5', color: filteredFailedBulkRepos.length > 0 ? '#fff' : '#aaa', border: 'none', borderRadius: 4, cursor: filteredFailedBulkRepos.length > 0 ? 'pointer' : 'not-allowed', fontSize: 13 }}
              onClick={exportFailedCsv}
              disabled={bulkPulling || filteredFailedBulkRepos.length === 0}
              title={filteredFailedBulkRepos.length > 0 ? '导出失败仓库清单 CSV' : '暂无失败清单'}
            >
              导出失败 CSV
            </button>

            <button
              style={{ padding: '7px 14px', background: lastBulkSummary ? '#52c41a' : '#f5f5f5', color: lastBulkSummary ? '#fff' : '#aaa', border: 'none', borderRadius: 4, cursor: lastBulkSummary ? 'pointer' : 'not-allowed', fontSize: 13 }}
              onClick={copyLastBulkSummary}
              disabled={bulkPulling || !lastBulkSummary}
              title={lastBulkSummary ? '复制最近批次执行摘要' : '暂无批次摘要'}
            >
              复制批次摘要
            </button>

            {bulkPulling && (
              <button
                style={{ padding: '7px 14px', background: '#fff1f0', color: '#cf1322', border: '1px solid #ffccc7', borderRadius: 4, cursor: 'pointer', fontSize: 13 }}
                onClick={cancelBulkPull}
              >
                取消当前批次
              </button>
            )}

            <select
              value={repoFilter}
              onChange={(e) => setRepoFilter(e.target.value)}
              style={{ padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 13, minWidth: 180 }}
            >
              <option value="all">全部仓库</option>
              {hookRepos.map((repo) => (
                <option key={repo} value={repo}>{repo}</option>
              ))}
            </select>

            <select
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value as 'all' | '24h' | '7d' | '30d')}
              style={{ padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 13, minWidth: 120 }}
            >
              <option value="all">全部时间</option>
              <option value="24h">近 24 小时</option>
              <option value="7d">近 7 天</option>
              <option value="30d">近 30 天</option>
            </select>

            <select
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value as 'desc' | 'asc')}
              style={{ padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 13, minWidth: 120 }}
            >
              <option value="desc">最新优先</option>
              <option value="asc">最早优先</option>
            </select>

            <select
              value={failedReasonFilter}
              onChange={(e) => setFailedReasonFilter(e.target.value as 'all' | 'timeout' | 'api')}
              style={{ padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 13, minWidth: 130 }}
              disabled={bulkPulling}
            >
              <option value="all">失败原因：全部</option>
              <option value="timeout">失败原因：超时</option>
              <option value="api">失败原因：接口失败</option>
            </select>

            <input
              placeholder="关键词：commit / 作者 / 技能 / 文件"
              value={keywordFilter}
              onChange={(e) => setKeywordFilter(e.target.value)}
              style={{ padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 13, minWidth: 260 }}
            />

            <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#555' }}>
              <input
                type="checkbox"
                checked={onlyPullable}
                onChange={(e) => setOnlyPullable(e.target.checked)}
                disabled={bulkPulling}
              />
              仅显示可 Pull
            </label>

            <span style={{ fontSize: 12, color: '#888' }}>共 {filteredHookEvents.length} 条（可 Pull {pullableCount} 条，{pullableRepos.length} 仓库）</span>
            {failedBulkRepos.length > 0 && (
              <span style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
                <span style={{ fontSize: 11, color: '#722ed1', background: '#f9f0ff', border: '1px solid #d3adf7', borderRadius: 10, padding: '1px 8px' }}>超时 {failedTimeoutCount}</span>
                <span style={{ fontSize: 11, color: '#d46b08', background: '#fff7e6', border: '1px solid #ffd591', borderRadius: 10, padding: '1px 8px' }}>接口失败 {failedApiCount}</span>
              </span>
            )}
            {hookActionTip && <span style={{ fontSize: 12, color: '#13a8a8' }}>{hookActionTip}</span>}
          </div>

          {lastBulkSummary && (
            <div style={{ background: '#fff', borderRadius: 8, padding: '10px 12px', boxShadow: '0 1px 4px rgba(0,0,0,.08)', marginBottom: 12, display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12, color: '#555' }}>
              <span>最近批次：{lastBulkSummary.canceled ? '已取消' : '已完成'}</span>
              <span>总计 {lastBulkSummary.total}</span>
              <span style={{ color: '#389e0d' }}>成功 {lastBulkSummary.success}</span>
              <span style={{ color: '#cf1322' }}>失败 {lastBulkSummary.failed}</span>
              <span style={{ color: '#722ed1' }}>超时 {lastBulkSummary.timeout}</span>
              <span style={{ color: '#d46b08' }}>接口失败 {lastBulkSummary.api}</span>
              <span style={{ color: '#999' }}>结束时间 {new Date(lastBulkSummary.endedAt).toLocaleString()}</span>
            </div>
          )}

          <table style={{ width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                {['仓库', '分支', '提交', '变更文件', '关联技能', '作者', '时间', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
                {filteredHookEvents.map((e) => {
                  const matchedRepo = findRepoByEvent(e);
                  const canPull = Boolean(matchedRepo?.id);
                  return (
                  <tr key={e.hook_event_id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={tdStyle}>{e.repository || '-'}</td>
                  <td style={tdStyle}>{e.branch || '-'}</td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{(e.commit_sha || '').slice(0, 10) || '-'}</td>
                  <td style={{ ...tdStyle, fontSize: 12, color: '#666' }}>{(e.changed_files || []).length}</td>
                  <td style={tdStyle}>{(e.linked_skill_ids || []).join(', ') || '-'}</td>
                  <td style={tdStyle}>{e.author || '-'}</td>
                  <td style={{ ...tdStyle, color: '#aaa', fontSize: 12 }}>{e.created_at ? new Date(e.created_at).toLocaleString() : '-'}</td>
                  <td style={tdStyle}>
                      <button
                        style={{ padding: '5px 10px', border: 'none', background: canPull ? '#1677ff' : '#f5f5f5', color: canPull ? '#fff' : '#aaa', borderRadius: 4, cursor: canPull ? 'pointer' : 'not-allowed', fontSize: 12, marginRight: 8 }}
                        onClick={() => canPull && handlePullRepo(matchedRepo.id)}
                        disabled={!canPull || pullingRepoId === matchedRepo.id || bulkPulling}
                        title={canPull ? `拉取仓库 ${matchedRepo.name}` : '未匹配到仓库配置，无法直接拉取'}
                      >
                        {pullingRepoId === matchedRepo?.id ? '拉取中...' : 'Pull & Ingest'}
                      </button>
                    <button
                      style={{ padding: '5px 10px', border: '1px solid #d9d9d9', background: '#fff', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}
                      onClick={() => setSelectedHookEvent(e)}
                    >
                      查看详情
                    </button>
                  </td>
                </tr>
                );})}
            </tbody>
          </table>

          {!hookLoading && filteredHookEvents.length === 0 && (
            <div style={{ color: '#aaa', marginTop: 20 }}>暂无匹配的 Hook 事件</div>
          )}

          {selectedHookEvent && (
            <div style={overlayStyle} onClick={() => setSelectedHookEvent(null)}>
              <div style={drawerStyle} onClick={(evt) => evt.stopPropagation()}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <strong>Hook 事件详情</strong>
                  <button
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: '#999', fontSize: 14 }}
                    onClick={() => setSelectedHookEvent(null)}
                  >
                    关闭
                  </button>
                </div>
                {copyTip && (
                  <div style={{ marginBottom: 10, fontSize: 12, color: '#52c41a' }}>{copyTip}</div>
                )}

                <div style={detailCardStyle}>
                  <div style={detailTitleStyle}>基本信息</div>
                  <div style={detailRowStyle}><span style={detailLabelStyle}>仓库</span>{selectedHookEvent.repository || '-'}</div>
                  <div style={detailRowStyle}><span style={detailLabelStyle}>分支</span>{selectedHookEvent.branch || '-'}</div>
                  <div style={detailRowStyle}><span style={detailLabelStyle}>提交</span>
                    <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{selectedHookEvent.commit_sha || '-'}</span>
                  </div>
                  <div style={detailRowStyle}><span style={detailLabelStyle}>作者</span>{selectedHookEvent.author || '-'}</div>
                  <div style={detailRowStyle}><span style={detailLabelStyle}>时间</span>{selectedHookEvent.created_at ? new Date(selectedHookEvent.created_at).toLocaleString() : '-'}</div>

                  <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      style={actionBtnStyle}
                      onClick={() => copyText(String(selectedHookEvent.commit_sha || ''), '已复制 commit SHA')}
                    >
                      复制 Commit
                    </button>
                    <button
                      style={actionBtnStyle}
                      onClick={() => copyText(
                        [
                          `repo: ${selectedHookEvent.repository || '-'}`,
                          `branch: ${selectedHookEvent.branch || '-'}`,
                          `commit: ${selectedHookEvent.commit_sha || '-'}`,
                          `author: ${selectedHookEvent.author || '-'}`,
                          `time: ${selectedHookEvent.created_at || '-'}`,
                        ].join('\n'),
                        '已复制事件摘要',
                      )}
                    >
                      复制摘要
                    </button>
                  </div>
                </div>

                <div style={detailCardStyle}>
                  <div style={detailTitleStyle}>变更文件（{(selectedHookEvent.changed_files || []).length}）</div>
                  {(selectedHookEvent.changed_files || []).length > 0 ? (
                    <>
                      <ul style={{ margin: 0, paddingLeft: 18, maxHeight: 150, overflow: 'auto' }}>
                        {(selectedHookEvent.changed_files || []).map((file: string) => (
                          <li key={file} style={{ fontSize: 12, lineHeight: 1.7, fontFamily: 'monospace' }}>{file}</li>
                        ))}
                      </ul>
                      <button
                        style={{ ...actionBtnStyle, marginTop: 8 }}
                        onClick={() => copyText((selectedHookEvent.changed_files || []).join('\n'), '已复制文件列表')}
                      >
                        复制文件列表
                      </button>
                    </>
                  ) : (
                    <div style={{ fontSize: 12, color: '#999' }}>无变更文件</div>
                  )}
                </div>

                <div style={detailCardStyle}>
                  <div style={detailTitleStyle}>关联技能（{(selectedHookEvent.linked_skill_ids || []).length}）</div>
                  {(selectedHookEvent.linked_skill_ids || []).length > 0 ? (
                    <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                      {(selectedHookEvent.linked_skill_ids || []).map((skillId: string) => (
                        <span key={skillId} style={skillTagStyle}>{skillId}</span>
                      ))}
                    </div>
                  ) : (
                    <div style={{ fontSize: 12, color: '#999' }}>未关联技能</div>
                  )}
                </div>

                <details style={detailCardStyle}>
                  <summary style={{ cursor: 'pointer', fontSize: 13, color: '#1677ff' }}>查看原始 JSON</summary>
                  <div style={{ marginTop: 8, display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      style={actionBtnStyle}
                      onClick={() => copyText(JSON.stringify(selectedHookEvent, null, 2), '已复制原始 JSON')}
                    >
                      复制 JSON
                    </button>
                  </div>
                  <pre style={{ margin: 0, marginTop: 8, background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 6, padding: 10, whiteSpace: 'pre-wrap', fontSize: 12, lineHeight: 1.6, maxHeight: 260, overflow: 'auto' }}>
                    {JSON.stringify(selectedHookEvent, null, 2)}
                  </pre>
                </details>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,.28)',
  display: 'flex',
  justifyContent: 'flex-end',
  zIndex: 999,
};
const drawerStyle: React.CSSProperties = {
  width: 'min(680px, 92vw)',
  height: '100vh',
  background: '#fff',
  boxShadow: '-4px 0 16px rgba(0,0,0,.12)',
  padding: 16,
  boxSizing: 'border-box',
  overflow: 'auto',
};
const detailCardStyle: React.CSSProperties = {
  marginBottom: 10,
  background: '#fff',
  border: '1px solid #f0f0f0',
  borderRadius: 8,
  padding: 10,
};
const detailTitleStyle: React.CSSProperties = {
  fontWeight: 600,
  fontSize: 13,
  marginBottom: 8,
};
const detailRowStyle: React.CSSProperties = {
  fontSize: 12,
  lineHeight: 1.8,
  display: 'flex',
  gap: 8,
};
const detailLabelStyle: React.CSSProperties = {
  width: 52,
  color: '#888',
  flexShrink: 0,
};
const actionBtnStyle: React.CSSProperties = {
  padding: '5px 10px',
  border: '1px solid #d9d9d9',
  background: '#fff',
  borderRadius: 4,
  cursor: 'pointer',
  fontSize: 12,
};
const skillTagStyle: React.CSSProperties = {
  fontSize: 12,
  padding: '2px 8px',
  borderRadius: 10,
  background: '#f0f5ff',
  color: '#1677ff',
};
