import React, { useEffect, useState } from 'react';
import { approvalsApi, learningApi, policiesApi } from '../../lib/api';

type GovTab = 'policies' | 'approvals' | 'learning';

const STATUS_STYLE: Record<string, React.CSSProperties> = {
  pending:  { background: '#fffbe6', color: '#d48806' },
  approved: { background: '#f6ffed', color: '#52c41a' },
  rejected: { background: '#fff2f0', color: '#ff4d4f' },
  canceled: { background: '#f5f5f5', color: '#aaa' },
  active:   { background: '#f6ffed', color: '#52c41a' },
  inactive: { background: '#f5f5f5', color: '#aaa' },
};

export default function GovernancePage() {
  const [tab, setTab] = useState<GovTab>('learning');

  // ── Policies ──
  const [policies, setPolicies] = useState<any[]>([]);
  const [policyForm, setPolicyForm] = useState({ name: '', type: 'rate_limit', rules: '{}', status: 'active' });
  const [showPolicyForm, setShowPolicyForm] = useState(false);
  const [savingPolicy, setSavingPolicy] = useState(false);

  // ── Approvals ──
  const [approvals, setApprovals] = useState<any[]>([]);
  const [approvalForm, setApprovalForm] = useState({ applicant_id: '', action: '', resource_id: '', reason: '' });
  const [showApprovalForm, setShowApprovalForm] = useState(false);
  const [submittingApproval, setSubmittingApproval] = useState(false);

  // ── Learning Ops ──
  const [gitRepos, setGitRepos] = useState<any[]>([]);
  const [hookEvents, setHookEvents] = useState<any[]>([]);
  const [conflictUpdates, setConflictUpdates] = useState<any[]>([]);
  const [hookSecretStatus, setHookSecretStatus] = useState<any>(null);
  const [rotatedSecret, setRotatedSecret] = useState('');
  const [learningLoading, setLearningLoading] = useState(false);
  const [pullingRepoId, setPullingRepoId] = useState('');
  const [rotatingSecret, setRotatingSecret] = useState(false);
  const [evolutionLoading, setEvolutionLoading] = useState(false);
  const [teamId, setTeamId] = useState('team_default');
  const [skillId, setSkillId] = useState('');
  const [createdBy, setCreatedBy] = useState('governance-ui');
  const [ruleSetId, setRuleSetId] = useState('');
  const [agentWorkflows, setAgentWorkflows] = useState<any[]>([]);
  const [evolutionResult, setEvolutionResult] = useState<any>(null);
  const [evolutionOverview, setEvolutionOverview] = useState<any>(null);
  const [evolutionActions, setEvolutionActions] = useState<any[]>([]);
  const [actionFilterName, setActionFilterName] = useState('');
  const [actionFilterStatus, setActionFilterStatus] = useState('');
  const [actionWindowMinutes, setActionWindowMinutes] = useState('120');
  const [actionTemplates, setActionTemplates] = useState<any[]>([]);
  const [templateName, setTemplateName] = useState('');
  const [templateActions, setTemplateActions] = useState('ingest_gateway_knowledge,summarize_rag_to_skill,generate_agent_workflow');

  const [error, setError] = useState('');

  const loadPolicies  = () => policiesApi.list().then(r => setPolicies(r.items)).catch(e => setError(e.message));
  const loadApprovals = () => approvalsApi.list().then(r => setApprovals(r.items)).catch(e => setError(e.message));
  const loadLearning = async () => {
    setLearningLoading(true);
    try {
      const [reposResp, hooksResp, updatesResp, secretStatus, workflowsResp, overviewResp, actionsResp, templatesResp] = await Promise.all([
        learningApi.gitRepos(),
        learningApi.hookEvents(),
        learningApi.skillUpdates({ status: 'draft', limit: 30, offset: 0 }),
        learningApi.hookSecretStatus(),
        learningApi.listAgentWorkflows(20, 0),
        learningApi.evolutionOverview(),
        learningApi.evolutionActions({
          action_name: actionFilterName || undefined,
          status: (actionFilterStatus as 'success' | 'failed') || undefined,
          window_minutes: actionWindowMinutes ? Number(actionWindowMinutes) : undefined,
          limit: 30,
          offset: 0,
        }),
        learningApi.actionTemplates(50, 0),
      ]);
      setGitRepos(reposResp.items || []);
      setHookEvents(hooksResp.items || []);
      setConflictUpdates(updatesResp.items || []);
      setHookSecretStatus(secretStatus);
      setAgentWorkflows(workflowsResp.items || []);
      setEvolutionOverview(overviewResp);
      setEvolutionActions(actionsResp.items || []);
      setActionTemplates(templatesResp.items || []);
    } catch (e: any) {
      setError(e.message || 'Learning 数据加载失败');
    } finally {
      setLearningLoading(false);
    }
  };

  const handleReloadActions = async () => {
    setLearningLoading(true);
    try {
      const actionsResp = await learningApi.evolutionActions({
        action_name: actionFilterName || undefined,
        status: (actionFilterStatus as 'success' | 'failed') || undefined,
        window_minutes: actionWindowMinutes ? Number(actionWindowMinutes) : undefined,
        limit: 30,
        offset: 0,
      });
      setEvolutionActions(actionsResp.items || []);
    } catch (e: any) {
      setError(e.message || '刷新动作流水线失败');
    } finally {
      setLearningLoading(false);
    }
  };

  const handleReplayLastSuccessChain = async () => {
    setEvolutionLoading(true);
    try {
      const result = await learningApi.replayLastSuccessChain(5);
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '重放成功动作链失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleCreateActionTemplate = async () => {
    if (!templateName.trim()) {
      setError('请先填写模板名称');
      return;
    }
    const actionNames = templateActions
      .split(',')
      .map(item => item.trim())
      .filter(Boolean);
    if (actionNames.length === 0) {
      setError('请至少填写一个动作名');
      return;
    }
    setEvolutionLoading(true);
    try {
      const result = await learningApi.createActionTemplate({
        name: templateName.trim(),
        action_names: actionNames,
        created_by: createdBy,
      });
      setEvolutionResult(result);
      setTemplateName('');
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '创建动作链模板失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleRunActionTemplate = async (templateId: string, dryRun: boolean) => {
    setEvolutionLoading(true);
    try {
      const result = await learningApi.runActionTemplate(templateId, {
        dry_run: dryRun,
        context: {
          team_id: teamId,
          skill_id: skillId,
          rule_set_id: ruleSetId,
          actor: createdBy,
        },
      });
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '运行动作链模板失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  useEffect(() => { loadPolicies(); loadApprovals(); loadLearning(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handlePullRepo = async (repoId: string) => {
    setPullingRepoId(repoId);
    try {
      await learningApi.pullRepo(repoId);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '拉取仓库失败');
    } finally {
      setPullingRepoId('');
    }
  };

  const handleRotateSecret = async () => {
    setRotatingSecret(true);
    setRotatedSecret('');
    try {
      const result = await learningApi.rotateHookSecret();
      setRotatedSecret(result.new_secret || '');
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '轮换 Hook Secret 失败');
    } finally {
      setRotatingSecret(false);
    }
  };

  const handleUploadSkillBundle = async () => {
    if (!teamId || !skillId) {
      setError('请先填写 Team ID 和 Skill ID');
      return;
    }
    setEvolutionLoading(true);
    try {
      const result = await learningApi.uploadSkillBundle({
        team_id: teamId,
        skill_id: skillId,
        version: 'v1',
        tags: ['governance', 'manual-upload'],
        uploaded_by: createdBy,
        bundle: { source: 'governance-ui' },
      });
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '上传 Skill Bundle 失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleGenerateTeamRules = async () => {
    if (!teamId) {
      setError('请先填写 Team ID');
      return;
    }
    setEvolutionLoading(true);
    try {
      const result = await learningApi.generateTeamRules(teamId);
      setRuleSetId(result?.rule?.rule_set_id || '');
      setEvolutionResult(result);
    } catch (e: any) {
      setError(e.message || '生成 Team Rules 失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleApplyTeamRules = async () => {
    if (!teamId || !ruleSetId) {
      setError('请先生成 Rule Set 或填写 Rule Set ID');
      return;
    }
    setEvolutionLoading(true);
    try {
      const result = await learningApi.applyTeamRules(teamId, ruleSetId, false);
      setEvolutionResult(result);
    } catch (e: any) {
      setError(e.message || '应用 Team Rules 失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleIngestGatewayKnowledge = async () => {
    if (!teamId) {
      setError('请先填写 Team ID');
      return;
    }
    setEvolutionLoading(true);
    try {
      const result = await learningApi.ingestGatewayKnowledge({
        created_by: createdBy,
        min_quality_score: 0.6,
        items: [
          {
            source_type: 'session',
            source_id: `session-${Date.now()}`,
            title: '会话有效知识摘要',
            content: '治理页触发：将工作会话中的有效知识导入RAG，并用于后续skill与agent优化。',
            team_id: teamId,
            tags: ['effective-knowledge', 'session-summary'],
            quality_score: 0.82,
            metadata: { trigger: 'governance-ui' },
          },
        ],
      });
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '网关知识入库失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleSummarizeRagToSkill = async () => {
    setEvolutionLoading(true);
    try {
      const result = await learningApi.summarizeRagToSkill({
        scope: 'team',
        limit: 20,
        created_by: createdBy,
      });
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || 'RAG 总结到 Skill 失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleGenerateAgentWorkflow = async () => {
    setEvolutionLoading(true);
    try {
      const result = await learningApi.generateAgentWorkflow({
        scope: 'team',
        created_by: createdBy,
        constraints: { team_id: teamId },
      });
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '生成 Agent Workflow 失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleOptimizeLatestWorkflow = async () => {
    const latest = agentWorkflows[0];
    if (!latest?.workflow_id) {
      setError('暂无可优化的 Workflow，请先生成');
      return;
    }
    setEvolutionLoading(true);
    try {
      const result = await learningApi.optimizeAgentWorkflow(latest.workflow_id, 20);
      setEvolutionResult(result);
      await loadLearning();
    } catch (e: any) {
      setError(e.message || '优化 Agent Workflow 失败');
    } finally {
      setEvolutionLoading(false);
    }
  };

  const handleUpsertPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingPolicy(true);
    try {
      let rules: Record<string, unknown> = {};
      try { rules = JSON.parse(policyForm.rules); } catch { throw new Error('规则必须是合法的 JSON，例如 {"rpm": 60}'); }
      await policiesApi.upsert({ name: policyForm.name, type: policyForm.type, rules, status: policyForm.status });
      setPolicyForm({ name: '', type: 'rate_limit', rules: '{}', status: 'active' });
      setShowPolicyForm(false);
      loadPolicies();
    } catch (e: any) { setError(e.message); }
    finally { setSavingPolicy(false); }
  };

  const handleSubmitApproval = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingApproval(true);
    try {
      await approvalsApi.submit(approvalForm);
      setApprovalForm({ applicant_id: '', action: '', resource_id: '', reason: '' });
      setShowApprovalForm(false);
      loadApprovals();
    } catch (e: any) { setError(e.message); }
    finally { setSubmittingApproval(false); }
  };

  const successActionCount = evolutionActions.filter((item) => item.status === 'success').length;
  const failedActionCount = evolutionActions.filter((item) => item.status === 'failed').length;
  const draftSkillCount = conflictUpdates.length;
  const templateCount = actionTemplates.length;

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>治理中心</h1>
      <div style={{ marginBottom: 16, color: '#667085', fontSize: 13 }}>
        统一编排 Team AI Platform 的策略、审批、学习闭环与模板化执行。
      </div>

      <div
        style={{
          marginBottom: 16,
          borderRadius: 10,
          padding: 14,
          background: 'linear-gradient(120deg, #e6f4ff 0%, #f6ffed 100%)',
          border: '1px solid #d6e4ff',
          display: 'grid',
          gridTemplateColumns: 'repeat(4, minmax(0, 1fr))',
          gap: 10,
        }}
      >
        <MetricBox label="成功动作" value={successActionCount} color="#52c41a" />
        <MetricBox label="失败动作" value={failedActionCount} color="#ff4d4f" />
        <MetricBox label="草案提案" value={draftSkillCount} color="#1677ff" />
        <MetricBox label="模板数量" value={templateCount} color="#722ed1" />
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12, padding: '8px 12px', background: '#fff2f0', borderRadius: 4 }}>{error}<button onClick={() => setError('')} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer', color: '#ff4d4f' }}>✕</button></div>}

      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid #f0f0f0' }}>
        {([['policies', '访问策略'], ['approvals', '审批中心'], ['learning', '学习闭环运维']] as [GovTab, string][]).map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} style={tabBtn(tab === key)}>{label}</button>
        ))}
      </div>

      {/* ── 策略管理 ── */}
      {tab === 'policies' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <button style={btnPrimary} onClick={() => setShowPolicyForm(v => !v)}>+ 新建策略</button>
          </div>
          {showPolicyForm && (
            <form onSubmit={handleUpsertPolicy} style={{ background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-start' }}>
                <input style={inputStyle} placeholder="策略名称" value={policyForm.name} onChange={e => setPolicyForm(f => ({ ...f, name: e.target.value }))} required />
                <select style={inputStyle} value={policyForm.type} onChange={e => setPolicyForm(f => ({ ...f, type: e.target.value }))}>
                  <option value="rate_limit">速率限制</option>
                  <option value="quota">配额管理</option>
                  <option value="ip_allowlist">IP 白名单</option>
                  <option value="model_access">模型访问控制</option>
                  <option value="cost_cap">费用上限</option>
                </select>
                <select style={inputStyle} value={policyForm.status} onChange={e => setPolicyForm(f => ({ ...f, status: e.target.value }))}>
                  <option value="active">激活</option>
                  <option value="inactive">停用</option>
                </select>
                <textarea
                  rows={2}
                  style={{ ...inputStyle, width: 260, fontFamily: 'monospace', fontSize: 12, resize: 'vertical' }}
                  placeholder={'规则 JSON，如 {"rpm": 60}'}
                  value={policyForm.rules}
                  onChange={e => setPolicyForm(f => ({ ...f, rules: e.target.value }))}
                />
                <button style={btnPrimary} type="submit" disabled={savingPolicy}>{savingPolicy ? '保存中...' : '确认保存'}</button>
                <button type="button" style={{ ...btnPrimary, background: '#fff', color: '#666', border: '1px solid #d9d9d9' }} onClick={() => setShowPolicyForm(false)}>取消</button>
              </div>
            </form>
          )}
          <table style={tableStyle}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                {['策略名', '类型', '规则摘要', '状态', '更新时间'].map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {policies.map(p => (
                <tr key={p.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={tdStyle}><span style={{ fontWeight: 500 }}>{p.name}</span></td>
                  <td style={tdStyle}><span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: '#f0f5ff', color: '#1677ff' }}>{p.type}</span></td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12, color: '#555', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{JSON.stringify(p.rules)}</td>
                  <td style={tdStyle}><span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, ...(STATUS_STYLE[p.status] ?? {}) }}>{p.status}</span></td>
                  <td style={{ ...tdStyle, fontSize: 12, color: '#aaa' }}>{new Date(p.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {policies.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无策略，点击「新建策略」创建第一条</div>}
        </>
      )}

      {/* ── 审批中心 ── */}
      {tab === 'approvals' && (
        <>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <button style={btnPrimary} onClick={() => setShowApprovalForm(v => !v)}>+ 提交申请</button>
          </div>
          {showApprovalForm && (
            <form onSubmit={handleSubmitApproval} style={{ background: '#fff', padding: 16, borderRadius: 8, marginBottom: 16, boxShadow: '0 1px 4px rgba(0,0,0,.08)' }}>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
                <input style={inputStyle} placeholder="申请人 ID" value={approvalForm.applicant_id} onChange={e => setApprovalForm(f => ({ ...f, applicant_id: e.target.value }))} required />
                <input style={inputStyle} placeholder="操作（如 access_model）" value={approvalForm.action} onChange={e => setApprovalForm(f => ({ ...f, action: e.target.value }))} required />
                <input style={inputStyle} placeholder="资源 ID" value={approvalForm.resource_id} onChange={e => setApprovalForm(f => ({ ...f, resource_id: e.target.value }))} required />
                <input style={{ ...inputStyle, width: 260 }} placeholder="申请理由" value={approvalForm.reason} onChange={e => setApprovalForm(f => ({ ...f, reason: e.target.value }))} required />
                <button style={btnPrimary} type="submit" disabled={submittingApproval}>{submittingApproval ? '提交中...' : '确认提交'}</button>
                <button type="button" style={{ ...btnPrimary, background: '#fff', color: '#666', border: '1px solid #d9d9d9' }} onClick={() => setShowApprovalForm(false)}>取消</button>
              </div>
            </form>
          )}
          <table style={tableStyle}>
            <thead>
              <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                {['申请人', '操作', '资源', '状态', '理由', '提交时间'].map(h => <th key={h} style={thStyle}>{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {approvals.map(a => (
                <tr key={a.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                  <td style={tdStyle}>{a.applicant_id}</td>
                  <td style={tdStyle}><span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, background: '#f0f5ff', color: '#1677ff' }}>{a.action}</span></td>
                  <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{a.resource_id}</td>
                  <td style={tdStyle}><span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, ...(STATUS_STYLE[a.status] ?? {}) }}>{a.status}</span></td>
                  <td style={{ ...tdStyle, fontSize: 12, color: '#555', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{a.reason}</td>
                  <td style={{ ...tdStyle, fontSize: 12, color: '#aaa' }}>{new Date(a.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {approvals.length === 0 && <div style={{ color: '#aaa', marginTop: 20 }}>暂无审批记录</div>}
        </>
      )}

      {tab === 'learning' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
            <div style={{ ...panelStyle }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Hook Secret</div>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                当前来源：{hookSecretStatus?.source || 'none'}
                {hookSecretStatus?.masked_secret ? `（${hookSecretStatus.masked_secret}）` : ''}
              </div>
              <button style={btnPrimary} onClick={handleRotateSecret} disabled={rotatingSecret}>
                {rotatingSecret ? '轮换中...' : '轮换 Secret'}
              </button>
              {rotatedSecret && (
                <div style={{ marginTop: 8, fontSize: 12, color: '#d48806' }}>
                  新 Secret（请保存）：{rotatedSecret}
                </div>
              )}
            </div>

            <div style={{ ...panelStyle }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>冲突草案</div>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                当前 draft 更新数：{conflictUpdates.length}
              </div>
              <button style={btnPrimary} onClick={loadLearning} disabled={learningLoading}>
                {learningLoading ? '刷新中...' : '刷新数据'}
              </button>
            </div>
          </div>

          <div style={{ ...panelStyle, marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>仓库拉取</div>
            <table style={tableStyle}>
              <thead>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  {['仓库', '分支', '最近同步', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {gitRepos.map((r) => (
                  <tr key={r.id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                    <td style={tdStyle}>{r.name}</td>
                    <td style={tdStyle}>{r.branch}</td>
                    <td style={{ ...tdStyle, fontSize: 12, color: '#888' }}>{r.last_synced_at ? new Date(r.last_synced_at).toLocaleString() : '-'}</td>
                    <td style={tdStyle}>
                      <button style={btnPrimary} onClick={() => handlePullRepo(r.id)} disabled={pullingRepoId === r.id}>
                        {pullingRepoId === r.id ? '拉取中...' : 'Pull & Ingest'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {gitRepos.length === 0 && <div style={{ color: '#aaa', marginTop: 10 }}>未配置 Git 仓库</div>}
          </div>

          <div style={{ ...panelStyle, marginBottom: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>MCP-Skill-RAG-Agent 进化动作</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8, marginBottom: 10 }}>
              <div style={{ background: '#f7faff', borderRadius: 6, padding: 8, fontSize: 12 }}>Skill Bundles: <b>{evolutionOverview?.skill_bundle_total ?? 0}</b></div>
              <div style={{ background: '#f7faff', borderRadius: 6, padding: 8, fontSize: 12 }}>Team Rules: <b>{evolutionOverview?.team_rule_total ?? 0}</b></div>
              <div style={{ background: '#f7faff', borderRadius: 6, padding: 8, fontSize: 12 }}>Gateway Knowledge: <b>{evolutionOverview?.gateway_knowledge_total ?? 0}</b></div>
              <div style={{ background: '#f7faff', borderRadius: 6, padding: 8, fontSize: 12 }}>RAG Skill Drafts: <b>{evolutionOverview?.rag_skill_update_total ?? 0}</b></div>
              <div style={{ background: '#f7faff', borderRadius: 6, padding: 8, fontSize: 12 }}>Agent Workflows: <b>{evolutionOverview?.agent_workflow_total ?? 0}</b></div>
              <div style={{ background: '#f7faff', borderRadius: 6, padding: 8, fontSize: 12 }}>Optimized Workflows: <b>{evolutionOverview?.optimized_workflow_total ?? 0}</b></div>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              <input style={inputStyle} value={teamId} onChange={e => setTeamId(e.target.value)} placeholder="Team ID" />
              <input style={inputStyle} value={skillId} onChange={e => setSkillId(e.target.value)} placeholder="Skill ID" />
              <input style={inputStyle} value={createdBy} onChange={e => setCreatedBy(e.target.value)} placeholder="Created By" />
              <input style={inputStyle} value={ruleSetId} onChange={e => setRuleSetId(e.target.value)} placeholder="Rule Set ID" />
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button style={btnPrimary} onClick={handleUploadSkillBundle} disabled={evolutionLoading}>上传 Skill Bundle</button>
              <button style={btnPrimary} onClick={handleGenerateTeamRules} disabled={evolutionLoading}>生成 Team Rules</button>
              <button style={btnPrimary} onClick={handleApplyTeamRules} disabled={evolutionLoading}>应用 Team Rules</button>
              <button style={btnPrimary} onClick={handleIngestGatewayKnowledge} disabled={evolutionLoading}>会话知识入RAG</button>
              <button style={btnPrimary} onClick={handleSummarizeRagToSkill} disabled={evolutionLoading}>RAG总结到Skill</button>
              <button style={btnPrimary} onClick={handleGenerateAgentWorkflow} disabled={evolutionLoading}>生成Agent工作流</button>
              <button style={btnPrimary} onClick={handleOptimizeLatestWorkflow} disabled={evolutionLoading}>优化最新工作流</button>
              <button style={btnPrimary} onClick={handleReplayLastSuccessChain} disabled={evolutionLoading}>重放最近成功动作链</button>
            </div>
            <div style={{ marginTop: 10, fontSize: 12, color: '#666' }}>
              当前工作流数量：{agentWorkflows.length}
            </div>
            {evolutionResult && (
              <pre style={{ marginTop: 10, background: '#f7f7f7', padding: 10, borderRadius: 6, fontSize: 12, overflow: 'auto' }}>
                {JSON.stringify(evolutionResult, null, 2)}
              </pre>
            )}
          </div>

          <div style={{ ...panelStyle }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>进化动作流水线</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              <input style={inputStyle} value={actionFilterName} onChange={e => setActionFilterName(e.target.value)} placeholder="动作名筛选" />
              <select style={inputStyle} value={actionFilterStatus} onChange={e => setActionFilterStatus(e.target.value)}>
                <option value="">全部状态</option>
                <option value="success">success</option>
                <option value="failed">failed</option>
              </select>
              <input style={inputStyle} value={actionWindowMinutes} onChange={e => setActionWindowMinutes(e.target.value)} placeholder="时间窗口(分钟)" />
              <button style={btnPrimary} onClick={handleReloadActions} disabled={learningLoading}>应用筛选</button>
            </div>
            <table style={tableStyle}>
              <thead>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  {['动作', '状态', '执行人', '摘要', '时间'].map(h => <th key={h} style={thStyle}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {evolutionActions.map((a) => (
                  <tr key={a.action_id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                    <td style={tdStyle}>{a.action_name}</td>
                    <td style={tdStyle}>
                      <span style={{ fontSize: 12, padding: '2px 8px', borderRadius: 3, ...(a.status === 'success' ? STATUS_STYLE.approved : STATUS_STYLE.rejected) }}>
                        {a.status}
                      </span>
                    </td>
                    <td style={{ ...tdStyle, fontSize: 12 }}>{a.actor || '-'}</td>
                    <td style={{ ...tdStyle, fontSize: 12, color: '#666', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {a.detail || '-'}
                    </td>
                    <td style={{ ...tdStyle, fontSize: 12, color: '#888' }}>{a.created_at ? new Date(a.created_at).toLocaleString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {evolutionActions.length === 0 && <div style={{ color: '#aaa', marginTop: 10 }}>暂无进化动作记录</div>}
          </div>

          <div style={{ ...panelStyle, marginTop: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>动作链模板</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
              <input style={inputStyle} value={templateName} onChange={e => setTemplateName(e.target.value)} placeholder="模板名称" />
              <input
                style={{ ...inputStyle, minWidth: 420 }}
                value={templateActions}
                onChange={e => setTemplateActions(e.target.value)}
                placeholder="动作列表(逗号分隔)"
              />
              <button style={btnPrimary} onClick={handleCreateActionTemplate} disabled={evolutionLoading}>保存模板</button>
            </div>
            <table style={tableStyle}>
              <thead>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  {['模板名', '动作数', '创建人', '更新时间', '操作'].map(h => <th key={h} style={thStyle}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {actionTemplates.map((t) => (
                  <tr key={t.template_id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                    <td style={tdStyle}>{t.name}</td>
                    <td style={tdStyle}>{(t.action_names || []).length}</td>
                    <td style={{ ...tdStyle, fontSize: 12 }}>{t.created_by || '-'}</td>
                    <td style={{ ...tdStyle, fontSize: 12, color: '#888' }}>{t.updated_at ? new Date(t.updated_at).toLocaleString() : '-'}</td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        <button style={btnPrimary} onClick={() => handleRunActionTemplate(t.template_id, true)} disabled={evolutionLoading}>Dry Run</button>
                        <button style={btnPrimary} onClick={() => handleRunActionTemplate(t.template_id, false)} disabled={evolutionLoading}>执行模板</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {actionTemplates.length === 0 && <div style={{ color: '#aaa', marginTop: 10 }}>暂无动作链模板</div>}
          </div>

          <div style={{ ...panelStyle, marginTop: 12 }}>
            <div style={{ fontWeight: 600, marginBottom: 8 }}>最近 Hook 事件</div>
            <table style={tableStyle}>
              <thead>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  {['仓库', '分支', '提交', '关联技能', '时间'].map(h => <th key={h} style={thStyle}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {hookEvents.map((e) => (
                  <tr key={e.hook_event_id} style={{ borderBottom: '1px solid #f9f9f9' }}>
                    <td style={tdStyle}>{e.repository}</td>
                    <td style={tdStyle}>{e.branch}</td>
                    <td style={{ ...tdStyle, fontFamily: 'monospace', fontSize: 12 }}>{(e.commit_sha || '').slice(0, 10)}</td>
                    <td style={tdStyle}>{(e.linked_skill_ids || []).join(', ') || '-'}</td>
                    <td style={{ ...tdStyle, fontSize: 12, color: '#888' }}>{e.created_at ? new Date(e.created_at).toLocaleString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {hookEvents.length === 0 && <div style={{ color: '#aaa', marginTop: 10 }}>暂无 Hook 事件</div>}
          </div>
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
const btnPrimary: React.CSSProperties = { padding: '7px 18px', background: '#1677ff', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 14 };
const inputStyle: React.CSSProperties = { padding: '7px 10px', border: '1px solid #d9d9d9', borderRadius: 4, fontSize: 14 };
const tableStyle: React.CSSProperties = { width: '100%', background: '#fff', borderRadius: 8, borderCollapse: 'collapse', boxShadow: '0 1px 4px rgba(0,0,0,.08)' };
const thStyle: React.CSSProperties = { padding: '12px 16px', textAlign: 'left', fontSize: 13, color: '#888', fontWeight: 500 };
const tdStyle: React.CSSProperties = { padding: '12px 16px', fontSize: 14 };
const panelStyle: React.CSSProperties = { background: '#fff', borderRadius: 8, padding: 14, boxShadow: '0 1px 4px rgba(0,0,0,.08)' };

function MetricBox({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ background: '#fff', borderRadius: 8, padding: '12px 14px', border: '1px solid #eef2f6' }}>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}
