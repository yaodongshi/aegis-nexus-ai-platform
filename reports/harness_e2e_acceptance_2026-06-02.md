# Harness E2E Acceptance Report (Task 6.2)

- Generated At: 2026-06-02T07:43:56.948257+00:00
- Commit: d459ddd
- Base URL: http://localhost:3000
- Capability Alias: chat-default

## Flow Result

- create_plan: passed
- run_plan: passed
- complete_plan: passed
- trace_fetch: passed
- replay_trace: passed
- rollout_canary: passed
- rollout_promote: passed
- rollout_rollback: passed
- audit_list_rollout_decisions: passed

## Runtime IDs

- source_plan_id: plan-a7c7d84d48af45d595aac277f2d471e0
- source_trace_id: trace-0b1f9969008e4496a33f525eefa70733
- replay_plan_id: plan-7f7d64cb30184078af0489dac50c1f19
- replayed_event_count: 3

## Plan States

- source_plan_state_after_complete: completed
- replay_plan_state: running

## Rollout Audit

- rollout_decision_count: 4
- actions_seen: canary, promote, canary, rollback
- last_decision_id: rdec-2180688dc2cd4da59d085419af19a51c

## Final Contract

- stable_strategy_id: strategy-canary-v2
- canary_strategy_id: None
- canary_traffic_percent: 0

## Metrics Snapshot

- plan_total: 13
- terminal_total: 1
- completed_total: 1
- failed_total: 0
- rolled_back_total: 0
- success_rate: 1.0
- rollback_rate: 0.0
- avg_latency_ms: 92.0
- p95_latency_ms: 92.0
- total_cost_usd: 0.4031999999999997

## Alert Evaluation

- status: ok
- alert_count: 0
