# 🤝 Contributing to MemWire

Thank you for your interest in contributing to **MemWire** — the open source memory infrastructure for AI agents.

We welcome contributions of all kinds:

- Code
- Documentation
- Tests
- Examples
- Integrations
- Design discussions
- Bug reports
- Feature proposals

---

# 📌 Code of Conduct

Please read and follow our `CODE_OF_CONDUCT.md`.

We are committed to maintaining a respectful, inclusive, and collaborative community.

---

# 🧭 Ways to Contribute

## 1️⃣ Report Bugs

If you find a bug:

- Check existing issues first
- Open a new issue with:
  - Clear title
  - Steps to reproduce
  - Expected behavior
  - Environment details

---

## 2️⃣ Propose Features

For new features:

- Open a GitHub Issue
- Clearly describe:
  - The problem
  - Proposed solution
  - Alternative approaches considered

For larger architectural changes, open an **RFC discussion** before coding.

---

## 3️⃣ Submit a Pull Request

### Step 1: Fork the repository

git clone https://github.com/memoryoss/memwire
cd memwire

### Step 2: Create a feature branch

git checkout -b feature/your-feature-name

### Step 3: Make your changes

Please follow:

- Clear, readable code
- Type hints where applicable
- Docstrings for public APIs
- Unit tests for new logic

### Step 4: Run tests locally

pytest

Ensure:
- All tests pass
- No linting errors

### Step 5: Open a Pull Request

Your PR should include:

- Clear description
- Linked issue (if applicable)
- Screenshots (if UI changes)
- Tests

---

# 🧪 Development Guidelines

## Code Style

- Python: PEP8
- Use type hints
- Prefer explicit over implicit
- Keep functions small and focused

---

## Architecture Principles

MemWire follows:

1. SQL as source of truth  
2. Explicit structured memory over raw transcripts  
3. Model-agnostic design  
4. Local-first philosophy  
5. Multi-tenant support  

All contributions should respect these principles.

---

# 🏗 Project Structure (High-Level)

memwire/
│
├── api/
├── memory/
├── ingestion/
├── vector/
├── models/
├── storage/
└── tests/

---

# 🧠 Good First Issues

Look for issues labeled:

- good-first-issue
- help-wanted
- community

---

# 🛡 Security Issues

If you discover a security vulnerability:

**Do not open a public issue.**

Instead, email:
security@memwire.dev

---

# 📄 License

By contributing, you agree that your contributions will be licensed under the project's open source license.

---

# 🙌 Recognition

All contributors will be listed in:

- GitHub contributors
- Release notes (for significant features)
- Community acknowledgements

Thank you for helping build the memory backbone for AI agents 🚀
