# 🛡 Security Policy

This document outlines how to report security vulnerabilities in **MemWire** and what to expect from the process.

---

## 📌 Supported Versions

| Version | Supported |
| --- | --- |
| `main` (latest) | ✅ |
| Previous releases | ⚠️ Best effort |

---

## 🚨 Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Public disclosure before a fix is available puts all MemWire users at risk.

### How to Report

Send an email to:

**hi@memwirelabs.com**

Include the following in your report:

- **Summary** — A clear description of the vulnerability
- **Affected component** — Which part of MemWire is affected (API, memory store, ingestion, vector pipeline, etc.)
- **Steps to reproduce** — Detailed reproduction steps or a proof-of-concept
- **Impact** — What an attacker could achieve by exploiting this
- **Suggested fix** (optional) — If you have a proposed solution

---

## ⏱ Response Timeline

| Stage | Target Time |
| --- | --- |
| Initial acknowledgement | Within 48 hours |
| Triage and severity assessment | Within 5 business days |
| Fix development and testing | Depends on severity |
| Patch release and disclosure | Coordinated with reporter |

We will keep you informed at each stage and credit you in the release notes unless you prefer to remain anonymous.

---

## 🔒 Severity Classification

We use the following severity levels based on [CVSS](https://www.first.org/cvss/):

| Severity | Description |
| --- | --- |
| **Critical** | Remote code execution, full data exfiltration, authentication bypass |
| **High** | Privilege escalation, significant data exposure, tenant isolation bypass |
| **Medium** | Partial data exposure, DoS requiring authentication |
| **Low** | Information leakage, minor configuration issues |

---

## 🏗 Scope

The following are **in scope** for security reports:

- MemWire REST API (`api/`)
- Memory storage and retrieval logic (`memory/`)
- Ingestion pipeline (`ingestion/`)
- Vector search layer (`vector/`)
- Multi-tenant isolation mechanisms
- Authentication and authorization logic
- Docker and deployment configuration

The following are **out of scope**:

- Vulnerabilities in third-party dependencies (please report directly to those projects)
- Issues requiring physical access to the host machine
- Social engineering attacks

---

## 🤝 Coordinated Disclosure

We follow **coordinated disclosure**:

1. Reporter notifies us privately
2. We investigate and develop a fix
3. We release the fix
4. We publish a security advisory
5. Reporter may publicly disclose after the patch is available

We aim to publish advisories within **90 days** of initial report.

---

## 🙏 Recognition

We deeply appreciate responsible disclosure. Reporters of valid vulnerabilities will be:

- Credited in the security advisory (unless anonymity is requested)
- Acknowledged in release notes
- Listed in our community acknowledgements

---

## 📄 Related

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

Thank you for helping keep MemWire and its users safe.
