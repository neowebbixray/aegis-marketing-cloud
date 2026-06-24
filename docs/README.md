# Aegis Marketing Cloud (AMC) — Documentation

> **Revision:** v1.0  
> **Total Volumes:** 15  
> **Estimated Total Pages:** 800–1,500  
> **Status:** 🏗️ In Progress

---

## Document Volumes

| # | Volume | Status | Pages |
|---|--------|--------|-------|
| 1 | [Vision, Mission & Business Goals](./volume-1/01-vision-mission-business-goals.md) | ✅ Complete | ~45 |
| 2 | Product Requirements Document (PRD) | 🏗️ In Progress | ~80 |
| 3 | Software Requirements Specification (SRS) | 🏗️ In Progress | ~120 |
| 4 | System Architecture | 🏗️ In Progress | ~90 |
| 5 | Database Design (ERD, Schemas, Migrations) | 🏗️ In Progress | ~100 |
| 6 | Backend API Specification (REST + GraphQL) | 🏗️ In Progress | ~150 |
| 7 | Frontend UI/UX Design System | 🏗️ In Progress | ~100 |
| 8 | AI Architecture (Hermes, NVIDIA NIM, Prompts, Memory) | 🏗️ In Progress | ~90 |
| 9 | Workflow & Automation Library (n8n) | 🏗️ In Progress | ~70 |
| 10 | Security Architecture and Compliance | 🏗️ In Progress | ~60 |
| 11 | DevOps, Deployment, Monitoring, DR | 🏗️ In Progress | ~80 |
| 12 | Testing Strategy | 🏗️ In Progress | ~60 |
| 13 | Plugin & Marketplace SDK | 🏗️ In Progress | ~70 |
| 14 | Operations Manual (Runbooks, Incident Response) | 🏗️ In Progress | ~90 |
| 15 | Product Roadmap (v1.0–v5.0) | 🏗️ In Progress | ~50 |

---

## Quick Links

- [Volume 1: Vision, Mission & Business Goals](./volume-1/01-vision-mission-business-goals.md)
- [Product Backlog](./volume-15/01-roadmap-v1-v5.md)
- [System Architecture Overview](./volume-4/01-system-architecture.md)
- [Database ERD](./volume-5/01-erd-overview.md)
- [API Reference](./volume-6/01-api-overview.md)
- [AI Agent Framework](./volume-8/01-ai-architecture-overview.md)
- [Testing Strategy](./volume-12/01-testing-strategy.md)

---

## Engineering Health Status

| Category | Status | Details |
|----------|--------|---------|
| Ruff (Python lint) | ✅ Clean | 0 errors, 0 warnings across `app/` |
| Mypy (type check) | ✅ Core clean | Overrides for missing stubs (jose, passlib, redis) |
| Bandit (SAST) | ✅ High: 0 | 0 high-severity, 6 medium, 15 low |
| CI validator | ✅ All 7/7 PASS | Structure, files, Docker, secrets, configs |
| Docker Compose | ✅ Config valid | `docker compose config` parses clean |
| .gitignore | ✅ Complete | Covers pyc, env, node_modules, .next, terraform, coverage |
| Python version | ✅ 3.11 + 3.12 | Local 3.11 (PEP 695 → Generic[T]), CI 3.12 (native) |

---

## Repository Structure

```
aegis-marketing-cloud/
├── docs/                          ← You are here
│   ├── volume-1/                 Vision & Business
│   ├── volume-2/                 Product Requirements
│   ├── volume-3/                 Software Requirements
│   ├── volume-4/                 System Architecture
│   ├── volume-5/                 Database Design
│   ├── volume-6/                 API Specification
│   ├── volume-7/                 UI/UX Design System
│   ├── volume-8/                 AI Architecture
│   ├── volume-9/                 Workflow & Automation
│   ├── volume-10/                Security & Compliance
│   ├── volume-11/                DevOps & Deployment
│   ├── volume-12/                Testing Strategy
│   ├── volume-13/                Plugin & Marketplace SDK
│   ├── volume-14/                Operations Manual
│   ├── volume-15/                Product Roadmap
│   └── README.md                 This file
├── src/
│   └── (application code — post-specification)
├── tests/
│   └── (test suites — per Volume 12)
├── deployment/
│   └── (Docker, K8s, Terraform — per Volume 11)
└── scripts/
    └── (utility scripts)
```

---

## Documentation Conventions

- **Language:** English (US)
- **Format:** Markdown with Mermaid diagrams where applicable
- **API Spec:** OpenAPI 3.1 (auto-generated from code, formal schema in `docs/volume-6/schemas/`)
- **ERD:** Mermaid ER diagrams in Volume 5
- **Architecture Diagrams:** Mermaid / PlantUML in Volume 4
- **Versioning:** Each volume has its own version history header

---

## How to Use This Documentation

1. **Start with Volume 1** — Understand the vision, market, and business goals
2. **Read Volumes 2–3** — Understand what we're building and why
3. **Study Volumes 4–6** — Understand the architecture, data, and APIs
4. **Reference Volumes 7–9** — When building the UI, AI, or workflows
5. **Consult Volumes 10–14** — For security, deployment, testing, and operations
6. **Track with Volume 15** — The roadmap guides sequencing and prioritization

---

> **"Documentation-first is not about writing more — it's about building smarter. Every page written saves a day of rework."**
