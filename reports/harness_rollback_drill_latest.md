# Harness Rollback Drill Report (Task 6.3)

- Generated At: 2026-06-02T07:45:52.895192+00:00
- Commit: d459ddd
- Base URL: http://localhost:3000
- Capability Alias: chat-default

## Drill Checks

- contract_canary_injected: passed
- rollout_rollback_decision: passed
- contract_restored_after_rollback: passed
- plan_rollback_terminal_state: passed
- trace_contains_rollback_event: passed
- audit_contains_rollback_decision: passed

## Runtime Evidence

- plan_id: plan-ba60c3f96567431cafbf592d4fd60f88
- trace_id: trace-3a4617befee648af9917d7299a015ee0
- rollback_decision_id: rdec-4b2258147ed540f1adc875676510941d
- latest_audit_rollback_decision_id: rdec-4b2258147ed540f1adc875676510941d

## Contract Before/After

- stable_strategy_before: strategy-rollback-stable-v1
- stable_strategy_after: strategy-rollback-stable-v1
- canary_strategy_after: None
- canary_traffic_after: 0

## Plan and Trace

- plan_state_after_rollback_event: rolled_back
- trace_event_types: validate, prepare, start, rollback

## Rollout Audit Snapshot

- decision_count: 6
- rollback_decision_count: 2
- latest_rollback_canary_strategy_after: None
- latest_rollback_canary_traffic_percent_after: 0

## Metrics Snapshot

- plan_total: 14
- terminal_total: 2
- completed_total: 1
- failed_total: 0
- rolled_back_total: 1
- success_rate: 0.5
- rollback_rate: 0.5
- avg_latency_ms: 92.0
- p95_latency_ms: 92.0
- total_cost_usd: 0.4367999999999997

## Alert Evaluation

- status: ok
- alert_count: 0
