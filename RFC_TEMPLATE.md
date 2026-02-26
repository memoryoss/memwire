# RFC-XXXX: [Title of Proposal]

> **Status:** Draft | Under Review | Accepted | Rejected | Superseded  
> **Author(s):** Your Name ([@github-handle](https://github.com/github-handle))  
> **Created:** YYYY-MM-DD  
> **Updated:** YYYY-MM-DD  
> **Target Version:** vX.Y  
> **Related Issues:** #issue-number

---

## 📌 Summary

<!-- One to three sentences describing what this RFC proposes and why. -->

---

## 🎯 Motivation

<!-- Why is this change needed? What problem does it solve?
     Link to any relevant issues, discussions, or prior art. -->

### Problem Statement

<!-- Describe the current state and its limitations. -->

### Goals

- Goal 1
- Goal 2

### Non-Goals

- Out-of-scope item 1
- Out-of-scope item 2

---

## 🧭 Detailed Design

<!-- This is the core of the RFC. Describe the design in enough detail for
     someone to implement it. Consider: API changes, data model changes,
     new components, interaction diagrams. -->

### Overview

### API Changes (if applicable)

```
# Example endpoint or interface change

POST /v1/memory/...
{
  "field": "value"
}
```

### Data Model Changes (if applicable)

```sql
-- Example schema change
ALTER TABLE memories ADD COLUMN ...;
```

### Component Interactions

<!-- Describe how components interact. Use ASCII diagrams or describe flow. -->

### Configuration

<!-- Any new configuration options or environment variables. -->

---

## 🔄 Migration Plan

<!-- How will existing users and deployments migrate to this change?
     Is this backwards-compatible? If not, what is the migration path? -->

| Concern | Impact | Mitigation |
| --- | --- | --- |
| Backwards compatibility | Low / Medium / High | Description |
| Data migration required | Yes / No | Description |
| Breaking API changes | Yes / No | Description |

---

## 🧪 Testing Strategy

<!-- How will this change be tested?
     Unit tests, integration tests, performance benchmarks, etc. -->

- [ ] Unit tests for core logic
- [ ] Integration tests for API changes
- [ ] Performance benchmarks (if applicable)
- [ ] Manual testing checklist

---

## ⚡ Performance Considerations

<!-- Does this change affect performance? Include benchmarks or estimates
     if relevant. -->

---

## 🔒 Security Considerations

<!-- Does this change introduce any security implications?
     Consider: authentication, authorization, data exposure, injection risks. -->

---

## 🏗 Architecture Principles Alignment

MemWire is built on these core principles — confirm this RFC aligns with them:

| Principle | Alignment | Notes |
| --- | --- | --- |
| Explicit structured memory over raw transcripts | ✅ / ⚠️ / ❌ | |
| Model-agnostic design | ✅ / ⚠️ / ❌ | |
| Local-first philosophy | ✅ / ⚠️ / ❌ | |
| Multi-tenant support | ✅ / ⚠️ / ❌ | |

---

## 🔀 Alternatives Considered

<!-- What other approaches were evaluated and why were they rejected? -->

### Alternative A: [Name]

**Description:** ...

**Reason rejected:** ...

### Alternative B: [Name]

**Description:** ...

**Reason rejected:** ...

---

## 📦 Implementation Plan

<!-- Break down the implementation into phases or milestones. -->

| Phase | Description | Estimated Effort |
| --- | --- | --- |
| Phase 1 | Core implementation | S / M / L |
| Phase 2 | Migration tooling | S / M / L |
| Phase 3 | Documentation | S / M / L |

---

## ❓ Open Questions

<!-- List any unresolved questions or decisions that need community input. -->

1. Question 1?
2. Question 2?

---

## 📄 References

<!-- Links to relevant discussions, prior art, related issues, or external resources. -->

- [GitHub Issue #XXX](https://github.com/memoryoss/memwire/issues/XXX)
- [Related RFC](RFC_TEMPLATE.md)

---

## 🗳 Decision

<!-- To be filled in by maintainers after review. -->

**Decision:** Accepted / Rejected / Deferred  
**Decision Date:** YYYY-MM-DD  
**Decision Rationale:**

> ...

---

*This RFC follows the MemWire RFC process. See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to submit an RFC.*
