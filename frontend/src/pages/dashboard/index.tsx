import React, { useEffect, useState } from 'react';
import { keysApi, learningApi, modelsApi, platformApi, providersApi, skillsApi } from '../../lib/api';

interface StatCardProps {
  label: string;
  value: number;
  color: string;
}

function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: '24px 28px', boxShadow: '0 1px 4px rgba(0,0,0,.08)', flex: 1, minWidth: 160 }}>
      <div style={{ fontSize: 13, color: '#888', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

function ServiceBadge({ name, reachable, detail }: { name: string; reachable: boolean; detail: string }) {
  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: '16px 20px', boxShadow: '0 1px 4px rgba(0,0,0,.08)', display: 'flex', alignItems: 'center', gap: 12, minWidth: 200 }}>
      <span style={{ fontSize: 20 }}>{reachable ? '🟢' : '🔴'}</span>
      <div>
        <div style={{ fontSize: 13, fontWeight: 600 }}>{name}</div>
        <div style={{ fontSize: 11, color: '#aaa', marginTop: 2 }}>{detail}</div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [counts, setCounts] = useState({ providers: 0, models: 0, keys: 0, skills: 0 });
  const [governanceStats, setGovernanceStats] = useState({ pendingProposals: 0, evolutionsThisWeek: 0 });
  const [overview, setOverview] = useState<any>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<any>(null);
  const blockingFailed: string[] = runtimeHealth?.blocking_failed ?? [];
  const hasBlockingFailure = blockingFailed.length > 0;

  const getWeekStart = () => {
    const now = new Date();
    const day = now.getDay();
    const daysSinceMonday = (day + 6) % 7;
    const weekStart = new Date(now);
    weekStart.setDate(now.getDate() - daysSinceMonday);
    weekStart.setHours(0, 0, 0, 0);
    return weekStart;
  };

  useEffect(() => {
    Promise.all([
      providersApi.list().then(r => r.total || 0).catch(() => 0),
      modelsApi.list(undefined, undefined, 1, 0).then(r => r.total || 0).catch(() => 0),
      keysApi.list().then(r => r.total || 0).catch(() => 0),
      skillsApi.list().then(r => r.total || 0).catch(() => 0),
    ]).then(([providers, models, keys, skills]) => {
      setCounts({ providers, models, keys, skills });
    });

    Promise.all([
      learningApi.skillUpdates({ status: 'draft', limit: 1, offset: 0 }).catch(() => ({ total: 0 })),
      learningApi.skillUpdates({ limit: 200, offset: 0 }).catch(() => ({ items: [] })),
    ]).then(([draftResp, allResp]: any[]) => {
      const weekStart = getWeekStart();
      const thisWeekCount = (allResp.items || []).filter((item: any) => {
        if (!item?.created_at) return false;
        return new Date(item.created_at) >= weekStart;
      }).length;
      setGovernanceStats({
        pendingProposals: draftResp.total || 0,
        evolutionsThisWeek: thisWeekCount,
      });
    });

    platformApi.overview().then(setOverview).catch(() => {});
    platformApi.runtimeHealth().then(setRuntimeHealth).catch(() => {});
  }, []);

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>控制台概览</h1>

      {/* 业务统计 */}
      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 32 }}>
        <StatCard label="服务商" value={counts.providers} color="#1677ff" />
        <StatCard label="注册模型" value={counts.models} color="#722ed1" />
        <StatCard label="虚拟密钥" value={counts.keys} color="#faad14" />
        <StatCard label="技能数量" value={counts.skills} color="#52c41a" />
      </div>

      {/* AI 治理指标 */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 12 }}>AI 技能治理指标</div>
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <StatCard label="技能总数" value={overview?.skills_total ?? overview?.total_skills ?? 0} color="#13c2c2" />
          <StatCard label="待审提案" value={governanceStats.pendingProposals} color="#fa8c16" />
          <StatCard label="本周演化" value={governanceStats.evolutionsThisWeek} color="#2f54eb" />
        </div>
      </div>

      {/* 服务健康 */}
      {overview && (
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 12 }}>
            服务健康状态
            <span style={{ fontSize: 12, color: '#aaa', marginLeft: 8, fontWeight: 400 }}>
              密钥 {overview.keys_active ?? overview.active_keys ?? 0}/{overview.keys_total ?? overview.total_keys ?? 0} 有效 ·
              会话 {overview.sessions_total ?? overview.total_sessions ?? 0} ·
              技能 {overview.skills_total ?? overview.total_skills ?? 0}
            </span>
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {(overview.service_status ?? overview.service_statuses ?? []).map((s: any) => (
              <ServiceBadge key={s.name} name={s.name} reachable={s.reachable} detail={s.detail} />
            ))}
          </div>
          {(overview.gateway_models_total ?? overview.gateway_model_count) != null && (
            <div style={{ fontSize: 13, color: '#888', marginTop: 10 }}>
              LiteLLM 网关已注册模型：{overview.gateway_models_total ?? overview.gateway_model_count} 个
            </div>
          )}
        </div>
      )}

      {runtimeHealth && (
        <div style={{ marginBottom: 32, background: '#fff', borderRadius: 8, padding: 20, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
          <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>
            运行时健康（聚合探测）
            <span style={{ marginLeft: 10, fontSize: 12, color: runtimeHealth.ok ? '#52c41a' : '#ff4d4f' }}>
              {runtimeHealth.ok ? 'OK' : '异常'}
            </span>
          </div>

          {hasBlockingFailure && (
            <div
              style={{
                marginBottom: 12,
                border: '1px solid #ffccc7',
                background: '#fff2f0',
                color: '#cf1322',
                borderRadius: 8,
                padding: '10px 12px',
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                阻断项告警：检测到 {blockingFailed.length} 个关键失败，请优先修复
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                {blockingFailed.map((name) => (
                  <span key={name} style={{ fontSize: 12, background: '#fff', border: '1px solid #ffa39e', borderRadius: 12, padding: '2px 10px' }}>
                    {name}
                  </span>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <a href="/providers?focus=blocking_failed" style={{ textDecoration: 'none', fontSize: 12, fontWeight: 600, color: '#fff', background: '#cf1322', borderRadius: 4, padding: '6px 10px' }}>
                  去修复服务商配置
                </a>
                <a href="/models?focus=blocking_failed" style={{ textDecoration: 'none', fontSize: 12, fontWeight: 600, color: '#cf1322', background: '#fff', border: '1px solid #ff7875', borderRadius: 4, padding: '6px 10px' }}>
                  去检查模型注册
                </a>
              </div>
            </div>
          )}

          <div style={{ fontSize: 12, color: '#888', marginBottom: 10 }}>
            模型 {runtimeHealth.model_count ?? 0} · 聊天模型 {runtimeHealth.chat_model_count ?? 0} · Embedding 模型 {runtimeHealth.embedding_model_count ?? 0}
          </div>
          <div style={{ display: 'grid', gap: 8 }}>
            {(runtimeHealth.checks ?? []).map((item: any) => (
              <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                <span>{item.ok ? '🟢' : (item.blocking ? '🔴' : '🟡')}</span>
                <span style={{ minWidth: 120, fontWeight: 600 }}>{item.name}</span>
                <span style={{ color: '#666' }}>{item.detail || '—'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 快速入口 */}
      <div style={{ background: '#fff', borderRadius: 8, padding: 24, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
        <div style={{ fontWeight: 600, marginBottom: 12, fontSize: 15 }}>快速入口</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {[
            { label: '技能平台', href: '/skills' },
            { label: '知识库(RAG)', href: '/knowledge' },
            { label: '智能体', href: '/agents' },
            { label: '虚拟密钥', href: '/keys' },
            { label: '模型注册', href: '/models' },
            { label: 'AI 服务商', href: '/providers' },
            { label: '治理中心', href: '/governance' },
            { label: '观测中心', href: '/observe' },
            { label: '系统设置', href: '/settings' },
          ].map(item => (
            <a
              key={item.href}
              href={item.href}
              style={{ padding: '8px 20px', background: '#f0f5ff', color: '#1677ff', borderRadius: 4, textDecoration: 'none', fontSize: 14, fontWeight: 500 }}
            >{item.label}</a>
          ))}
        </div>
      </div>
    </div>
  );
}
