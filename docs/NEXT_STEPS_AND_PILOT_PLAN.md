# Next Steps & Pilot Plan

**X-Tern Agents – Disruption Response Planner**  
**Version:** 1.0  
**Last Updated:** March 2026

---

## 1. Immediate Fixes (v1.1)

Based on E2E test findings (`docs/E2E_TEST_REPORT_AND_FIX_PLAN.md`):

| Priority | Gap | Action |
|----------|-----|--------|
| High | RAG: Decisions not indexed | Call `kb.add_decision()` in execution_engine after approve/reject |
| High | RAG: Disruptions not indexed | Call `kb.add_disruption()` when disruption marked resolved |
| Medium | Disruption not auto-resolved | Add `_maybe_resolve_disruption()` when all scenarios handled |
| Low | E2E audit log parsing | Handle list response from `/api/audit-logs` |

---

## 2. Pilot Deployment Plan

### Phase 1: Single-DC Pilot (4–6 weeks)

| Week | Milestone |
|------|-----------|
| 1–2 | Deploy backend (Railway/Render) + frontend (Vercel); configure CORS, env vars |
| 2–3 | Seed production DB with real/sanitized disruption types; onboard 2–3 managers |
| 3–4 | Run 20+ disruptions; collect feedback on scenario quality and UX |
| 4–5 | Implement RAG indexing fixes; tune domain knowledge for pilot DC |
| 5–6 | Governance review; document lessons learned |

### Phase 2: Multi-DC Rollout (8–12 weeks)

- Add second DC; validate cross-DC routing and capacity logic
- Integrate with TMS/WMS for automated disruption ingestion (APIs/webhooks)
- Expand RAG with historical decisions from Phase 1

### Phase 3: Scale & Integrate (ongoing)

- Predictive disruption detection
- Automated execution for low-risk scenarios (with safeguards)
- External integrations (ERP, shipping providers)

---

## 3. Technical Roadmap

### Near-term (v1.1)

- [ ] Index decisions to Chroma on approve/reject
- [ ] Index disruptions to Chroma on resolve
- [ ] Auto-resolve disruption when all scenarios handled
- [ ] Real-time alerts (WebSocket or polling)
- [ ] Bulk disruption processing

### Mid-term (v1.2)

- [ ] Real TMS/WMS integration
- [ ] Bedrock embeddings for RAG
- [ ] Mobile-friendly approval flow
- [ ] Dashboard improvements (SLA trend, cost impact)

### Long-term (v2.0)

- [ ] Predictive disruption detection
- [ ] Automated execution for low-risk scenarios
- [ ] Multi-warehouse coordination
- [ ] API for third-party tools

---

## 4. Success Criteria for Pilot

| Metric | Target |
|--------|--------|
| Pipeline completion rate | >95% |
| Scenario acceptance rate | >70% |
| Time to first scenario | <60 seconds |
| Zero critical security incidents | |
| Positive manager feedback | >4/5 |

---

## 5. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM latency/timeout | Deterministic fallback; cache common patterns |
| Pipeline exceeds serverless limits | Host backend on persistent infra (Railway, EC2) |
| Poor scenario quality | Tune RAG, add more domain knowledge, user feedback loop |
| Resistance to AI recommendations | Emphasize human approval; show rationale; phased rollout |

---

## 6. Dependencies

- **AWS**: Optional Bedrock for LLM routing; S3/DynamoDB for artifacts
- **Database**: PostgreSQL for production (RDS or managed)
- **ChromaDB**: For RAG (persistent storage)
- **Frontend Hosting**: Vercel or similar
- **Backend Hosting**: Railway, Render, Fly.io, or EC2

---

## 7. Recommended Next Steps

1. Run `python scripts/e2e_test.py` to validate current state
2. Implement RAG indexing fixes (GAP 1 & 2)
3. Deploy backend + frontend to staging
4. Conduct 2-week pilot with 2–3 managers
5. Review audit logs and governance outputs
6. Plan Phase 2 based on pilot results
