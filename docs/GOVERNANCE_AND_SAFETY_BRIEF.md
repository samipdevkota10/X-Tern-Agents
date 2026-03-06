# Governance & Safety Brief

**X-Tern Agents – Disruption Response Planner**  
**Version:** 1.0  
**Last Updated:** March 2026

---

## 1. Overview

X-Tern Agents implements enterprise-grade AI governance aligned with Gartner’s **AI TRiSM** (Trust, Risk, and Security Management) principles. All pipeline runs are evaluated for trust, risk, security, and management controls before completion.

---

## 2. TRiSM Framework Implementation

### 2.1 TRUST

| Principle | Implementation |
|-----------|----------------|
| **Model Explainability** | Agents provide `rationale`; LLM-generated scenarios include `llm_rationale` |
| **Output Consistency** | Deterministic rule fallbacks; routing trace for reproducibility |
| **Human Override Tracking** | `human_decision`, `approver_id`, `approver_note` in DecisionLog |
| **Rationale Required** | Every agent decision logs `rationale` with `confidence_score` |

### 2.2 RISK

| Principle | Implementation |
|-----------|----------------|
| **Risk Classification** | RiskLevel: LOW, MEDIUM, HIGH, CRITICAL |
| **Harm Categories** | FINANCIAL, OPERATIONAL, SAFETY, COMPLIANCE, REPUTATIONAL |
| **Confidence Threshold** | 0.7 minimum; low-confidence outputs flagged for review |
| **Cost/SLA Escalation** | HIGH_COST_THRESHOLD $50k; HIGH_SLA_RISK 0.8; CRITICAL 0.95 |

### 2.3 SECURITY

| Principle | Implementation |
|-----------|----------------|
| **Data Lineage** | pipeline_run_id links all decisions to source disruption |
| **PII Detection** | Regex patterns for SSN, email, credit card, phone |
| **Prompt Injection** | Indicators: "ignore previous", "disregard instructions", "admin override" |
| **Input Sanitization** | AgentSecurityGuard redacts SENSITIVE_FIELDS |
| **Output Validation** | Action whitelist (delay, reroute, substitute, etc.); cost/SLA limits |

### 2.4 MANAGEMENT

| Principle | Implementation |
|-----------|----------------|
| **Approval Workflows** | Human approval required for high-cost/high-SLA scenarios |
| **Escalation Paths** | Manager → Executive approval tiers by cost |
| **Evaluation Records** | TRiSMEvaluation per pipeline run; stored in final_summary |
| **Audit Trail** | DecisionLog entries with full metadata; exportable via API |

---

## 3. Agent Security Guard

The `AgentSecurityGuard` module enforces:

- **Action Whitelisting**: Only delay, reroute, substitute, resequence, expedite, split, cancel, hold
- **Cost Thresholds**: Auto-approve &lt;$5k; Manager &lt;$50k; Executive &lt;$100k
- **SLA Thresholds**: Auto-approve &lt;0.3; Manager &lt;0.7
- **Sensitive Field Redaction**: password, token, secret, api_key, ssn, credit_card, etc.

---

## 4. Human-in-the-Loop

- **Gating**: Scenarios are plans until a human approves them.
- **Execution Engine**: `apply_scenario()` performs real DB updates only after approval.
- **Constraint Checking**: Substitution, inventory, capacity validated before apply.
- **Override Tracking**: Rejections and edits logged with approver_note.

---

## 5. Compliance Readiness

- **Audit Logs**: Every agent decision and human action stored in `decision_logs`.
- **Traceability**: pipeline_run_id → disruption_id → scenarios → decision_logs.
- **Export**: `/api/audit-logs` supports JSON export for compliance review.
- **RAG for Learning**: (Planned) Index decisions for future context retrieval.

---

## 6. Recommendations

1. **RAG Indexing**: Index approved decisions and resolved disruptions into Chroma for learning.
2. **Auto-Resolve**: Consider auto-resolving disruption when all scenarios are handled.
3. **Periodic TRiSM Review**: Run governance reports on a schedule.
4. **Access Control**: Enforce manager vs analyst roles at API and UI levels (currently implemented).
