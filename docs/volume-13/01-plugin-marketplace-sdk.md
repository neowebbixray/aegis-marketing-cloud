# Volume 13: Plugin & Marketplace SDK

> **Document Version:** 1.0  
> **Classification:** Internal — Engineering & Ecosystem  
> **Date:** June 2026  
> **Author:** Platform & Ecosystem Team  
> **Status:** ✅ Complete  
> **Applies To:** Aegis Marketing Cloud (AMC) — Marketplace & Plugin SDK

---

## Table of Contents

1. [Ecosystem Philosophy](#1-ecosystem-philosophy)
2. [Marketplace Overview](#2-marketplace-overview)
3. [Developer Onboarding](#3-developer-onboarding)
4. [SDK Architecture](#4-sdk-architecture)
5. [Plugin Manifest](#5-plugin-manifest)
6. [UI Extension Points](#6-ui-extension-points)
7. [Backend Extension Points](#7-backend-extension-points)
8. [Event System](#8-event-system)
9. [Billing & Monetization](#9-billing--monetization)
10. [Plugin Lifecycle](#10-plugin-lifecycle)
11. [Security & Sandboxing](#11-security--sandboxing)
12. [Developer Portal](#12-developer-portal)
13. [SDK Reference (Python)](#13-sdk-reference-python)
14. [SDK Reference (TypeScript/React)](#14-sdk-reference-typescriptreact)
15. [Example Plugins](#15-example-plugins)

---

## 1. Ecosystem Philosophy

### 1.1 Platform + Marketplace = The Flywheel Effect

AMC's marketplace is not a bolt-on storefront — it is a core architectural primitive that creates a **self-reinforcing flywheel**:

```mermaid
graph TD
    A["🔧 More Developers<br/>Build Extensions"] --> B["📦 More Plugins,<br/>Tools & Integrations"]
    B --> C["👥 More Customers<br/>Adopt AMC"]
    C --> D["💰 More Revenue<br/>(Platform + Developers)"]
    D --> E["🛠️ Better SDK,<br/>Docs & Infrastructure"]
    E --> A

    style A fill:#6366f1,color:#fff
    style B fill:#8b5cf6,color:#fff
    style C fill:#a855f7,color:#fff
    style D fill:#d946ef,color:#fff
    style E fill:#ec4899,color:#fff
```

**Mechanism:**

| Driven | Driver | Effect |
|--------|--------|--------|
| Developers | Growing customer base | Larger addressable market for their plugins |
| Customers | Rich plugin ecosystem | Platform becomes indispensable |
| Platform | Plugin revenue share | Resources to improve SDK, infra, and marketplace |
| SDK Quality | Developer feedback + usage data | Better tooling, docs, and extension points |

The flywheel means that every new plugin makes AMC more valuable for every customer, which attracts more customers, which attracts more developers. **Platform and ecosystem grow together or not at all.**

### 1.2 Extensibility Without Compromising Security

The single greatest tension in any extensible platform is **power vs. safety**. AMC resolves this with a layered trust model:

```
┌─────────────────────────────────────────────────┐
│              AMC Platform Core                    │
│  (Database, AI Engine, Workflow, APIs, UI)       │
├─────────────────────────────────────────────────┤
│              Permission Boundary                  │
│  ┌───────────────────────────────────────────┐   │
│  │         Plugin Sandbox Layer               │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │   │
│  │  │Plugin │ │Plugin │ │Plugin │ │Plugin │    │   │
│  │  │  A   │ │  B   │ │  C   │ │  D   │    │   │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘    │   │
│  │     │         │         │         │        │   │
│  │     └─────── AMC SDK (API) ───────┘        │   │
│  └───────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│              Network Egress Filter               │
│        (Only domains declared in manifest)        │
└─────────────────────────────────────────────────┘
```

**Key tenets:**

- **No direct database access** — Plugins interact with data exclusively through the AMC API, which enforces tenant isolation, row-level security, and permission checks on every operation.
- **No raw filesystem access** — Plugins get an ephemeral `/tmp` directory that is destroyed when the plugin process terminates. Persistent storage is provided through the SDK's `Storage` API (key-value, tenant-scoped, encrypted at rest).
- **Network egress is declared, not discovered** — A plugin may only connect to domains listed in its manifest. Any attempt to reach an undeclared host is blocked at the sandbox boundary.
- **Execution is bounded** — Synchronous handlers time out at 30 seconds; async handlers at 5 minutes. Memory is capped at 256 MB per plugin instance.
- **Frontend code runs in isolation** — UI extensions are rendered as web components in Shadow DOM or sandboxed iframes, with no access to the parent page's DOM, cookies, or local storage.

### 1.3 Developers Succeed → Platform Succeeds

This is not a slogan — it is an architectural axiom reflected in every design decision:

- **Revenue share is 70/30 in favor of developers** (industry standard on platforms like Shopify, Stripe, and Salesforce AppExchange is 80/20 or 70/30). AMC's 30% covers hosting, sandboxing, distribution, billing infrastructure, and marketplace operations.
- **Free tier for developers** — Developer accounts cost nothing. There are no listing fees, no annual subscription, and no charge for development sandbox workspaces.
- **API-first design** — The same APIs that power AMC's own UI are available to plugins. Developers are never second-class citizens.
- **No lock-in** — Plugins are distributed as standard Python packages or NPM packages. The SDK is open-source (MIT license). A developer can run their plugin locally, test it in CI, and only submit to the marketplace when ready.

### 1.4 Sandboxed Execution for All Third-Party Code

Every plugin — regardless of whether it's a 10-line prompt template or a complex backend extension with database hooks — runs in an **isolated sandbox**:

```mermaid
graph LR
    subgraph Host["AMC Host Infrastructure"]
        direction TB
        API["API Gateway"]
        DB[("PostgreSQL<br/>(RLS-enforced)")]
        UI["AMC Frontend"]
    end

    subgraph Plugin1["Plugin A Sandbox"]
        P1_PROC["Python Subprocess<br/>(backend)"]
        P1_UI["Web Component<br/>(Shadow DOM)"]
        P1_NET["Network Filter<br/>(allowlist)"]
    end

    subgraph Plugin2["Plugin B Sandbox"]
        P2_PROC["Python Subprocess<br/>(backend)"]
        P2_UI["Web Component<br/>(Shadow DOM)"]
        P2_NET["Network Filter<br/>(allowlist)"]
    end

    Plugin1 -->|"AMC API (scoped token)"| API
    Plugin2 -->|"AMC API (scoped token)"| API
    API --> DB
    P1_UI -->|"PostMessage API"| UI
    P2_UI -->|"PostMessage API"| UI
```

**Isolation layers:**

| Layer | Mechanism |
|-------|-----------|
| Backend runtime | Subprocess (default) or Docker container (for resource-intensive plugins). Each process gets a dedicated OS user with restricted capabilities. |
| Frontend runtime | Web components rendered in Shadow DOM. Communication with the host page is via a strict `postMessage` protocol. |
| Network | iptables/nftables rules per process based on manifest allowlist. DNS resolution is intercepted and validated. |
| Storage | No direct filesystem beyond `/tmp`. Persistent data goes through the SDK `Storage` API, which encrypts values with a plugin-specific key. |
| Database | No database connection pool. All data access is through the AMC REST API, which applies tenant RLS and permission checks. |

### 1.5 API-First — Extensions Are Just API Consumers

AMC treats plugins as **privileged API consumers**, not as embedded code. This distinction is fundamental:

- **A plugin is a program that calls AMC APIs.** It does not import internal modules, share memory, or access unexported functions.
- **The SDK is a strongly-typed API client.** It provides convenience wrappers, authentication context, and event subscriptions — but every operation goes through the public API.
- **This means plugins are language-agnostic in principle.** While AMC provides first-party SDKs in Python (backend) and TypeScript (frontend), any HTTP client can interact with the marketplace and plugin APIs. A plugin could be written in Go, Rust, or even as a shell script.
- **The API contract is the stability guarantee.** As long as the API does not break, plugins continue to work. AMC follows [SemVer](https://semver.org/) for all API changes, with breaking changes signaled 12+ months in advance via the `Sunset` and `Deprecation` headers.

---

## 2. Marketplace Overview

### 2.1 Listing Types

The AMC Marketplace supports nine distinct listing types, each targeting a different extension modality:

| Type | Description | Runtime | Example |
|------|-------------|---------|---------|
| **AI Agents** | Custom agent roles with specialized behaviors, prompts, and tool access | AI Layer (Hermes) | "Customer Support Agent," "SEO Audit Agent" |
| **Tools** | Individual tools that AI agents can invoke | AI Layer (function call) | "Web Scraper Tool," "PDF Generator Tool" |
| **Extensions** | Serverless backend logic triggered by events or API calls | Backend Sandbox | "Webhook to Slack Relay" |
| **Prompts** | Curated prompt libraries for AI agents | AI Layer (prompt store) | "Brand Voice Prompts," "A/B Copy Generator" |
| **Templates** | Standalone n8n workflow templates | n8n Engine | "Welcome Email Sequence," "Lead Scoring" |
| **Workflows** | Multi-step n8n workflow bundles with dependencies | n8n Engine | "Full Sales Funnel Automation" |
| **Plugins** | Full-featured extensions with UI components + backend logic | Full sandbox (frontend + backend) | "Slack Integration Plugin" |
| **Integrations** | Connectors to external services via OAuth/API key | Backend Sandbox | "Google Analytics Connector," "Shopify Sync" |
| **Themes** | Custom branding packages (colors, typography, logos) | Frontend (CSS variables) | "Dark Mode Pro," "Agency White-Label" |

#### 2.1.1 AI Agents

AI Agents are the most powerful extension type — they define a complete agent persona with:

- **System prompt** — The base instructions that define the agent's role, tone, and knowledge
- **Tool access** — Which platform tools (and optionally custom tools) the agent can invoke
- **Guardrails** — Topics to avoid, content policies, escalation rules
- **Memory configuration** — How the agent retains context across conversations
- **Entry triggers** — How the agent is invoked (slash command, mention, event, scheduled)

```yaml
# manifest.yaml for an AI Agent
id: com.acme.support-agent
name: Customer Support Agent
version: 2.1.0
type: ai-agent
description: Handles tier-1 customer support inquiries with empathy and accuracy
author: Acme Corp
icon: support-agent.svg

agent:
  system_prompt: |
    You are a helpful customer support agent for {workspace.name}.
    Your knowledge base includes:
    - Product documentation (from workspace knowledge base)
    - Known issues and resolutions
    - Company policies on refunds and returns
    
    Always:
    - Be empathetic and professional
    - Ask clarifying questions if the issue is ambiguous
    - Escalate to human support if you cannot resolve
  tools:
    - crm:contact:read
    - knowledge:search
    - ticket:create
    - ticket:update
  guardrails:
    avoid_topics:
      - pricing negotiations
      - legal advice
      - medical advice
    escalation:
      condition: user requests human or sentiment < -0.5
      action: create_ticket + notify_support_team
  memory:
    type: conversation
    retention_days: 90
  triggers:
    - type: mention
      pattern: "@support"
    - type: event
      event: ticket.created
      handler: offer_assistance
```

#### 2.1.2 Tools

Tools are standalone functions that AI agents can invoke. Each tool has:

- **Name and description** — Used by the AI to decide when to call the tool
- **Input schema** — JSON Schema defining the parameters
- **Output schema** — JSON Schema for the return value
- **Implementation** — Python function or external API call
- **Rate limits** — Maximum invocations per minute per workspace

```yaml
# manifest.yaml for a Tool
id: com.acme.url-shortener
name: URL Shortener
version: 1.0.0
type: tool
description: Shortens URLs using the Acme shortener service

tool:
  input:
    type: object
    properties:
      url:
        type: string
        format: uri
        description: The URL to shorten
      custom_slug:
        type: string
        description: Optional custom slug
    required:
      - url
  output:
    type: object
    properties:
      short_url:
        type: string
        format: uri
      expires_at:
        type: string
        format: date-time
  implementation:
    type: api
    url: https://api.acme.com/shorten
    method: POST
    auth:
      type: api-key
      header: X-API-Key
```

#### 2.1.3 Extensions

Extensions are pure backend logic — no UI components — that react to events or serve as webhook receivers. They are the most lightweight plugin type.

```yaml
# manifest.yaml for an Extension
id: com.acme.log-archiver
name: Log Archiver
version: 1.2.0
type: extension
description: Archives audit logs older than 90 days to S3-compatible storage

backend:
  entry: archiver.py
  type: python
  timeout: 300
  memory: 128

hooks:
  - event: schedule.daily
    handler: archive_old_logs

network:
  allow:
    - s3.amazonaws.com
    - api.acme-archive.com
```

#### 2.1.4 Prompts

Prompts are shareable instruction libraries that can be imported into any AI agent configuration. They are the simplest listing type — no backend, no UI, just curated text.

```yaml
# manifest.yaml for a Prompt Library
id: com.acme.brand-voice
name: Brand Voice Prompts
version: 3.0.0
type: prompts
description: A library of brand voice guidelines for marketing copy generation
author: Acme Corp

prompts:
  - id: professional-tone
    name: Professional Tone
    content: |
      Write in a professional, authoritative tone suitable for B2B communications.
      Use industry-specific terminology where appropriate.
      Avoid slang, exclamation marks, and overly casual language.
    variables:
      - audience
      - industry
  - id: friendly-tone
    name: Friendly & Approachable
    content: |
      Write in a warm, friendly tone that makes the reader feel welcome.
      Use contractions and conversational language.
      Be encouraging and positive.
    variables:
      - product_name
      - audience
  - id: urgent-cta
    name: Urgent Call-to-Action
    content: |
      Create a sense of urgency without being alarmist.
      Use time-sensitive language and clear action verbs.
      Include specific deadlines or limited availability.
    variables:
      - offer
      - deadline
```

#### 2.1.5 Templates & Workflows

Templates are individual n8n workflow JSON files. Workflows are bundles of multiple interconnected workflows that share state and configuration.

```yaml
# manifest.yaml for a Workflow Bundle
id: com.acme.lead-nurture
name: Lead Nurture Workflow Bundle
version: 2.0.0
type: workflows
description: Complete lead nurture system with scoring, email sequences, and handoff
author: Acme Corp

workflows:
  - id: lead-scoring
    file: workflows/lead-scoring.json
    description: Scores leads based on engagement and demographic data
    triggers:
      - crm.contact.created
      - crm.contact.updated
  - id: email-nurture
    file: workflows/email-nurture.json
    description: Sends a 5-email nurture sequence to warm leads
    triggers:
      - event: hook.lead_scored
        from_workflow: lead-scoring
  - id: sales-handoff
    file: workflows/sales-handoff.json
    description: Creates a sales task when a lead reaches threshold score
    triggers:
      - event: hook.lead_qualified
        from_workflow: email-nurture

configuration:
  - key: lead_threshold_score
    type: number
    default: 80
    description: Score at which a lead is handed to sales
  - key: nurture_email_from
    type: string
    default: noreply@company.com
    description: From address for nurture emails
```

#### 2.1.6 Plugins (Full Extensions)

Plugins are the most comprehensive extension type, combining UI components, backend logic, event hooks, and storage into a single package. The rest of this document focuses primarily on Plugins, as they encompass the full surface area of the SDK.

#### 2.1.7 Integrations

Integrations are connectors to external services. They handle authentication (OAuth, API keys), webhook registration, and data synchronization.

```yaml
# manifest.yaml for an Integration
id: com.acme.google-analytics
name: Google Analytics Connector
version: 1.5.0
type: integration
description: Syncs Google Analytics 4 data into AMC reports and dashboards
author: Acme Corp

integration:
  auth:
    type: oauth2
    provider: google
    scopes:
      - https://www.googleapis.com/auth/analytics.readonly
    redirect_uri: https://marketplace.amc.io/oauth/callback
  sync:
    - type: scheduled
      frequency: hourly
      handler: sync_analytics_data
    - type: webhook
      from: google
      handler: handle_realtime_event
  data_mappings:
    - source: ga4.sessions
      target: amc.analytics.page_views
      transform: transform_ga4_session
    - source: ga4.events
      target: amc.analytics.events
      transform: transform_ga4_event
```

#### 2.1.8 Themes

Themes customize the visual appearance of AMC workspaces. They are pure CSS/CSS custom property overrides with optional assets (fonts, logos, icons).

```yaml
# manifest.yaml for a Theme
id: com.acme.dark-pro
name: Dark Mode Pro
version: 2.0.0
type: theme
description: Professional dark theme with custom accent colors
author: Acme Corp

theme:
  variables:
    # Base colors
    --color-bg-primary: "#0f172a"
    --color-bg-secondary: "#1e293b"
    --color-bg-tertiary: "#334155"
    --color-text-primary: "#f1f5f9"
    --color-text-secondary: "#94a3b8"
    --color-accent: "#6366f1"
    --color-accent-hover: "#818cf8"
    # Typography
    --font-family-primary: "'Inter', sans-serif"
    --font-family-mono: "'JetBrains Mono', monospace"
    # Spacing
    --radius-sm: "6px"
    --radius-md: "8px"
    --radius-lg: "12px"
  assets:
    - logo-dark.svg
    - favicon.ico
  preview: preview-dark.png
```

### 2.2 Marketplace Tiers

Listings can be offered under four pricing tiers:

| Tier | Description | AMC Commission | Example |
|------|-------------|---------------|---------|
| **Free** | No charge to users | N/A | Open-source integrations, prompt libraries |
| **One-time Purchase** | Single payment for perpetual use | 30% | Theme packs, tool licenses |
| **Subscription** | Monthly or yearly recurring | 30% | SaaS-like plugins (Slack integration, analytics) |
| **Usage-based** | Pay per API call, AI credit, active contact, etc. | 30% | AI tools, data enrichment services |

**Pricing ranges:**

| Tier | Min Price | Max Price | Recommended |
|------|-----------|-----------|-------------|
| Free | $0 | $0 | Adopted open-source, community tools |
| One-time | $4.99 | $499.99 | Themes, prompt packs, templates |
| Subscription | $4.99/mo | $999.99/mo | Active integrations, plugins with server costs |
| Usage-based | $0.001/unit | $0.50/unit | AI tools, API wrappers, data services |

### 2.3 Developer Revenue Share

```
Revenue Flow:
┌─────────┐     ┌──────────────┐     ┌──────────────┐
│ Customer │────▶│ AMC Platform │────▶│  Developer   │
│  Pays    │     │ (Processes)  │     │  (Receives)  │
│  $10.00  │     │              │     │    $7.00     │
└─────────┘     │ Keeps: $3.00 │     └──────────────┘
                │ (30% + fees) │
                └──────────────┘
```

- **Revenue split:** 70% developer, 30% AMC
- **Payment processing fees:** Included in AMC's 30% (Stripe fees are not passed through to developers)
- **Withholding:** AMC withholds applicable taxes (VAT, GST, sales tax) before remitting developer share
- **Minimum payout:** $50.00 (accumulated earnings below this carry over to the next month)
- **Payout schedule:** Net-30, paid on the 15th of the following month via Stripe Connect, PayPal, or direct bank transfer (ACH/SWIFT)
- **Currency:** All listings priced in USD; payouts in USD unless otherwise agreed

### 2.4 Listing Review Process

Every listing submission goes through a multi-stage review process:

```mermaid
flowchart LR
    A["Developer<br/>Submits"] --> B{"Automated<br/>Scan"}
    B -->|"Pass"| C{"Manual<br/>Review"}
    B -->|"Fail"| D["Rejected<br/>(with reason)"]
    C -->|"Approve"| E["Published"]
    C -->|"Changes<br/>Requested"| F["Developer<br/>Revises"]
    C -->|"Reject"| D
    F --> B
    D --> G["Developer<br/>Notified"]
    E --> H["Available in<br/>Marketplace"]
```

| Stage | What's Checked | Time Target | Automated? |
|-------|---------------|-------------|------------|
| **Static analysis** | Malware signatures, hardcoded secrets, dependency vulnerabilities, code quality | < 2 minutes | ✅ Yes |
| **Sandbox execution** | Plugin starts correctly, declares permissions match actual usage, no unexpected network calls | < 10 minutes | ✅ Yes |
| **UI rendering** | UI extensions render without errors in test workspace | < 5 minutes | ✅ Yes |
| **Permissions audit** | Requested permissions match documented functionality | < 15 minutes | ✅ Yes |
| **Manual review** | UX quality, documentation, compliance with marketplace policies, appropriate pricing | 1–3 business days | ❌ No |
| **Security review** | Any plugin requesting sensitive permissions (PII access, financial data) gets additional scrutiny | 1–5 business days | ❌ No |

**Review SLAs:**

| Listing Type | Auto Review | Manual Review (target) |
|-------------|-------------|----------------------|
| Prompts, Themes | ✅ Pass/Fail | 24 hours |
| Templates | ✅ Pass/Fail | 24 hours |
| Tools, Extensions | ✅ Pass/Fail | 48 hours |
| Integrations | ✅ Pass/Fail | 3 business days |
| AI Agents | ✅ Pass/Fail | 5 business days |
| Plugins | ✅ Pass/Fail | 5 business days |
| Workflows | ✅ Pass/Fail | 3 business days |

### 2.5 Versioning and Update Policy

AMC follows strict semantic versioning for both the platform and all marketplace listings.

| Version Component | When to Bump | User Impact |
|------------------|--------------|-------------|
| **Patch (1.0.x)** | Bug fixes, security patches, performance improvements | Auto-updated (no user action needed) |
| **Minor (1.x.0)** | New features, new UI components, new event handlers | Opt-in update (user notified, can upgrade at convenience) |
| **Major (x.0.0)** | Breaking changes, removed APIs, changed data models | Manual upgrade required; developer must publish migration guide |

**Update flow:**

1. Developer uploads new version to marketplace (starts review process)
2. Review process repeats (automated + manual)
3. Upon approval, the new version is available in the marketplace
4. Existing users receive a notification (in-app + email)
5. Patch updates install automatically; minor updates require user approval; major updates require explicit upgrade with migration confirmation
6. Developer can set a **minimum supported version** — users on older versions are prompted to upgrade
7. After **3 major versions** of deprecation, the oldest version is retired (removed from installation, existing installs continue but support ends)

**Version compatibility:** The manifest includes a `min_amc_version` field that declares the minimum AMC platform version required. The marketplace enforces this at install time.

---

## 3. Developer Onboarding

### 3.1 Developer Account Registration

Any authenticated AMC user can become a marketplace developer. The process is self-serve:

1. **Navigate to** `Settings → Developer → Register as Developer`
2. **Accept the Developer Agreement** (see Section 3.5)
3. **Complete your developer profile** (see Section 3.2)
4. **Generate API keys** (see Section 3.3)
5. **Access your sandbox workspace** (see Section 3.4)

Registration is **free** — there are no fees to join the developer program. Developers only pay the standard AMC subscription for their workspace.

### 3.2 Developer Profile

Every developer has a public-facing profile that appears on marketplace listings:

```json
{
  "developer_id": "dev_acme_corp",
  "public_name": "Acme Corp",
  "bio": "Enterprise integration specialists since 2015. We build connectors that just work.",
  "website": "https://acme-corp.com",
  "support_email": "support@acme-corp.com",
  "support_url": "https://acme-corp.com/support",
  "logo_url": "https://marketplace.amc.io/devs/acme/logo.svg",
  "social_links": {
    "github": "https://github.com/acme-corp",
    "twitter": "https://twitter.com/acme-corp",
    "discord": "https://discord.gg/acme"
  },
  "published_listings": 12,
  "total_installs": 45231,
  "average_rating": 4.7,
  "member_since": "2026-01-15"
}
```

**Profile fields:**

| Field | Required | Public? | Description |
|-------|----------|---------|-------------|
| `public_name` | ✅ Yes | ✅ Yes | Display name on listings (can be company name or personal name) |
| `bio` | ✅ Yes | ✅ Yes | Max 500 characters describing your development focus |
| `website` | ❌ No | ✅ Yes | Your company or personal website |
| `support_email` | ✅ Yes | ✅ Yes | Where users send support requests |
| `support_url` | ❌ No | ✅ Yes | Support portal or knowledge base URL |
| `logo_url` | ❌ No | ✅ Yes | Square logo, min 256x256, SVG or PNG |
| `social_links` | ❌ No | ✅ Yes | Optional social media profiles |

### 3.3 API Key Generation

Developers generate **scoped API keys** from the Developer Portal. These keys are different from regular AMC API keys — they carry marketplace-specific permissions:

| Scope | Description | Included by Default? |
|-------|-------------|---------------------|
| `marketplace:plugins:read` | List and read plugin manifest details | ✅ Yes |
| `marketplace:plugins:write` | Create, update, delete own plugins | ✅ Yes |
| `marketplace:plugins:publish` | Submit plugins for review and publish | ✅ Yes |
| `marketplace:analytics:read` | View install and revenue analytics | ✅ Yes |
| `marketplace:developer:read` | Read developer profile | ✅ Yes |
| `marketplace:developer:write` | Update developer profile | ✅ Yes |
| `sandbox:workspace:manage` | Manage sandbox workspace settings | ✅ Yes |
| `sandbox:execution:logs` | View sandbox execution logs | ✅ Yes |

**Key types:**

| Key Type | Use Case | Expiry | Rate Limit |
|----------|----------|--------|------------|
| **Development Key** | Local development and testing | 90 days (renewable) | 100 req/min |
| **CI/CD Key** | Automated testing in CI pipelines | 1 year | 500 req/min |
| **Deployment Key** | Production deployment (marketplace internal) | 2 years | 10,000 req/min |

```python
# Example: Using an API key with the AMC SDK
from amc_sdk import AMCClient

client = AMCClient(
    api_key="amc_dev_xxxxxxxxxxxxxxxx",
    workspace_id="ws_xxxxxxxx",
    environment="sandbox"  # or "production"
)

# List all your plugins
plugins = client.marketplace.plugins.list()
```

### 3.4 Sandbox/Test Workspace

Every developer automatically gets a **sandbox workspace** — an isolated AMC environment with:

- **Full platform access** — All AMC modules (CRM, Marketing, Projects, Knowledge, AI)
- **Synthetic data** — Pre-populated with test contacts, campaigns, templates, and analytics
- **No outbound email** — Email sends are intercepted and logged, not delivered
- **No AI credit costs** — AI operations in the sandbox are free
- **Plugin debug mode** — Extended logging, runtime introspection, hot reload
- **Shared with team members** — Up to 5 additional developer seats per sandbox

**Sandbox limits:**

| Resource | Limit |
|----------|-------|
| Contacts | 10,000 |
| Campaigns | 100 |
| Active workflows | 20 |
| Storage (KV) | 100 MB |
| API calls per day | 50,000 |
| Concurrent plugin instances | 5 |
| Log retention | 30 days |

### 3.5 Developer Agreement

Before publishing any listing, developers must accept the **AMC Marketplace Developer Agreement**. Key terms:

| Clause | Summary |
|--------|---------|
| **License Grant** | Developer grants AMC a non-exclusive, royalty-free license to distribute, display, and sublicense the plugin through the marketplace |
| **Revenue Share** | 70% developer / 30% AMC on all paid transactions. AMC may adjust the split with 90 days notice |
| **Intellectual Property** | Developer retains full IP ownership of their plugin. AMC owns the marketplace, SDK, and platform |
| **Warranties** | Developer warrants that their plugin does not infringe third-party IP, contains no malware, and complies with all applicable laws |
| **Liability** | Developer is liable for damages caused by their plugin. AMC's liability is capped at the total revenue share paid to the developer in the preceding 12 months |
| **Termination** | Either party may terminate with 30 days notice. AMC may terminate immediately for security violations or TOS breaches |
| **Data Privacy** | Plugins must not transmit user data to unauthorized third parties. GDPR and CCPA compliance is required for plugins processing EU or California user data |
| **Indemnification** | Developer indemnifies AMC against third-party claims arising from the plugin |
| **Updates** | Developer must provide security updates for published plugins within a reasonable timeframe |
| **Appeals** | Rejected listings and terminations can be appealed to the Marketplace Review Board |

### 3.6 Documentation and Getting-Started Guide

New developers are guided through their first plugin with an interactive tutorial:

1. **SDK Installation** — `pip install amc-sdk` or `npm install @amc/sdk`
2. **Plugin Scaffolding** — `amc plugin init my-plugin` (creates project structure)
3. **Manifest Configuration** — Guided editor for `plugin.yaml`
4. **Local Development** — `amc dev run` (starts local dev server with hot reload)
5. **Sandbox Deployment** — `amc sandbox deploy` (deploys to sandbox workspace)
6. **Testing** — `amc test` (runs automated tests in sandbox)
7. **Submission** — `amc marketplace submit` (packages and submits for review)

---

## 4. SDK Architecture

### 4.1 SDK Languages

AMC provides first-party SDK coverage for:

| Language | Purpose | Package | Support Level |
|----------|---------|---------|---------------|
| **Python 3.11+** | Backend plugin logic, event handlers, API client | `amc-sdk` (PyPI) | ✅ Full support |
| **TypeScript 5.x** | Frontend UI extensions, React components | `@amc/sdk` (npm) | ✅ Full support |
| **REST API** | Any language with HTTP | OpenAPI 3.1 spec | ✅ Full support |

Third-party SDKs (community-maintained):
- Go (`github.com/amc/sdk-go`) — Community
- Rust (`crates.io/amc-sdk`) — Community

### 4.2 SDK Core Capabilities

```mermaid
graph TD
    SDK["AMC SDK Core"]
    
    SDK --> Auth["Authentication<br/>Context-Inherited"]
    SDK --> API["API Client<br/>Typed Endpoints"]
    SDK --> Events["Event System<br/>Subscribe & Handle"]
    SDK --> UI["UI Extensions<br/>React Components"]
    SDK --> Storage["Storage API<br/>KV per Installation"]
    SDK --> Billing["Billing Metering<br/>Usage Reporting"]
    SDK --> Logging["Logging API<br/>Structured JSON"]
    SDK --> Webhook["Webhook Receiver<br/>External Callbacks"]
    SDK --> Models["Data Models<br/>Typed Entities"]
    SDK --> Scheduler["Scheduler<br/>Cron Tasks"]

    Auth --> API
    API --> Models
    Events --> Webhook
    Scheduler --> Events
```

#### 4.2.1 Authentication (Context-Inherited)

Plugins never handle authentication directly. The SDK inherits the authenticated context of the user who installed the plugin:

- **For UI extensions:** The user's session is automatically propagated. API calls made from the plugin's frontend component use the current user's permissions.
- **For backend event handlers:** The system context (tenant, workspace, system user) is provided by the SDK. Handlers run with the permissions granted to the plugin at install time.
- **For webhook receivers:** Authentication of the external caller is the webhook's responsibility (API key, signature verification). Once verified, the handler runs with plugin-scoped permissions.

```python
# Backend SDK — context is automatically available
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    def on_activate(self):
        # Context is already set before any handler runs
        tenant_id = self.context.tenant_id
        workspace_id = self.context.workspace_id
        user_id = self.context.user_id
        locale = self.context.locale
        timezone = self.context.timezone
        self.logger.info(f"Plugin activated in workspace {workspace_id}")
```

```typescript
// Frontend SDK — context via hooks
import { useAmcPlugin } from '@amc/sdk';

function MyWidget() {
    const { context, api, currentUser } = useAmcPlugin();
    // context.tenant_id, context.workspace_id, context.locale
    // currentUser.id, currentUser.email, currentUser.role
}
```

#### 4.2.2 Tenant/Workspace Context

The SDK provides access to the full context of the current operation:

| Context Property | Type | Description |
|-----------------|------|-------------|
| `tenant_id` | `str` | The tenant (organization) ID |
| `workspace_id` | `str` | The workspace ID within the tenant |
| `user_id` | `str` | The current user ID (may be system user for event handlers) |
| `user_email` | `str` | The current user's email |
| `user_role` | `str` | The current user's role within the workspace |
| `locale` | `str` | IETF language tag (e.g., `en-US`, `de-DE`, `ja-JP`) |
| `timezone` | `str` | IANA timezone (e.g., `America/New_York`, `Europe/Berlin`) |
| `installation_id` | `str` | Unique ID of this plugin installation |
| `plugin_version` | `str` | Version string of the installed plugin |

#### 4.2.3 AMC API Client

The SDK exposes a fully typed API client that covers every public AMC endpoint:

```python
# Python SDK — typed API client
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def on_contact_created(self, event):
        # CRM
        contact = await self.api.crm.contacts.get(event.data.contact_id)
        all_contacts = await self.api.crm.contacts.list(
            limit=100,
            filters={"status": "active"}
        )
        new_contact = await self.api.crm.contacts.create({
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        })
        updated = await self.api.crm.contacts.update(
            contact_id="c_123",
            data={"tags": ["lead", "webinar"]}
        )

        # Marketing
        campaign = await self.api.marketing.campaigns.get("camp_456")
        await self.api.marketing.campaigns.send(campaign_id="camp_456")

        # Projects
        tasks = await self.api.projects.tasks.list(project_id="proj_789")

        # Knowledge
        docs = await self.api.knowledge.documents.search(query="brand guidelines")

        # AI
        completion = await self.api.ai.complete(
            prompt="Write a marketing email for...",
            model="hermes-4",
            temperature=0.7
        )

        # Automation (n8n)
        workflow = await self.api.automation.workflows.get("wf_001")
        execution = await self.api.automation.workflows.execute("wf_001", {
            "contact_id": contact.id
        })

        # Analytics
        report = await self.api.analytics.reports.create({
            "type": "campaign_performance",
            "campaign_id": "camp_456"
        })
```

The TypeScript SDK mirrors the same API surface:

```typescript
// TypeScript SDK — typed API client
import { useAmcApi } from '@amc/sdk';

function CampaignDetail() {
    const api = useAmcApi();

    useEffect(() => {
        async function load() {
            // Typed response
            const contacts = await api.crm.contacts.list({
                limit: 50,
                filters: { status: 'active' }
            });
            // contacts: { items: Contact[], total: number, page: number }

            const campaign = await api.marketing.campaigns.get('camp_456');
            // campaign: Campaign
        }
        load();
    }, []);
}
```

**API client capabilities:**

| Feature | Description |
|---------|-------------|
| **Typed requests/responses** | Full TypeScript types and Python dataclasses for all entities |
| **Automatic pagination** | `.list()` returns an async iterator that auto-paginates |
| **Idempotency keys** | Automatic retry with idempotency for mutating requests |
| **Rate limit awareness** | Client auto-throttles when approaching rate limits |
| **Request/response logging** | Structured logs for every API call (controlled by log level) |
| **Timeout configuration** | Configurable per-call timeout (default: 30s) |
| **Bulk operations** | Batch create/update/delete for supported entities |

#### 4.2.4 Event Hook System

Plugins subscribe to AMC events and provide handler functions. The SDK manages the subscription lifecycle:

```python
# Python SDK — event hooks
from amc_sdk import AmcPlugin, event_handler

class MyPlugin(AmcPlugin):
    @event_handler("crm.contact.created")
    async def on_contact_created(self, event):
        contact = event.data
        self.logger.info(f"New contact: {contact.email}")
        # Do something with the new contact

    @event_handler("campaign.sent")
    async def on_campaign_sent(self, event):
        campaign = event.data
        self.logger.info(f"Campaign sent: {campaign.name}")
```

```typescript
// TypeScript SDK — event hooks
import { useAmcEvent } from '@amc/sdk';

function ContactActivity() {
    useAmcEvent('crm.contact.created', async (event) => {
        console.log('New contact:', event.data.email);
        // Update UI
    });

    useAmcEvent('campaign.sent', async (event) => {
        console.log('Campaign sent:', event.data.name);
    });
}
```

#### 4.2.5 Data Model Access

The SDK provides typed CRUD operations for all AMC data models. Each entity type has a dedicated repository with methods for create, read, update, delete, list, search, and count.

**Available entity types (non-exhaustive):**

| Module | Entity Types |
|--------|-------------|
| CRM | `Contact`, `Company`, `Deal`, `Lead`, `Note`, `Activity`, `List`, `Segment` |
| Marketing | `Campaign`, `Email`, `Template`, `LandingPage`, `Form`, `CTA`, `Audience` |
| Projects | `Project`, `Task`, `Milestone`, `Timesheet`, `Attachment`, `Comment` |
| Knowledge | `Document`, `Article`, `Category`, `FAQ`, `GlossaryTerm` |
| Analytics | `Report`, `Dashboard`, `Metric`, `Dimension`, `Segment` |
| Automation | `Workflow`, `Execution`, `Trigger`, `Action`, `Log` |
| Settings | `Workspace`, `User`, `Role`, `Permission`, `Integration` |

#### 4.2.6 UI Extension Points

The SDK provides a registration system that lets plugins inject UI components into predefined locations in the AMC interface. See [Section 6](#6-ui-extension-points) for the full reference.

#### 4.2.7 Storage API

Each plugin installation gets a dedicated key-value store:

```python
# Python SDK — Storage API
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Storage is persistent, tenant-scoped, and encrypted at rest
        await self.storage.set("api_key", "sk-xxx...")
        await self.storage.set("webhook_url", "https://hooks.example.com/callback")

        api_key = await self.storage.get("api_key")  # "sk-xxx..."
        all_keys = await self.storage.keys()  # ["api_key", "webhook_url"]

        await self.storage.delete("temporary_key")

        # Storage with TTL (auto-expire)
        await self.storage.set("temp_token", "abc123", ttl_seconds=3600)
```

```typescript
// TypeScript SDK — Storage API
import { useAmcPlugin } from '@amc/sdk';

function SettingsPanel() {
    const { storage } = useAmcPlugin();
    const [apiKey, setApiKey] = useState('');

    useEffect(() => {
        storage.get('api_key').then(setApiKey);
    }, []);

    const saveApiKey = async () => {
        await storage.set('api_key', apiKey);
    };
}
```

**Storage limitations:**

| Property | Limit |
|----------|-------|
| Max key length | 256 characters |
| Max value size | 64 KB per key |
| Total storage per installation | 10 MB |
| Max keys per installation | 1,000 |
| TTL max | 365 days |

#### 4.2.8 Billing Metering API

For usage-based pricing, plugins report usage metrics:

```python
# Python SDK — Billing Metering API
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def process_data(self, data):
        # Process the data...
        result = await self.do_something(data)

        # Report usage for billing
        await self.billing.report(
            metric="api_calls",
            value=1,
            metadata={"endpoint": "/process", "data_size": len(data)}
        )

        await self.billing.report(
            metric="ai_credits",
            value=result.credits_used
        )

        # Report multiple metrics in batch
        await self.billing.report_batch([
            {"metric": "api_calls", "value": 1},
            {"metric": "storage_mb", "value": 0.5},
        ])

        return result
```

#### 4.2.9 Logging API

All plugin logging is structured, tenant-tagged, and emitted to the AMC observability pipeline:

```python
# Python SDK — Logging API
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def on_contact_created(self, event):
        self.logger.debug("Processing new contact", extra={
            "contact_id": event.data.contact_id,
            "source": event.data.source,
        })

        try:
            result = await self.api.crm.contacts.get(event.data.contact_id)
            self.logger.info("Contact retrieved successfully",
                           extra={"contact_id": result.id, "email": result.email})
        except Exception as e:
            self.logger.error("Failed to retrieve contact",
                            extra={"contact_id": event.data.contact_id, "error": str(e)},
                            exc_info=True)

        # Structured logging with severity levels
        self.logger.critical("Component failure - manual intervention required")
```

**Log levels and retention:**

| Level | Usage | Retention |
|-------|-------|-----------|
| `DEBUG` | Development diagnostics | 7 days |
| `INFO` | Normal operation events | 30 days |
| `WARNING` | Unexpected but handled conditions | 90 days |
| `ERROR` | Operation failures requiring attention | 90 days |
| `CRITICAL` | Component failures, data corruption risks | 365 days |

#### 4.2.10 Webhook Receiver

Plugins can register custom HTTP endpoints that external services can call:

```python
# Python SDK — Webhook Receiver
from amc_sdk import AmcPlugin, webhook

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Register webhook endpoints
        self.register_webhook("/slack/events", self.handle_slack_event)
        self.register_webhook("/github/push", self.handle_github_push)

    async def handle_slack_event(self, request):
        # Verify Slack signature
        if not self.verify_slack_signature(request):
            return {"status": "unauthorized"}, 401

        payload = request.json()
        self.logger.info("Received Slack event", extra={"type": payload.get("type")})

        # Process the event
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            await self.process_slack_event(event)

        return {"status": "ok"}

    async def handle_github_push(self, request):
        # Verify GitHub webhook secret
        signature = request.headers.get("X-Hub-Signature-256")
        if not self.verify_github_signature(request.body, signature):
            return {"status": "unauthorized"}, 401

        payload = request.json()
        self.logger.info("Received GitHub push event",
                        extra={"repository": payload.get("repository", {}).get("full_name")})
        return {"status": "ok"}
```

### 4.3 SDK Security

#### 4.3.1 No Raw Database Access

Plugins cannot open database connections. The only way to read or write data is through the AMC API client provided by the SDK. This ensures:

- **Tenant isolation** — Every API call is scoped to the plugin's installation tenant
- **Permission enforcement** — The API checks whether the plugin has the required permissions for each operation
- **Audit logging** — Every data access is logged with the plugin ID, user ID, and operation
- **Rate limiting** — API calls are subject to per-plugin rate limits

#### 4.3.2 No Filesystem Access (Except Ephemeral Temp)

Plugins receive a temporary directory at `/tmp/amc-plugin-{installation_id}` that:

- Is created when the plugin process starts
- Is writable (unlike the rest of the filesystem)
- Is automatically cleaned up when the process terminates
- Has a 256 MB size limit
- Is NOT backed up
- Is NOT accessible from other plugin instances

```python
# Python SDK — Temp directory usage
from amc_sdk import AmcPlugin
import os

class MyPlugin(AmcPlugin):
    async def generate_report(self):
        temp_dir = os.environ.get("AMC_TEMP_DIR", "/tmp")
        report_path = os.path.join(temp_dir, "report.pdf")
        
        # Write temporary file
        with open(report_path, "wb") as f:
            f.write(self.generate_pdf_content())
        
        # Upload to storage (persistent)
        await self.api.storage.upload("reports/report.pdf", report_path)
        
        # Temp file is cleaned up automatically
```

#### 4.3.3 Network Access Restricted to Allowed Domains

The plugin manifest declares which external domains the plugin may connect to. The sandbox enforces this at multiple levels:

```yaml
# plugin.yaml — Network allowlist
network:
  allow:
    - api.acme-corp.com          # Specific hostname
    - *.acme-corp.com            # Wildcard subdomains
    - api.stripe.com             # Payment processing
    - hooks.slack.com            # Slack webhooks
    - storage.googleapis.com     # Cloud storage
  block:                         # Explicitly blocked (overrides wildcards)
    - evil.acme-corp.com
```

**Network enforcement:**

| Layer | Enforcement |
|-------|-------------|
| **DNS** | Plugin's DNS resolver only resolves allowed domains. Any DNS query for a non-allowed domain returns NXDOMAIN. |
| **TCP/UDP** | iptables/nftables rules per process PID. Only allowed destinations can be reached. |
| **HTTP** | If the plugin uses the SDK's HTTP client, enforcement is double-checked at the application layer. |
| **TLS** | Certificate pinning can be required for high-security plugins. |

#### 4.3.4 Execution Timeout

| Handler Type | Timeout | After Timeout |
|-------------|---------|---------------|
| Synchronous (event handler, webhook) | 30 seconds | Process is SIGKILLed; event is marked as failed |
| Asynchronous (scheduled task, long-running) | 5 minutes | Process is SIGKILLed; task is marked as failed |
| UI component (initial render) | 10 seconds | Component is replaced with error placeholder |

#### 4.3.5 Memory Limit

Each plugin instance is limited to **256 MB** of RAM. Exceeding this:

1. At 80% (≈205 MB), the SDK emits a `memory.warning` log event
2. At 95% (≈243 MB), the SDK attempts a graceful shutdown of the current operation
3. At 100% (256 MB), the process is SIGKILLed

---

## 5. Plugin Manifest

### 5.1 Manifest Format

Plugins can use either YAML (`plugin.yaml`) or JSON (`manifest.json`). AMC recommends YAML for readability.

### 5.2 Full Schema

```yaml
# plugin.yaml — Complete manifest example
id: com.example.my-plugin
name: My Plugin
version: 1.0.0
type: plugin                                # See listing types in §2.1
description: Does something useful
author: Example Corp
icon: icon.svg

# Version compatibility
min_amc_version: "1.2.0"
max_amc_version: "2.0.0"                   # Optional: cap at next major

# Categories and discovery
categories:
  - productivity
  - communication
tags:
  - slack
  - notifications
  - collaboration

# Screenshots for marketplace listing
screenshots:
  - src: screenshots/dashboard-widget.png
    alt: Dashboard widget showing recent notifications
  - src: screenshots/settings-page.png
    alt: Plugin configuration page

# Dependencies on other plugins
dependencies:
  - id: com.amc.core-functions
    version: ">=1.0.0"
  - id: com.example.shared-library
    version: "^2.0.0"
    optional: true

# Permissions the plugin requires
permissions:
  - crm:contact:read
  - crm:contact:write
  - notification:send
  - workspace:settings:read

# Event hooks the plugin subscribes to
hooks:
  - event: crm.contact.created
    handler: on_contact_created
    filters:
      source: web_form                        # Only contacts from web forms
      tags__contains: lead                     # Only contacts tagged as "lead"
  - event: campaign.sent
    handler: on_campaign_sent
  - event: schedule.daily
    handler: daily_maintenance
    cron: "0 3 * * *"                        # Run at 3 AM daily

# UI extension points
ui:
  - location: sidebar.marketing
    component: MyPluginPanel
    title: My Plugin
    icon: puzzle
    priority: 10
  - location: dashboard.widget
    component: MyWidget
    title: Campaign Overview
    size: md                                 # sm, md, lg, xl
  - location: settings.plugin
    component: MySettings
    title: Plugin Settings
  - location: toolbar.campaign.detail
    component: CampaignActionButton
    title: Send to Slack
  - location: email.editor.block
    component: CustomEmailBlock
    title: Product Showcase

# Backend configuration
backend:
  entry: server.py
  type: python                               # python | docker
  timeout: 30                                # seconds (sync)
  async_timeout: 300                         # seconds (async tasks)
  memory: 256                                # MB

# Network access
network:
  allow:
    - api.slack.com
    - hooks.slack.com
    - api.stripe.com

# Billing configuration
billing:
  type: subscription                         # free | one-time | subscription | usage-based
  price: 9.99
  currency: USD
  trial_days: 14
  billing_interval: monthly                  # monthly | yearly
  usage_metrics:
    - name: api_calls
      display_name: API Calls
      unit: call
      price_per_unit: 0.001
    - name: storage_mb
      display_name: Storage (MB)
      unit: MB/month
      price_per_unit: 0.05

# Localization
locales:
  - en
  - de
  - fr
  - ja

# License and legal
license: MIT
terms_of_service: https://example.com/tos
privacy_policy: https://example.com/privacy
```

### 5.3 Manifest Fields Reference

#### 5.3.1 Identity Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | ✅ | Reverse-domain identifier (e.g., `com.example.my-plugin`). Must be globally unique. |
| `name` | `string` | ✅ | Human-readable display name (max 50 characters) |
| `version` | `string` | ✅ | Semantic version (SemVer 2.0.0). Must be unique per plugin. |
| `type` | `enum` | ✅ | One of: `plugin`, `ai-agent`, `tool`, `extension`, `prompts`, `templates`, `workflows`, `integration`, `theme` |
| `description` | `string` | ✅ | Short description (max 500 characters). Markdown is not supported. |
| `author` | `string` | ✅ | Developer or organization name |
| `icon` | `string` | ❌ | Path to icon file (SVG preferred, min 48x48). Relative to manifest. |

#### 5.3.2 Compatibility Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `min_amc_version` | `string` | ✅ | Minimum AMC version required (SemVer). Enforced at install time. |
| `max_amc_version` | `string` | ❌ | Maximum AMC version (exclusive). Plugin will not be installable on versions ≥ this. |

#### 5.3.3 Discovery Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `categories` | `string[]` | ❌ | Categories for marketplace browsing. See category list below. |
| `tags` | `string[]` | ❌ | Search tags (max 10, alphanumeric + hyphens only) |
| `screenshots` | `object[]` | ❌ | Up to 5 screenshots for marketplace listing. Each has `src` and `alt`. |

**Available categories:**

```
analytics, automation, communication, crm, data-enrichment, design,
developer-tools, email, integrations, productivity, reporting, seo,
social-media, templates, ai, compliance, ecommerce, events, forms,
knowledge-management, landing-pages, payments, personalization,
security, sms, survey, video, webinars, other
```

#### 5.3.4 Dependencies

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `dependencies` | `object[]` | ❌ | Other plugins this plugin depends on. Each entry has `id`, `version` (SemVer range), and optional `optional` (boolean). |

#### 5.3.5 Permissions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `permissions` | `string[]` | ✅ | List of permission strings the plugin requires. Format: `{module}:{entity}:{action}` |

**Permission catalog:**

| Module | Entity | Actions |
|--------|--------|---------|
| `crm` | `contact` | `read`, `write`, `delete`, `export`, `import` |
| `crm` | `deal` | `read`, `write`, `delete` |
| `crm` | `company` | `read`, `write`, `delete` |
| `crm` | `list` | `read`, `write`, `delete`, `members_manage` |
| `crm` | `segment` | `read`, `write`, `delete` |
| `marketing` | `campaign` | `read`, `write`, `delete`, `send`, `schedule` |
| `marketing` | `email` | `read`, `write`, `delete`, `send`, `template` |
| `marketing` | `landing_page` | `read`, `write`, `delete`, `publish` |
| `marketing` | `form` | `read`, `write`, `delete` |
| `projects` | `task` | `read`, `write`, `delete`, `assign` |
| `projects` | `project` | `read`, `write`, `delete` |
| `knowledge` | `document` | `read`, `write`, `delete`, `search` |
| `knowledge` | `article` | `read`, `write`, `delete`, `publish` |
| `notification` | `send` | — | `send` (send notifications to users) |
| `workspace` | `settings` | `read`, `write` |
| `workspace` | `members` | `read`, `invite`, `remove` |
| `workspace` | `billing` | `read` |
| `ai` | `agent` | `invoke`, `configure` |
| `ai` | `credits` | `read`, `consume` |
| `analytics` | `report` | `read`, `write`, `delete` |
| `analytics` | `dashboard` | `read`, `write`, `delete` |
| `automation` | `workflow` | `read`, `write`, `delete`, `execute` |
| `storage` | `plugin` | `read`, `write` |

#### 5.3.6 Hooks

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `hooks` | `object[]` | ❌ | Event subscriptions. Each has `event` (string), `handler` (string — function name), optional `filters` (object), and optional `cron` (string — cron expression for scheduled events). |

#### 5.3.7 UI Extensions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ui` | `object[]` | ❌ | UI extension registrations. Each has `location` (string — extension point identifier), `component` (string — component name as registered in code), optional `title` (string), optional `icon` (string), optional `priority` (number), optional `size` (string). |

#### 5.3.8 Backend

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `backend.entry` | `string` | ✅ | Entry point file (e.g., `server.py`). Must export the plugin class. |
| `backend.type` | `enum` | ✅ | `python` (subprocess) or `docker` (container). Default: `python`. |
| `backend.timeout` | `integer` | ❌ | Synchronous handler timeout in seconds. Default: 30. Max: 60. |
| `backend.async_timeout` | `integer` | ❌ | Async handler timeout in seconds. Default: 300. Max: 600. |
| `backend.memory` | `integer` | ❌ | Memory limit in MB. Default: 256. Min: 64. Max: 1024 (requires approval). |

#### 5.3.9 Network

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `network.allow` | `string[]` | ❌ | List of allowed domains (`*` wildcards supported, e.g., `*.example.com`). |
| `network.block` | `string[]` | ❌ | Explicitly blocked domains (overrides wildcards in `allow`). |

#### 5.3.10 Billing

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `billing.type` | `enum` | ✅ | `free`, `one-time`, `subscription`, `usage-based` |
| `billing.price` | `number` | Conditional | Required if type is not `free`. Price in `currency` units. |
| `billing.currency` | `string` | ❌ | ISO 4217 currency code. Default: `USD`. |
| `billing.trial_days` | `integer` | ❌ | Free trial duration in days. Options: 7, 14, 30. |
| `billing.billing_interval` | `string` | Conditional | Required for `subscription`. `monthly` or `yearly`. |
| `billing.usage_metrics` | `object[]` | Conditional | Required for `usage-based`. Each has `name`, `display_name`, `unit`, `price_per_unit`. |

---

## 6. UI Extension Points

### 6.1 Architecture

UI extensions are React components that are rendered inside the AMC frontend within isolated boundaries:

```mermaid
graph TD
    subgraph AMC_Frontend["AMC Frontend (Next.js)"]
        Shell["Application Shell"]
        Router["Router"]
        ExtRegistry["Extension Registry"]
    end

    subgraph Plugin_UI["Plugin UI Sandbox"]
        ShadowDom["Shadow DOM Boundary"]
        Comp1["Component A<br/>(Web Component)"]
        Comp2["Component B<br/>(Web Component)"]
        Bridge["postMessage Bridge"]
    end

    Shell --> ExtRegistry
    ExtRegistry -->|"Mount Plugin Components"| ShadowDom
    Comp1 --> Bridge
    Comp2 --> Bridge
    Bridge -->|"Actions (API calls, navigation, etc.)"| Shell
    Shell -->|"Events (context, data, etc.)"| Bridge
```

**Rendering modes:**

| Mode | Isolation Level | Capabilities | When to Use |
|------|----------------|--------------|-------------|
| **React Component** | Same origin, same DOM (component-scoped CSS) | Maximum — full access to SDK hooks, co-located state | Dashboard widgets, form fields, inline components |
| **Web Component (Shadow DOM)** | CSS isolation, DOM encapsulation | High — style isolation, no CSS leaks | Sidebar panels, settings pages, custom blocks |
| **Iframe** | Full process isolation, separate origin | Medium — complete isolation, but limited communication | Third-party embeds, high-security extensions |

### 6.2 Extension Point Catalog

#### 6.2.1 Sidebar Panels

Add navigation items to the sidebar with associated content panels.

```yaml
# Manifest declaration
ui:
  - location: sidebar.main
    component: MySidebarPanel
    title: My Plugin
    icon: puzzle              # Heroicon or custom SVG icon name
    priority: 10              # Lower number = higher position
  - location: sidebar.marketing
    component: MarketingTools
    title: Marketing Tools
    icon: chart-bar
    priority: 20
  - location: sidebar.admin
    component: AdminPanel
    title: Plugin Admin
    icon: cog
```

```typescript
// React component
import { useAmcPlugin } from '@amc/sdk';
import { SidebarPanel } from '@amc/sdk/components';

export function MySidebarPanel() {
    const { api, context } = useAmcPlugin();
    const [contacts, setContacts] = useState<Contact[]>([]);

    useEffect(() => {
        api.crm.contacts.list({ limit: 10 }).then(setContacts);
    }, []);

    return (
        <SidebarPanel title="Recent Contacts" icon="users">
            <ul>
                {contacts.map(c => (
                    <li key={c.id}>{c.firstName} {c.lastName}</li>
                ))}
            </ul>
        </SidebarPanel>
    );
}
```

**Available sidebar locations:**

| Location | Description |
|----------|-------------|
| `sidebar.main` | Main navigation section |
| `sidebar.crm` | CRM section |
| `sidebar.marketing` | Marketing section |
| `sidebar.projects` | Projects section |
| `sidebar.knowledge` | Knowledge base section |
| `sidebar.analytics` | Analytics section |
| `sidebar.automation` | Automation section |
| `sidebar.admin` | Administration section (admin users only) |
| `sidebar.developer` | Developer tools section |

#### 6.2.2 Dashboard Widgets

Add cards, charts, and data visualizations to the AMC dashboard.

```yaml
ui:
  - location: dashboard.widget
    component: CampaignPerformanceWidget
    title: Campaign Performance
    size: md                    # sm | md | lg | xl | full
```

```typescript
// Dashboard widget component
import { AmcDashboardCard } from '@amc/sdk/components';
import { useAmcApi } from '@amc/sdk';
import { BarChart } from './charts';

export function CampaignPerformanceWidget() {
    const api = useAmcApi();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.analytics.reports.get('campaign-performance').then(report => {
            setData(report);
            setLoading(false);
        });
    }, []);

    return (
        <AmcDashboardCard
            title="Campaign Performance"
            loading={loading}
            refreshInterval={300000}  // Auto-refresh every 5 minutes
            onRefresh={() => window.location.reload()}
        >
            {data && <BarChart data={data.series} />}
        </AmcDashboardCard>
    );
}
```

**Available dashboard locations:**

| Location | Description |
|----------|-------------|
| `dashboard.widget` | Custom dashboard grid |
| `dashboard.header` | Dashboard header area (buttons, toggles) |
| `dashboard.footer` | Dashboard footer area |

#### 6.2.3 Toolbar Buttons

Add action buttons to list views and detail pages.

```yaml
ui:
  - location: toolbar.contacts.list
    component: ExportToSlackButton
    title: Export to Slack
    icon: slack
    priority: 5
  - location: toolbar.campaign.detail
    component: ScheduleInSlack
    title: Post to Slack
    icon: slack
    conditions:
      - campaign.status == "draft"
```

```typescript
// Toolbar button component
import { useAmcPlugin } from '@amc/sdk';
import { ToolbarButton } from '@amc/sdk/components';

export function ExportToSlackButton() {
    const { api, context } = useAmcPlugin();

    const handleClick = async () => {
        const contacts = await api.crm.contacts.list({ limit: 100 });
        await api.plugin.webhook.post('/slack/message', {
            text: `Contact export from ${context.workspace.name}:\n${
                contacts.items.map(c => `• ${c.email}`).join('\n')
            }`
        });
    };

    return (
        <ToolbarButton
            icon="slack"
            label="Export to Slack"
            onClick={handleClick}
            variant="secondary"
        />
    );
}
```

**Available toolbar locations:**

| Location | Description |
|----------|-------------|
| `toolbar.contacts.list` | Contact list view toolbar |
| `toolbar.contacts.detail` | Contact detail view toolbar |
| `toolbar.companies.list` | Company list view toolbar |
| `toolbar.deals.list` | Deal list view toolbar |
| `toolbar.campaign.list` | Campaign list view toolbar |
| `toolbar.campaign.detail` | Campaign detail view toolbar |
| `toolbar.email.list` | Email list view toolbar |
| `toolbar.email.editor` | Email editor toolbar |
| `toolbar.project.list` | Project list view toolbar |
| `toolbar.task.list` | Task list view toolbar |
| `toolbar.workflow.list` | Workflow list view toolbar |

#### 6.2.4 Settings Panels

Add configuration pages to the workspace settings.

```yaml
ui:
  - location: settings.plugin
    component: MyPluginSettings
    title: Slack Integration
    icon: slack
    category: integrations    # Groups plugins under "Integrations" in settings
```

```typescript
// Settings panel component
import { useAmcPlugin } from '@amc/sdk';
import { Form, FormField, Button } from '@amc/sdk/components';

export function MyPluginSettings() {
    const { storage, api } = useAmcPlugin();
    const [webhookUrl, setWebhookUrl] = useState('');
    const [channel, setChannel] = useState('#general');
    const [saving, setSaving] = useState(false);
    const [saved, setSaved] = useState(false);

    useEffect(() => {
        storage.get('slack_webhook_url').then(setWebhookUrl);
        storage.get('slack_channel').then(setChannel);
    }, []);

    const handleSave = async () => {
        setSaving(true);
        await storage.set('slack_webhook_url', webhookUrl);
        await storage.set('slack_channel', channel);
        setSaving(false);
        setSaved(true);
        setTimeout(() => setSaved(false), 3000);
    };

    return (
        <Form onSubmit={handleSave}>
            <h2>Slack Integration Settings</h2>

            <FormField
                label="Webhook URL"
                help="The incoming webhook URL from Slack. Starts with https://hooks.slack.com/"
            >
                <input
                    type="url"
                    value={webhookUrl}
                    onChange={e => setWebhookUrl(e.target.value)}
                    placeholder="https://hooks.slack.com/services/..."
                />
            </FormField>

            <FormField label="Default Channel">
                <input
                    type="text"
                    value={channel}
                    onChange={e => setChannel(e.target.value)}
                    placeholder="#general"
                />
            </FormField>

            <Button type="submit" loading={saving}>
                {saved ? '✓ Saved' : 'Save Settings'}
            </Button>
        </Form>
    );
}
```

**Available settings locations:**

| Location | Description |
|----------|-------------|
| `settings.plugin` | Plugin settings (grouped by category if multiple plugins share a category) |
| `settings.workspace` | Workspace-level settings section |
| `settings.account` | User account settings section |

#### 6.2.5 AI Agent Tools

Register custom tools that AI agents can invoke.

```typescript
// TypeScript — AI tool registration
import { registerPlugin } from '@amc/sdk';

export const SentimentTool = {
    name: 'sentiment_analyze',
    description: 'Analyze the sentiment of a text string',
    inputSchema: {
        type: 'object',
        properties: {
            text: {
                type: 'string',
                description: 'The text to analyze'
            },
            language: {
                type: 'string',
                enum: ['en', 'es', 'fr', 'de', 'ja'],
                default: 'en'
            }
        },
        required: ['text']
    },
    handler: async ({ text, language }: { text: string; language: string }) => {
        // Call external sentiment API
        const response = await fetch('https://api.example.com/sentiment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, language })
        });
        const result = await response.json();
        return {
            sentiment: result.label,
            score: result.score,
            confidence: result.confidence
        };
    }
};

// Register as an AI tool
registerPlugin({
    id: 'com.example.sentiment-tool',
    name: 'Sentiment Analyzer',
    tools: [SentimentTool]
});
```

**Available AI tool locations:**

| Location | Description |
|----------|-------------|
| `ai.tool` | Register a custom tool available to AI agents |
| `ai.agent-template` | Register a custom agent template |

#### 6.2.6 Email Template Blocks

Custom content blocks for the email builder.

```yaml
ui:
  - location: email.editor.block
    component: ProductShowcaseBlock
    title: Product Showcase
    icon: shopping-bag
    category: content
```

```typescript
// Email template block component
import { EmailBlock, useAmcApi } from '@amc/sdk/components';

export function ProductShowcaseBlock({ data, onChange }) {
    const api = useAmcApi();
    const [products, setProducts] = useState(data?.products || []);

    const addProduct = async () => {
        const product = await api.crm.products.create({
            name: '',
            price: 0,
            image_url: ''
        });
        setProducts([...products, product]);
        onChange({ products: [...products, product] });
    };

    return (
        <EmailBlock
            title="Product Showcase"
            onSettings={() => {/* open block settings */}}
        >
            <div className="product-grid">
                {products.map(product => (
                    <div key={product.id} className="product-card">
                        {product.image_url && (
                            <img src={product.image_url} alt={product.name} />
                        )}
                        <h3>{product.name}</h3>
                        <p>${product.price}</p>
                    </div>
                ))}
            </div>
            <button onClick={addProduct}>Add Product</button>
        </EmailBlock>
    );
}
```

#### 6.2.7 Landing Page Blocks

Custom sections for the landing page builder.

```yaml
ui:
  - location: landing-page.block
    component: TestimonialSection
    title: Testimonials Carousel
    icon: quote
    category: social-proof
```

#### 6.2.8 Data Table Columns

Custom column renderers for AMC data tables.

```yaml
ui:
  - location: table.contacts.column
    component: SlackStatusBadge
    title: Slack Status
    field: custom.slack_status      # Maps to a field in the contact data
```

```typescript
// Custom column renderer
import { ColumnRenderer } from '@amc/sdk/components';

export function SlackStatusBadge({ value, row }: ColumnRendererProps) {
    // `value` is the cell data; `row` is the full row data
    const isActive = value === 'active';
    return (
        <span className={`badge ${isActive ? 'badge-success' : 'badge-inactive'}`}>
            {isActive ? '🟢 Online' : '⚪ Offline'}
        </span>
    );
}
```

#### 6.2.9 Action Menus

Add items to contextual (right-click) menus.

```yaml
ui:
  - location: menu.contact
    component: SendSlackMessageAction
    title: Send Slack Message
    icon: slack
    group: communication
```

```typescript
// Context menu action
import { MenuAction, useAmcPlugin } from '@amc/sdk';

export function SendSlackMessageAction({ selectedIds }: { selectedIds: string[] }) {
    const { api } = useAmcPlugin();

    return (
        <MenuAction
            label="Send Slack Message"
            icon="slack"
            onAction={async () => {
                for (const id of selectedIds) {
                    const contact = await api.crm.contacts.get(id);
                    await api.plugin.webhook.post('/slack/message', {
                        text: `Contact: ${contact.firstName} ${contact.lastName} (${contact.email})`
                    });
                }
            }}
        />
    );
}
```

**Available menu locations:**

| Location | Description |
|----------|-------------|
| `menu.contact` | Contact contextual menu |
| `menu.company` | Company contextual menu |
| `menu.deal` | Deal contextual menu |
| `menu.campaign` | Campaign contextual menu |
| `menu.email` | Email contextual menu |
| `menu.task` | Task contextual menu |
| `menu.file` | File/document contextual menu |

#### 6.2.10 Modals and Overlays

Register modal dialogs that can be opened programmatically.

```typescript
import { registerModal, useAmcPlugin } from '@amc/sdk';

// Register a modal
registerModal({
    id: 'com.example.slack-message-modal',
    component: SlackMessageModal,
    size: 'md'  // sm, md, lg, xl, fullscreen
});

// Modal component
function SlackMessageModal({ contactId, onClose }) {
    const { api } = useAmcPlugin();
    const [message, setMessage] = useState('');

    const handleSend = async () => {
        await api.plugin.webhook.post('/slack/message', {
            contact_id: contactId,
            text: message
        });
        onClose();
    };

    return (
        <div className="modal">
            <h2>Send Slack Message</h2>
            <textarea
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder="Type your message..."
            />
            <div className="modal-actions">
                <button onClick={onClose}>Cancel</button>
                <button onClick={handleSend}>Send</button>
            </div>
        </div>
    );
}
```

#### 6.2.11 Custom Pages

Full-page extensions accessible via their own URL.

```yaml
ui:
  - location: page.custom
    component: AnalyticsDashboard
    route: /analytics/custom         # URL path relative to workspace
    title: Custom Analytics
    icon: chart-bar
    navigation: true                 # Show in main navigation
```

```typescript
// Custom page component
import { CustomPage, useAmcApi } from '@amc/sdk';

export function AnalyticsDashboard() {
    const api = useAmcApi();
    const [data, setData] = useState(null);

    useEffect(() => {
        api.analytics.reports.list().then(setData);
    }, []);

    return (
        <CustomPage title="Custom Analytics Dashboard">
            {/* Full-page content here */}
            <div className="grid grid-cols-3 gap-4">
                {data?.items.map(report => (
                    <ReportCard key={report.id} report={report} />
                ))}
            </div>
        </CustomPage>
    );
}
```

#### 6.2.12 Report Blocks

Custom chart types for the AMC reporting module.

```yaml
ui:
  - location: report.block
    component: HeatmapChart
    title: Activity Heatmap
    icon: grid
    category: advanced
```

#### 6.2.13 Form Fields

Custom input components for AMC forms.

```yaml
ui:
  - location: form.field
    component: ColorPicker
    title: Color Picker
    type: color
```

```typescript
// Custom form field
import { FormField } from '@amc/sdk/components';

export function ColorPicker({ value, onChange, label, error, ...props }) {
    return (
        <FormField label={label} error={error}>
            <div className="color-picker">
                <input
                    type="color"
                    value={value || '#6366f1'}
                    onChange={e => onChange(e.target.value)}
                />
                <input
                    type="text"
                    value={value || ''}
                    onChange={e => onChange(e.target.value)}
                    placeholder="#hex-color"
                />
            </div>
        </FormField>
    );
}
```

### 6.3 UI Extension Registration API

```typescript
// TypeScript — Registering UI extensions
import { registerPlugin } from '@amc/sdk';
import { MySidebarPanel } from './SidebarPanel';
import { MyWidget } from './Widget';
import { MySettings } from './Settings';
import { SentimentTool } from './SentimentTool';
import { SlackMessageModal } from './Modals';

registerPlugin({
    id: 'com.example.my-plugin',
    name: 'My Plugin',
    version: '1.0.0',

    // Components mapped to manifest locations
    components: {
        // Sidebar panel
        MySidebarPanel: {
            component: MySidebarPanel,
            locations: ['sidebar.marketing']
        },
        // Dashboard widget
        MyWidget: {
            component: MyWidget,
            locations: ['dashboard.widget']
        },
        // Settings panel
        MySettings: {
            component: MySettings,
            locations: ['settings.plugin']
        },
    },

    // AI tools
    tools: [
        SentimentTool
    ],

    // Modal dialogs
    modals: {
        'slack-message': SlackMessageModal
    },

    // Event handlers
    handlers: {
        'crm.contact.created': {
            handler: onContactCreated
        }
    }
});
```

### 6.4 UI Extension Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Mounted: Component registered,\nlocation rendered
    Mounted --> Rendering: Context and props\ninjected by host
    Rendering --> Active: Component renders\nsuccessfully
    Rendering --> Error: Render error
    Active --> Updated: Props/context\nchanged
    Updated --> Active
    Active --> Unmounted: User navigates\naway
    Error --> Unmounted
    Unmounted --> [*]

    state Active {
        [*] --> Idle
        Idle --> Fetching: API call
        Fetching --> Idle: Response
        Idle --> UserInteraction: User input
        UserInteraction --> Idle: Handler completes
    }
```

| Lifecycle Event | Description | Plugin Can |
|-----------------|-------------|------------|
| `mount` | Component is added to the DOM | Initialize state, set up subscriptions |
| `render` | React renders the component | Return JSX |
| `contextChange` | Context (workspace, user) changes | Re-fetch data, update UI |
| `propsChange` | Props from host change | Re-render with new props |
| `error` | Render error caught by error boundary | Show fallback UI |
| `unmount` | Component removed from DOM | Clean up subscriptions, release resources |

### 6.5 Cross-Origin Isolation

| Technique | CSS Isolation | DOM Isolation | Communication | Performance | Use Case |
|-----------|--------------|---------------|---------------|-------------|----------|
| **React Component** | ❌ (component-scoped CSS) | ❌ (shared DOM) | ✅ Direct | ⭐⭐⭐⭐⭐ | Dashboard widgets, form fields |
| **Web Component (Shadow DOM)** | ✅ Full | ✅ Partial (slots) | ✅ Through SDK bridge | ⭐⭐⭐⭐ | Sidebar panels, settings pages |
| **Iframe** | ✅ Full | ✅ Full | ✅ postMessage | ⭐⭐⭐ | Third-party embeds, untrusted code |

**Shadow DOM example:**

```typescript
// The SDK automatically wraps React components in Shadow DOM
// when the location requires it (sidebar, settings, custom blocks)
import { ShadowRoot, useAmcPlugin } from '@amc/sdk';

export function IsolatedWidget() {
    const { context } = useAmcPlugin();

    return (
        <ShadowRoot>
            {/* Styles here are scoped to this component */}
            <style>{`
                .widget { background: var(--color-bg-primary); padding: 16px; }
                .title { color: var(--color-text-primary); font-size: 18px; }
            `}</style>
            <div className="widget">
                <h2 className="title">Isolated Widget</h2>
                <p>Workspace: {context.workspaceId}</p>
            </div>
        </ShadowRoot>
    );
}
```

---

## 7. Backend Extension Points

### 7.1 Event Hooks

Plugins subscribe to AMC events and execute handler functions when those events fire.

```python
# Python SDK — Event hooks
from amc_sdk import AmcPlugin, event_handler

class MyPlugin(AmcPlugin):
    @event_handler("crm.contact.created")
    async def on_contact_created(self, event):
        """Called when a new contact is created in the CRM."""
        self.logger.info(f"New contact: {event.data.email}")
        # Event data is typed
        contact: Contact = event.data
        await self.process_new_contact(contact)

    @event_handler("crm.contact.updated")
    async def on_contact_updated(self, event):
        """Called when a contact is updated."""
        old: Contact = event.data.before
        new: Contact = event.data.after
        if old.email != new.email:
            self.logger.info(f"Contact {new.id} email changed")

    @event_handler("campaign.sent", filters={"type": "email"})
    async def on_campaign_sent(self, event):
        """Called when an email campaign is sent (filtered to email type only)."""
        campaign: Campaign = event.data
        await self.post_to_slack(f"Campaign '{campaign.name}' sent to {campaign.recipient_count} recipients")

    @event_handler("schedule.hourly")
    async def hourly_maintenance(self, event):
        """Runs on a schedule (every hour)."""
        await self.sync_external_data()

    @event_handler("schedule.daily")
    async def daily_maintenance(self, event):
        """Runs on a schedule (daily at configured time)."""
        await self.cleanup_old_data()
```

### 7.2 Webhook Receivers

Custom HTTP endpoints for external services to call into the plugin.

```python
# Python SDK — Webhook receivers
from amc_sdk import AmcPlugin, webhook

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        """Register webhook endpoints on plugin activation."""
        self.register_webhook("/slack/events", self.handle_slack, methods=["POST"])
        self.register_webhook("/github/events", self.handle_github, methods=["POST"])
        self.register_webhook("/health", self.health_check, methods=["GET"])

    async def handle_slack(self, request):
        """Handle incoming Slack events."""
        # Challenge verification
        if request.json().get("type") == "url_verification":
            return {"challenge": request.json()["challenge"]}

        # Verify signature
        signature = request.headers.get("X-Slack-Signature")
        timestamp = request.headers.get("X-Slack-Request-Timestamp")
        if not self.verify_slack_signature(request.body, signature, timestamp):
            return {"error": "invalid signature"}, 401

        # Process event
        event = request.json().get("event", {})
        await self.handle_slack_event(event)
        return {"status": "ok"}

    async def handle_github(self, request):
        """Handle incoming GitHub webhooks."""
        # Verify signature
        signature = request.headers.get("X-Hub-Signature-256")
        if not self.verify_github_signature(request.body, signature):
            return {"error": "invalid signature"}, 401

        event_type = request.headers.get("X-GitHub-Event")
        payload = request.json()

        self.logger.info(f"GitHub {event_type} event from {payload.get('repository', {}).get('full_name')}")
        return {"status": "ok"}

    async def health_check(self, request):
        """Simple health check endpoint."""
        return {"status": "healthy", "version": self.context.plugin_version}
```

**Webhook URL format:**

```
https://{workspace}.amc.io/api/v1/plugins/{plugin_id}/webhook/{path}
```

Example: `https://acme-corp.amc.io/api/v1/plugins/com.example.my-plugin/webhook/slack/events`

### 7.3 Scheduled Tasks

Cron-like periodic execution for maintenance, sync, and batch operations.

```yaml
# plugin.yaml — Scheduled tasks
hooks:
  - event: schedule.every_minute
    handler: frequent_check
  - event: schedule.every_5_minutes
    handler: sync_status
  - event: schedule.hourly
    handler: hourly_maintenance
  - event: schedule.daily
    handler: daily_cleanup
    cron: "0 3 * * *"              # Run at 3:00 AM
  - event: schedule.weekly
    handler: weekly_report
    cron: "0 5 * * 1"              # Run at 5:00 AM on Monday
  - event: schedule.custom
    handler: custom_schedule
    cron: "*/15 * * * *"           # Custom cron: every 15 minutes
```

```python
# Python SDK — Scheduled tasks
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def frequent_check(self, event):
        """Runs every minute."""
        await self.check_queue()

    async def sync_status(self, event):
        """Runs every 5 minutes."""
        await self.sync_external_status()

    async def hourly_maintenance(self, event):
        """Runs every hour."""
        await self.rotate_api_keys()

    async def daily_cleanup(self, event):
        """Runs daily at 3 AM."""
        cutoff = self.context.now() - timedelta(days=90)
        old_keys = await self.storage.keys()
        for key in old_keys:
            if key.startswith("temp_"):
                await self.storage.delete(key)
        self.logger.info("Daily cleanup complete")
```

**Available schedule presets:**

| Event Name | Frequency | Typical Use |
|------------|-----------|-------------|
| `schedule.every_minute` | Every 60 seconds | Queue checks, health pings |
| `schedule.every_5_minutes` | Every 5 minutes | Sync status checks |
| `schedule.every_15_minutes` | Every 15 minutes | Batch processing |
| `schedule.hourly` | Every hour | Data aggregation, cache warming |
| `schedule.daily` | Once per day (configurable cron) | Cleanup, reports, sync |
| `schedule.weekly` | Once per week (configurable cron) | Analytics rollups, maintenance |
| `schedule.custom` | Custom cron expression | Any custom schedule |

### 7.4 AI Tool Implementations

Custom tools that AI agents can invoke during conversations.

```python
# Python SDK — AI tool registration
from amc_sdk import AmcPlugin, ai_tool

class MyPlugin(AmcPlugin):
    @ai_tool(
        name="calculate_roi",
        description="Calculate marketing ROI given spend and revenue",
        parameters={
            "type": "object",
            "properties": {
                "spend": {
                    "type": "number",
                    "description": "Total marketing spend in USD"
                },
                "revenue": {
                    "type": "number",
                    "description": "Total attributed revenue in USD"
                },
                "period": {
                    "type": "string",
                    "enum": ["monthly", "quarterly", "yearly"],
                    "description": "The time period"
                }
            },
            "required": ["spend", "revenue"]
        }
    )
    async def calculate_roi(self, params: dict) -> dict:
        """Calculate ROI for marketing campaigns."""
        spend = params["spend"]
        revenue = params["revenue"]
        if spend <= 0:
            return {"error": "Spend must be greater than 0"}

        roi = ((revenue - spend) / spend) * 100
        return {
            "roi_percentage": round(roi, 2),
            "net_profit": round(revenue - spend, 2),
            "summary": f"ROI of {roi:.1f}% on {params.get('period', 'this period')} spend"
        }

    @ai_tool(
        name="generate_email_variants",
        description="Generate A/B test variants of an email",
        parameters={
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "string",
                    "description": "The campaign ID to generate variants for"
                },
                "num_variants": {
                    "type": "integer",
                    "description": "Number of variants to generate (2-5)",
                    "minimum": 2,
                    "maximum": 5
                },
                "focus": {
                    "type": "string",
                    "enum": ["subject_line", "cta", "body", "layout"],
                    "description": "What aspect to vary"
                }
            },
            "required": ["campaign_id"]
        }
    )
    async def generate_email_variants(self, params: dict) -> dict:
        """Generate A/B test email variants using AI."""
        campaign = await self.api.marketing.campaigns.get(params["campaign_id"])
        variants = []

        for i in range(params.get("num_variants", 3)):
            variant = await self.api.ai.complete(
                prompt=f"Generate a {params.get('focus', 'subject_line')} variant for: {campaign.name}",
                model="hermes-4",
                temperature=0.8 + (i * 0.1)
            )
            variants.append({
                "variant": i + 1,
                "content": variant.text,
                "focus": params.get("focus", "subject_line")
            })

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "variants": variants,
            "recommendation": "Consider A/B testing subject lines first for highest impact"
        }
```

### 7.5 API Route Injection

Plugins can inject custom API routes under a namespaced path.

```python
# Python SDK — API route injection
from amc_sdk import AmcPlugin, api_route

class MyPlugin(AmcPlugin):
    @api_route("/contacts/enrich", methods=["POST"])
    async def enrich_contact(self, request):
        """Enrich a contact with external data."""
        contact_id = request.json().get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}, 400

        contact = await self.api.crm.contacts.get(contact_id)
        enriched = await self.enrich_with_external_api(contact)

        # Update the contact with enriched data
        await self.api.crm.contacts.update(contact_id, enriched)

        return {"contact_id": contact_id, "enriched_fields": list(enriched.keys())}

    @api_route("/stats", methods=["GET"])
    async def plugin_stats(self, request):
        """Return plugin usage statistics."""
        api_calls = await self.billing.get_usage(metric="api_calls")
        storage_used = await self.storage.usage()
        return {
            "api_calls_total": api_calls.total,
            "api_calls_this_month": api_calls.this_period,
            "storage_keys": storage_used.key_count,
            "storage_bytes": storage_used.total_bytes
        }
```

**Route URL format:**

```
https://{workspace}.amc.io/api/v1/plugins/{plugin_id}/{path}
```

Example: `https://acme-corp.amc.io/api/v1/plugins/com.example.my-plugin/contacts/enrich`

**Route constraints:**

| Constraint | Limit |
|------------|-------|
| Max routes per plugin | 20 |
| Max path depth | 5 segments |
| Max request body size | 10 MB |
| Max response body size | 10 MB |
| Timeout (sync) | 30 seconds |
| Rate limit | 100 req/min per installation |

### 7.6 Middleware Hooks

Plugins can register middleware that intercepts requests and responses flowing through the AMC API.

```python
# Python SDK — Middleware hooks
from amc_sdk import AmcPlugin, middleware

class MyPlugin(AmcPlugin):
    @middleware("pre-request")
    async def add_custom_header(self, request):
        """Add headers to outgoing API requests."""
        request.headers["X-Plugin-Id"] = self.context.plugin_id
        request.headers["X-Plugin-Version"] = self.context.plugin_version
        return request

    @middleware("post-response")
    async def log_response(self, response):
        """Log all API responses for debugging."""
        self.logger.debug("API response", extra={
            "status": response.status,
            "endpoint": response.request.url,
            "duration_ms": response.duration_ms
        })
        return response

    @middleware("error")
    async def handle_api_error(self, error):
        """Handle API errors gracefully."""
        if error.status_code == 429:
            self.logger.warning("Rate limited, will retry")
            # The SDK will handle retry automatically
        elif error.status_code >= 500:
            self.logger.error(f"Server error: {error}")
            await self.notify_admin(error)
        return error
```

**Middleware types:**

| Type | When It Runs | Can Modify |
|------|-------------|------------|
| `pre-request` | Before every AMC API call | Request headers, body, URL |
| `post-response` | After every AMC API response | Response body, headers, status |
| `error` | When an API call fails | Error handling behavior |

### 7.7 Data Transformation Hooks

Hooks that run before data is saved or after it is read.

```python
# Python SDK — Data transformation hooks
from amc_sdk import AmcPlugin, data_hook

class MyPlugin(AmcPlugin):
    @data_hook("before-save", entity="crm.contact")
    async def before_contact_save(self, contact):
        """Transform contact data before it's saved to the database.
        Runs within the same transaction."""
        # Auto-format phone numbers
        if contact.phone:
            contact.phone = self.format_phone(contact.phone)

        # Set default tags
        if not contact.tags:
            contact.tags = ["new-lead"]

        # Look up company info
        if contact.email:
            domain = contact.email.split("@")[1]
            company = await self.api.crm.companies.get_by_domain(domain)
            if company:
                contact.company_id = company.id

        return contact

    @data_hook("after-read", entity="crm.contact")
    async def after_contact_read(self, contact):
        """Add computed fields to contact data."""
        # Add enrichment status
        contact.custom_fields["enrichment_status"] = await self.get_enrichment_status(contact.id)
        contact.custom_fields["slack_channel"] = await self.get_slack_channel(contact.id)
        return contact

    @data_hook("before-delete", entity="crm.contact")
    async def before_contact_delete(self, contact_id):
        """Clean up external data before contact is deleted."""
        await self.cleanup_external_data(contact_id)
        await self.storage.delete(f"contact_meta:{contact_id}")
        # Return None to allow deletion to proceed
        return None
```

### 7.8 Notification Channel Adapters

Custom notification delivery channels beyond email, SMS, and push.

```python
# Python SDK — Notification channel adapter
from amc_sdk import AmcPlugin, notification_channel

class MyPlugin(AmcPlugin):
    @notification_channel("slack")
    async def send_slack_notification(self, notification):
        """Send notifications via Slack webhook."""
        channel_config = await self.storage.get("slack_config")
        if not channel_config:
            raise Exception("Slack not configured")

        payload = {
            "channel": channel_config.get("channel", "#notifications"),
            "text": notification.title,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{notification.title}*\n{notification.body}"
                    }
                }
            ]
        }

        if notification.action_url:
            payload["blocks"].append({
                "type": "actions",
                "elements": [{
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View in AMC"},
                    "url": notification.action_url
                }]
            })

        response = await self.http_post(
            channel_config["webhook_url"],
            json=payload
        )

        return {"status": "sent", "channel": "slack", "message_ts": response.json().get("ts")}
```

### 7.9 Authentication Adapters

Custom SSO providers for workspace authentication.

```python
# Python SDK — Authentication adapter
from amc_sdk import AmcPlugin, auth_adapter

class MyPlugin(AmcPlugin):
    @auth_adapter("custom-saml")
    class CustomSAMLProvider:
        """Custom SAML authentication provider."""

        provider_name = "Custom SAML"
        icon = "saml-icon.svg"

        async def initiate_login(self, redirect_uri: str, state: str) -> str:
            """Return the SSO redirect URL."""
            saml_request = self.build_saml_request(redirect_uri, state)
            return f"https://saml.example.com/sso?SAMLRequest={saml_request}"

        async def handle_callback(self, request) -> dict:
            """Handle the SSO callback and return user info."""
            saml_response = request.form.get("SAMLResponse")
            user_info = self.parse_saml_response(saml_response)
            return {
                "email": user_info["email"],
                "first_name": user_info.get("firstName"),
                "last_name": user_info.get("lastName"),
                "external_id": user_info["nameId"],
                "groups": user_info.get("groups", [])
            }

        async def provision_user(self, user_info: dict) -> str:
            """Provision a user in the workspace (create if not exists)."""
            # AMC handles user creation; this hook allows custom mapping
            return {
                "role": "member",
                "workspace_id": user_info.get("workspace_id")
            }
```

### 7.10 Storage Adapters

Custom storage backends for plugin data.

```python
# Python SDK — Storage adapter
from amc_sdk import AmcPlugin, storage_adapter

class MyPlugin(AmcPlugin):
    @storage_adapter("s3-compatible")
    class S3Storage:
        """Custom S3-compatible storage backend for large files."""

        async def initialize(self, config: dict):
            """Initialize the storage adapter with configuration."""
            import boto3
            self.client = boto3.client(
                "s3",
                endpoint_url=config.get("endpoint_url"),
                aws_access_key_id=config["access_key"],
                aws_secret_access_key=config["secret_key"],
                region_name=config.get("region", "us-east-1")
            )
            self.bucket = config["bucket"]

        async def upload(self, path: str, data: bytes, content_type: str = None):
            """Upload a file."""
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            await self.client.put_object(
                Bucket=self.bucket,
                Key=path,
                Body=data,
                **extra_args
            )
            return {"path": path, "size": len(data)}

        async def download(self, path: str) -> bytes:
            """Download a file."""
            response = await self.client.get_object(Bucket=self.bucket, Key=path)
            return await response["Body"].read()

        async def delete(self, path: str):
            """Delete a file."""
            await self.client.delete_object(Bucket=self.bucket, Key=path)

        async def list(self, prefix: str = "") -> list:
            """List files with the given prefix."""
            response = await self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix
            )
            return [obj["Key"] for obj in response.get("Contents", [])]
```

---

## 8. Event System

### 8.1 Event Catalog

AMC emits events for virtually every state change in the platform. Plugins can subscribe to any of these events (subject to permission requirements).

#### CRM Events

| Event | Description | Data | Required Permission |
|-------|-------------|------|---------------------|
| `crm.contact.created` | A new contact is created | `Contact` | `crm:contact:read` |
| `crm.contact.updated` | A contact is modified | `ContactChange` (before + after) | `crm:contact:read` |
| `crm.contact.deleted` | A contact is deleted | `ContactDeleted` (id, timestamp) | `crm:contact:read` |
| `crm.company.created` | A new company is created | `Company` | `crm:company:read` |
| `crm.company.updated` | A company is modified | `CompanyChange` | `crm:company:read` |
| `crm.company.deleted` | A company is deleted | `CompanyDeleted` | `crm:company:read` |
| `crm.deal.created` | A new deal is created | `Deal` | `crm:deal:read` |
| `crm.deal.stage_changed` | A deal moves to a new stage | `DealStageChange` | `crm:deal:read` |
| `crm.deal.won` | A deal is marked as won | `Deal` | `crm:deal:read` |
| `crm.deal.lost` | A deal is marked as lost | `DealLost` (reason) | `crm:deal:read` |
| `crm.lead.created` | A new lead is created | `Lead` | `crm:lead:read` |
| `crm.lead.qualified` | A lead is qualified | `Lead` | `crm:lead:read` |
| `crm.list.membership.added` | Contact added to a list | `ListMembership` | `crm:list:read` |
| `crm.list.membership.removed` | Contact removed from a list | `ListMembership` | `crm:list:read` |
| `crm.segment.updated` | A segment's membership changes | `SegmentUpdate` | `crm:segment:read` |

#### Marketing Events

| Event | Description | Data | Required Permission |
|-------|-------------|------|---------------------|
| `campaign.created` | A campaign is created | `Campaign` | `marketing:campaign:read` |
| `campaign.updated` | A campaign is modified | `CampaignChange` | `marketing:campaign:read` |
| `campaign.scheduled` | A campaign is scheduled | `CampaignScheduled` | `marketing:campaign:read` |
| `campaign.sent` | A campaign is sent | `CampaignSent` (stats) | `marketing:campaign:read` |
| `campaign.opened` | A recipient opens a campaign email | `CampaignEvent` (contact_id, campaign_id) | `marketing:campaign:read` |
| `campaign.clicked` | A recipient clicks a link | `CampaignEvent` (url, contact_id) | `marketing:campaign:read` |
| `campaign.bounced` | An email bounces | `CampaignEvent` (reason) | `marketing:campaign:read` |
| `campaign.unsubscribed` | A recipient unsubscribes | `CampaignEvent` | `marketing:campaign:read` |
| `campaign.complained` | A recipient marks as spam | `CampaignEvent` | `marketing:campaign:read` |
| `campaign.completed` | A campaign finishes sending | `CampaignCompleted` (full stats) | `marketing:campaign:read` |
| `email.template.created` | An email template is created | `EmailTemplate` | `marketing:template:read` |
| `landing_page.published` | A landing page is published | `LandingPage` | `marketing:landing_page:read` |
| `form.submitted` | A form is submitted | `FormSubmission` (field values) | `marketing:form:read` |

#### Project Events

| Event | Description | Data | Required Permission |
|-------|-------------|------|---------------------|
| `project.created` | A project is created | `Project` | `projects:project:read` |
| `project.updated` | A project is updated | `ProjectChange` | `projects:project:read` |
| `project.completed` | A project is marked complete | `Project` | `projects:project:read` |
| `task.created` | A task is created | `Task` | `projects:task:read` |
| `task.updated` | A task is updated | `TaskChange` | `projects:task:read` |
| `task.completed` | A task is completed | `Task` | `projects:task:read` |
| `task.assigned` | A task is assigned to a user | `TaskAssignment` | `projects:task:read` |

#### AI Events

| Event | Description | Data | Required Permission |
|-------|-------------|------|---------------------|
| `ai.agent.invoked` | An AI agent is invoked | `AgentInvocation` | `ai:agent:read` |
| `ai.agent.response` | An AI agent generates a response | `AgentResponse` | `ai:agent:read` |
| `ai.credits.depleted` | Workspace AI credits are depleted | `CreditEvent` (remaining) | `ai:credits:read` |
| `ai.tool.called` | An AI tool is invoked | `ToolCall` | `ai:agent:read` |

#### Automation Events

| Event | Description | Data | Required Permission |
|-------|-------------|------|---------------------|
| `automation.workflow.created` | A workflow is created | `Workflow` | `automation:workflow:read` |
| `automation.workflow.activated` | A workflow is activated | `Workflow` | `automation:workflow:read` |
| `automation.workflow.completed` | A workflow execution completes | `WorkflowExecution` | `automation:workflow:read` |
| `automation.workflow.failed` | A workflow execution fails | `WorkflowFailure` (error) | `automation:workflow:read` |

#### System Events

| Event | Description | Data | Required Permission |
|-------|-------------|------|---------------------|
| `workspace.user.added` | A user is added to workspace | `WorkspaceUser` | `workspace:members:read` |
| `workspace.user.removed` | A user is removed from workspace | `WorkspaceUserRemoved` | `workspace:members:read` |
| `workspace.settings.updated` | Workspace settings change | `SettingsChange` | `workspace:settings:read` |
| `installation.enabled` | Plugin is enabled | `InstallationEvent` | N/A (automatic) |
| `installation.disabled` | Plugin is disabled | `InstallationEvent` | N/A (automatic) |
| `schedule.*` | Scheduled timer events | `ScheduleEvent` | N/A (automatic) |

### 8.2 Event Format (CloudEvents)

All AMC events conform to the [CloudEvents](https://cloudevents.io/) specification (v1.0.2) with the `application/cloudevents+json` format:

```json
{
    "specversion": "1.0",
    "type": "crm.contact.created",
    "source": "/workspaces/ws_abc123",
    "id": "evt_01J2XYZ...",
    "time": "2026-06-19T14:30:00Z",
    "datacontenttype": "application/json",
    "subject": "contact/c_789012",
    "tenantid": "tnt_abc123",
    "workspaceid": "ws_abc123",
    "userid": "usr_456789",
    "pluginid": "com.example.my-plugin",
    "data": {
        "id": "c_789012",
        "email": "jane@example.com",
        "first_name": "Jane",
        "last_name": "Smith",
        "company_id": "comp_345",
        "tags": ["lead", "webinar-attendee"],
        "created_at": "2026-06-19T14:30:00Z"
    }
}
```

**CloudEvents context attributes:**

| Attribute | Type | Description |
|-----------|------|-------------|
| `specversion` | `string` | CloudEvents specification version (always `1.0`) |
| `type` | `string` | Event type, dot-notation hierarchical (e.g., `crm.contact.created`) |
| `source` | `URI` | The context in which the event happened (workspace URI) |
| `id` | `string` | Unique event ID (ULID format) |
| `time` | `timestamp` | ISO 8601 UTC timestamp of the event |
| `datacontenttype` | `string` | Media type of the data (usually `application/json`) |
| `subject` | `string` | The subject of the event (entity type and ID) |
| `tenantid` | `string` | (Extension) Tenant ID for scoping |
| `workspaceid` | `string` | (Extension) Workspace ID |
| `userid` | `string` | (Extension) User who triggered the event |
| `pluginid` | `string` | (Extension) Plugin that triggered the event (if applicable) |
| `data` | `object` | Event payload (schema depends on event type) |

### 8.3 Event Delivery Guarantees

| Property | Guarantee |
|----------|-----------|
| **Delivery** | **At-least-once** — Events are retried until acknowledged or the retry budget is exhausted. |
| **Ordering** | **Per-entity, sequential** — Events for the same entity (e.g., contact `c_789012`) are delivered in the order they occurred. Events across different entities have best-effort ordering. |
| **Retry** | Exponential backoff: 1s → 2s → 4s → 8s → 16s → 32s → 60s (max). Total retry window: 1 hour. |
| **Dead letter** | After 1 hour of failed delivery attempts, the event is moved to a dead-letter queue. Developers are notified via email. Dead-letter events can be replayed from the Developer Portal. |
| **Duplication** | Events include a unique `id` field. Plugins should be idempotent — the same event may be delivered more than once under failure conditions. |

```python
# Python SDK — Idempotent event handling
from amc_sdk import AmcPlugin, event_handler

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Track processed event IDs for idempotency
        self.processed_events = set()

    @event_handler("crm.contact.created")
    async def on_contact_created(self, event):
        # Idempotency check
        if event.id in self.processed_events:
            self.logger.debug(f"Skipping duplicate event {event.id}")
            return

        self.processed_events.add(event.id)

        # Process the event
        await self.handle_new_contact(event.data)

        # Clean up old event IDs (keep last 1000)
        if len(self.processed_events) > 1000:
            self.processed_events = set(list(self.processed_events)[-1000:])
```

### 8.4 Event Subscription Management

Plugins declare their event subscriptions in the manifest:

```yaml
hooks:
  - event: crm.contact.created
    handler: on_contact_created
  - event: crm.contact.updated
    handler: on_contact_updated
  - event: campaign.sent
    handler: on_campaign_sent
    filters:                   # Optional: only receive filtered events
      campaign_type: email
  - event: schedule.daily
    handler: daily_cleanup
    cron: "0 3 * * *"
```

The AMC platform automatically:

1. **Registers subscriptions** when the plugin is installed/enabled
2. **Unregisters subscriptions** when the plugin is disabled/uninstalled
3. **Validates permissions** — an event that requires `crm:contact:read` permission will only be delivered if the plugin has that permission
4. **Enforces rate limits** — see Section 8.6

**Dynamic subscription management** (advanced use cases):

```python
# Python SDK — Dynamic subscription management
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Subscribe to events dynamically (in addition to manifest declarations)
        await self.events.subscribe("crm.contact.created", self.on_contact_created)

        # Subscribe with filters
        await self.events.subscribe("campaign.sent", self.on_campaign_sent, filters={
            "campaign_type": "email"
        })

        # Subscribe to a custom event emitted by another plugin
        await self.events.subscribe("com.example.other-plugin.custom-event", self.on_custom_event)

    async def on_disable(self):
        # Unsubscribe from dynamic subscriptions
        await self.events.unsubscribe("crm.contact.created", self.on_contact_created)
```

### 8.5 Event Filtering

Events can be filtered at the subscription level to reduce unnecessary handler invocations:

```yaml
hooks:
  - event: crm.contact.created
    handler: on_lead_created
    filters:
      tags__contains: lead        # Only contacts tagged "lead"
      source: web_form            # Only from web forms
  - event: campaign.sent
    handler: on_email_sent
    filters:
      type: email                 # Only email campaigns
      status: sent                # Only successfully sent
```

**Filter operators:**

| Operator | Description | Example |
|----------|-------------|---------|
| `field: value` | Exact match | `source: web_form` |
| `field__contains: value` | Array contains value | `tags__contains: lead` |
| `field__gt: value` | Greater than | `score__gt: 80` |
| `field__gte: value` | Greater than or equal | `amount__gte: 100` |
| `field__lt: value` | Less than | `priority__lt: 3` |
| `field__lte: value` | Less than or equal | `age__lte: 30` |
| `field__in: [a, b]` | In array | `status__in: [active, pending]` |
| `field__exists: true` | Field exists | `company_id__exists: true` |
| `field__regex: pattern` | Regex match | `email__regex: .*@example\.com` |

### 8.6 Throttling

Each plugin installation has a maximum event delivery rate. Exceeding the rate causes events to be queued and delivered when the rate drops below the threshold.

| Tier | Max Events/sec | Burst | Default for |
|------|---------------|-------|-------------|
| Free plugins | 5 | 10 | Free listings |
| Paid plugins | 20 | 50 | Paid listings |
| Premium plugins | 100 | 200 | Enterprise tier, high-volume plugins |

**Throttling behavior:**

```mermaid
sequenceDiagram
    participant S as AMC Event Bus
    participant T as Throttle Gate
    participant P as Plugin Handler

    S->>T: Event A
    S->>T: Event B
    S->>T: Event C
    Note over T: Within rate limit
    T->>P: Deliver Event A
    T->>P: Deliver Event B
    T->>P: Deliver Event C
    
    S->>T: Event D
    S->>T: Event E
    S->>T: Event F
    S->>T: Event G
    Note over T: Exceeded rate limit
    T->>P: Deliver Event D
    T-->>P: Event E (queued)
    T-->>P: Event F (queued)
    T-->>P: Event G (queued)
    
    Note over P: Handler processes Event D
    P->>T: Ack
    Note over T: Rate drops below limit
    T->>P: Deliver Event E
    T->>P: Deliver Event F
    T->>P: Deliver Event G
```

**Backpressure signals:**

If the plugin handler consistently takes longer than the event arrival interval, the AMC event bus signals backpressure:

1. The throttle gate reduces delivery rate
2. Events queue up (max queue depth: 10,000 events)
3. If the queue overflows, oldest events are dropped (with a warning log)
4. Developer is notified if backpressure persists for > 5 minutes

---

## 9. Billing & Monetization

### 9.1 Pricing Models

AMC supports five pricing models for marketplace listings:

#### 9.1.1 Free

No cost to the user. Ideal for open-source tools, community integrations, and prompt libraries.

```yaml
billing:
  type: free
```

#### 9.1.2 One-Time Purchase

A single payment grants perpetual use of the plugin (with access to updates for the current major version).

```yaml
billing:
  type: one-time
  price: 49.99
  currency: USD
```

#### 9.1.3 Monthly/Yearly Subscription

Recurring payment that grants access while the subscription is active.

```yaml
billing:
  type: subscription
  price: 9.99
  currency: USD
  billing_interval: monthly      # monthly or yearly
  trial_days: 14                 # 7, 14, or 30
```

```yaml
# Yearly subscription (often with discount)
billing:
  type: subscription
  price: 99.99
  currency: USD
  billing_interval: yearly
  annual_discount: 17%           # vs monthly ($9.99 × 12 = $119.88)
```

#### 9.1.4 Usage-Based

Pay-per-use pricing where the plugin reports usage via the metering API.

```yaml
billing:
  type: usage-based
  usage_metrics:
    - name: api_calls
      display_name: API Calls
      unit: call
      price_per_unit: 0.01
      billing_cycle: monthly
    - name: ai_credits
      display_name: AI Credits Consumed
      unit: credit
      price_per_unit: 0.05
      billing_cycle: monthly
    - name: contacts_synced
      display_name: Contacts Synced
      unit: contact
      price_per_unit: 0.001
      billing_cycle: monthly
  minimum_monthly: 9.99          # Minimum charge per month
  maximum_monthly: 999.99        # Cap (optional)
```

#### 9.1.5 Freemium

A free tier with limited functionality, plus paid upgrades.

```yaml
# Freemium is achieved by publishing two listings:
# 1. Free plugin (limited features)
billing:
  type: free

# 2. Paid plugin (full features)
billing:
  type: subscription
  price: 19.99
  currency: USD
  billing_interval: monthly
  trial_days: 14
```

### 9.2 Trial Periods

Paid plugins can offer free trials:

| Trial Duration | When Billing Starts | Notes |
|---------------|---------------------|-------|
| 7 days | After trial ends | Best for simple plugins |
| 14 days | After trial ends | Recommended default |
| 30 days | After trial ends | Best for complex plugins with onboarding |

**Trial behavior:**

- During the trial, the plugin has full access to all features
- Users are reminded via in-app notification 3 days before trial ends
- When the trial ends, the plugin is either:
  - **Converted to paid** (if user has a payment method on file)
  - **Disabled** (if no payment method) — data is preserved for 30 days
- Users can cancel during the trial at any time with no charge

### 9.3 Metering API

The metering API lets usage-based plugins report consumption:

```python
# Python SDK — Metering API
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def process_data(self, payload):
        # Process the request
        result = await self.perform_processing(payload)

        # Report usage
        await self.billing.report(
            metric="api_calls",
            value=1,
            metadata={
                "endpoint": "process",
                "data_size_kb": len(str(payload)) // 1024
            }
        )

        # Report AI credits consumed
        credits_used = result.get("ai_credits", 0)
        if credits_used > 0:
            await self.billing.report(
                metric="ai_credits",
                value=credits_used
            )

        return result

    async def handle_batch(self, items):
        # Batch reporting is more efficient
        reports = []
        for item in items:
            reports.append({"metric": "api_calls", "value": 1})

        await self.billing.report_batch(reports)

    async def get_current_usage(self):
        """Check current billing period usage."""
        usage = await self.billing.get_usage(
            metric="api_calls",
            period="current_month"
        )
        self.logger.info(f"Current API calls this month: {usage.total}")
        return usage
```

**Metering API reference:**

| Method | Description |
|--------|-------------|
| `billing.report(metric, value, metadata=None)` | Report a single usage event |
| `billing.report_batch(reports)` | Report multiple usage events atomically |
| `billing.get_usage(metric, period="current_month")` | Get current usage for a metric |
| `billing.get_all_usage(period="current_month")` | Get usage for all metrics |
| `billing.get_remaining_budget()` | Get remaining spend cap (if configured) |

### 9.4 License Key Validation

For plugins that need to operate outside the AMC marketplace (e.g., on-premises deployments), license keys can be validated:

```python
# Python SDK — License key validation
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Validate license key on activation
        license_key = await self.storage.get("license_key")
        if license_key:
            valid = await self.billing.validate_license(license_key)
            if not valid:
                self.logger.warning("Invalid license key")
                # Optionally degrade functionality
        else:
            self.logger.info("No license key configured")

    async def validate_license(self, license_key: str) -> dict:
        """Validate a license key against the licensing server."""
        return await self.billing.validate_license(license_key)
```

### 9.5 Refund Policy

| Scenario | Refund Policy | Developer Impact |
|----------|--------------|------------------|
| **User requests refund within 7 days** | Full refund | Revenue is deducted from developer's next payout |
| **User requests refund after 7 days** | Case-by-case review | Revenue may be deducted from developer's next payout |
| **Plugin is broken/non-functional** | Full refund | Revenue deducted; developer must fix or plugin is removed |
| **Security vulnerability** | Full refund for affected period | Revenue deducted; plugin may be emergency disabled |
| **Fraudulent activity** | Full refund | Revenue deducted; developer may be banned |

### 9.6 Revenue Dashboard

Developers access their revenue analytics through the Developer Portal:

| Metric | Description | Update Frequency |
|--------|-------------|------------------|
| **Gross Revenue** | Total revenue from all sales before commission | Real-time |
| **Net Revenue** | Developer's 70% share after commission | Real-time |
| **Monthly Recurring Revenue (MRR)** | Sum of active subscription revenue | Daily |
| **Annual Run Rate (ARR)** | MRR × 12 | Daily |
| **Active Subscriptions** | Number of currently paying installations | Real-time |
| **Churn Rate** | % of subscriptions canceled in period | Monthly |
| **Average Revenue Per User (ARPU)** | Net revenue / active installations | Monthly |
| **Lifetime Value (LTV)** | Average total revenue per installation | Monthly |
| **Payout History** | Historical payouts with breakdown | Per-payout |
| **Upcoming Payout** | Estimated next payout amount | Real-time |
| **Tax Withheld** | Applicable taxes withheld per jurisdiction | Per-transaction |

---

## 10. Plugin Lifecycle

### 10.1 Lifecycle States

```mermaid
stateDiagram-v2
    [*] --> Development: amc plugin init
    Development --> Submitted: amc marketplace submit
    Submitted --> InReview: Automated scan passes
    Submitted --> Rejected: Automated scan fails
    InReview --> Approved: Manual review passes
    InReview --> ChangesRequested: Fixes needed
    InReview --> Rejected: Policy violation
    ChangesRequested --> Submitted: Developer resubmits
    Approved --> Published: Developer clicks publish
    Published --> Installed: User installs
    Installed --> Active: Plugin initializes
    Active --> Disabled: User disables
    Disabled --> Active: User enables
    Active --> Uninstalled: User uninstalls
    Disabled --> Uninstalled: User uninstalls
    Uninstalled --> [*]
    Published --> Archived: Developer archives
    Active --> EmergencyDisabled: Security issue
    EmergencyDisabled --> [*]: Plugin removed
    
    state Development {
        [*] --> Coding
        Coding --> Testing: amc test
        Testing --> Debugging: Fail
        Debugging --> Coding
        Testing --> [*]: All tests pass
    end
    
    state Published {
        Published --> Version1_v0: v1.0.0
        Published --> Version1_v1: v1.1.0
        Published --> Version2_v0: v2.0.0
    end
```

### 10.2 Development Mode

During development, plugins run in the sandbox workspace with special privileges:

- **Debug logging** — Full debug output visible in the Developer Portal
- **Hot reload** — Changes to plugin code are applied without restarting
- **Extended timeouts** — 5 minutes for synchronous handlers (vs. 30s in production)
- **Unlimited network access** — No network restrictions during development
- **Simulated events** — Developers can manually trigger events to test handlers
- **Performance metrics** — Detailed execution traces for each handler invocation

```bash
# Start development mode
amc dev run

# Output:
# ╔══════════════════════════════════════════════╗
# ║   Plugin Dev Server v1.0.0                  ║
# ║   Plugin: com.example.my-plugin             ║
# ║   Workspace: Acme Corp (Sandbox)            ║
# ║   Status: Running                           ║
# ║   Hot Reload: Enabled                       ║
# ║   Debug: ON                                 ║
# ╚══════════════════════════════════════════════╝
# 
# Registered handlers:
#   📥 crm.contact.created  → on_contact_created
#   📥 campaign.sent       → on_campaign_sent
#   📥 schedule.daily      → daily_maintenance
# 
# UI Components:
#   🖥️ sidebar.marketing    → MyPluginPanel
#   🖥️ dashboard.widget    → MyWidget
#   🖥️ settings.plugin     → MySettings
# 
# Webhook endpoints:
#   🔗 /slack/events
#   🔗 /github/push
# 
# Watching for file changes... (Ctrl+C to stop)
```

### 10.3 Submission Checklist

Before submitting a plugin for review, developers should verify:

```
□ Manifest (plugin.yaml) is complete and valid
□ All permissions declared in manifest match actual usage
□ No hardcoded secrets (API keys, passwords, tokens) in code
□ All external domains are declared in network.allow
□ Plugin has been tested in sandbox workspace
□ All UI components render correctly
□ Event handlers complete within timeouts
□ Error handling covers network failures, API errors, timeouts
□ Logging is appropriate (no PII in logs)
□ Documentation is complete (README, screenshots, changelog)
□ License file is included
□ Screenshots are uploaded for marketplace listing
□ Pricing and billing model is configured
□ Support contact information is current
□ Changelog is updated for this version
□ Plugin version matches git tag
```

### 10.4 Review Process

```mermaid
sequenceDiagram
    participant D as Developer
    participant M as Marketplace API
    participant Auto as Automated Scanner
    participant Manual as Manual Reviewer
    participant Pub as Publisher

    D->>M: POST /marketplace/submit
    M->>Auto: Trigger automated scan
    Auto-->>M: Scan result
    
    alt Scan Failed
        M-->>D: 422 Rejected (with errors)
    else Scan Passed
        M-->>D: 202 Accepted (submission_id)
        
        alt Manual Review Required
            M->>Manual: Add to review queue
            Manual-->>M: Review decision
            
            alt Changes Requested
                M-->>D: Review notes
                D->>M: POST /marketplace/resubmit
                M->>Auto: Re-scan
                M->>Manual: Re-review
            else Rejected
                M-->>D: Rejection reason
            else Approved
                M->>Pub: Auto-publish or wait for developer
                alt Auto-publish
                    Pub-->>M: Published
                    M-->>D: Published notification
                else Manual publish
                    M-->>D: Ready to publish
                    D->>M: POST /marketplace/publish
                    M-->>D: Published
                end
            end
        end
    end
```

**Automated scan checks:**

| Check | What It Detects | Pass/Fail |
|-------|----------------|-----------|
| **Malware scan** | Known malware signatures, suspicious patterns | 🚫 Fail |
| **Secret leakage** | Hardcoded API keys, tokens, passwords | 🚫 Fail |
| **Dependency audit** | Known CVEs in dependencies | ⚠️ Warning / 🚫 Fail |
| **Static analysis** | Code quality, potential bugs, type errors | ⚠️ Warning |
| **Permission audit** | Code accesses entities not declared in manifest | 🚫 Fail |
| **Network audit** | Code connects to domains not in manifest allowlist | 🚫 Fail |
| **UI rendering test** | UI components render without errors | ⚠️ Warning |
| **Manifest validation** | Manifest is syntactically and semantically valid | 🚫 Fail |
| **Size check** | Plugin package size < 50 MB | 🚫 Fail |
| **License check** | License file present and valid | ⚠️ Warning |

### 10.5 Update Flow

```mermaid
flowchart LR
    A["Developer creates<br/>new version"] --> B["Upload to marketplace"]
    B --> C["Automated scan"]
    C --> D{"Changes?"}
    D -->|"Patch (1.0.0 → 1.0.1)"| E["Fast-track review"]
    D -->|"Minor (1.0.0 → 1.1.0)"| F["Standard review"]
    D -->|"Major (1.0.0 → 2.0.0)"| G["Full review"]
    E --> H["Approved"]
    F --> H
    G --> H
    H --> I{"Version type"}
    I -->|"Patch"| J["Auto-update<br/>all installations"]
    I -->|"Minor"| K["Notify users<br/>(opt-in update)"]
    I -->|"Major"| L["Manual upgrade<br/>+ migration required"]
```

**Version bump rules:**

| Change Type | Version Bump | Review Track | User Impact |
|-------------|-------------|--------------|-------------|
| Bug fix, security patch | Patch (+0.0.1) | Fast-track (automated only) | Auto-updated |
| New feature, new UI | Minor (+0.1.0) | Standard (automated + manual) | Notified, can choose to update |
| Breaking changes | Major (+1.0.0) | Full review | Must manually upgrade |

### 10.6 Breaking Changes

A change is considered **breaking** if it:

1. Removes or renames a manifest field
2. Removes or changes the signature of a handler the SDK exposes
3. Changes the data format of an event payload
4. Removes or narrows a permission
5. Changes a UI extension location or component API
6. Removes a webhook endpoint
7. Changes the behavior of existing functionality in a way that could break dependent workflows

**Major version requirements:**

- Plugin must include a **migration guide** explaining what changed and how to adapt
- Plugin must maintain backward compatibility for at least **3 months** after the major release
- Plugin can use the `max_amc_version` field to prevent installation on incompatible AMC versions
- Users on the previous major version continue to receive security patches for 6 months

### 10.7 Deprecation Policy

When a developer decides to deprecate (sunset) a plugin:

| Phase | Duration | What Happens |
|-------|----------|--------------|
| **Notice** | Day 0 | Developer marks plugin as "deprecated" in marketplace. New installs blocked. |
| **Grace period** | 90 days | Existing installations continue to work. Developer must provide migration path. |
| **End-of-life** | Day 90 | Plugin is disabled on all installations. Data is preserved for 30 more days. |
| **Data deletion** | Day 120 | Plugin data is deleted from active storage. Archived for 1 year. |

**Developer obligations during deprecation:**

- Provide clear migration instructions to users
- Offer alternative recommendations (own or third-party)
- Respond to support inquiries during the grace period
- Ensure security patches for critical vulnerabilities during the grace period

### 10.8 Emergency Disable

AMC can remotely disable a plugin in response to:

| Scenario | Response Time | Action |
|----------|--------------|--------|
| **Critical security vulnerability** (CVSS ≥ 9.0) | Immediate | Plugin disabled globally. Developer notified. |
| **Data breach** (PII exposed) | Immediate | Plugin disabled globally. All installations notified. |
| **Malware detected** | Immediate | Plugin disabled globally. Developer account suspended. |
| **Active exploitation** | Immediate | Plugin disabled globally. Forensics initiated. |
| **High-severity vulnerability** (CVSS 7.0–8.9) | Within 24 hours | Plugin disabled globally unless patch is deployed. |
| **TOS violation** | Within 72 hours | Plugin disabled. Developer can appeal. |

**Emergency disable procedure:**

1. AMC security team identifies the issue (via automated monitoring, user report, or disclosure)
2. Plugin is remotely disabled — the AMC platform sends a `disable` signal to all installations
3. Plugin code cannot run; UI components are replaced with a "Plugin Disabled" message
4. Plugin data is preserved (not deleted)
5. Developer is notified with details of the issue and steps to remediate
6. After remediation, developer submits a new version for expedited review
7. Once approved, AMC re-enables the plugin on all installations

---

## 11. Security & Sandboxing

### 11.1 Plugin Isolation Architecture

```mermaid
graph TB
    subgraph Host["AMC Host"]
        Scheduler["Plugin Scheduler"]
        Monitor["Resource Monitor"]
        EventBus["Event Bus"]
    end
    
    subgraph PluginSandbox["Plugin Sandbox"]
        direction TB
        Proc["Process<br/>(subprocess/Docker)"]
        NetFilter["Network Filter<br/>(nftables)"]
        FS["Temp FS<br/>(ephemeral)"]
        MemLimit["Memory Limit<br/>(256 MB)"]
        TimeLimit["Execution Timeout<br/>(30s/5min)"]
    end
    
    subgraph DataAccess["Data Access Layer"]
        API["AMC REST API<br/>(with RLS)"]
        StorageAPI["SDK Storage API<br/>(encrypted KV)"]
    end
    
    PluginSandbox -->|"AMC API calls"| DataAccess
    PluginSandbox -->|"Allowed domains only"| Ext["External Services"]
    EventBus -->|"Events"| Proc
    Scheduler -->|"Start/Stop"| Proc
    Monitor -->|"Resource usage"| Proc
```

### 11.2 Backend Isolation

#### 11.2.1 Subprocess Isolation (Default)

For most plugins, a **subprocess** sandbox is sufficient:

| Mechanism | Details |
|-----------|---------|
| **Process** | Each plugin instance runs as a separate OS process under a dedicated system user (`plugin-{id}`) |
| **User permissions** | The plugin user has read/write access only to its own temp directory |
| **Capabilities** | Linux capabilities are dropped — no `CAP_NET_RAW`, `CAP_SYS_ADMIN`, etc. |
| **Seccomp** | System call filtering restricts ~50% of syscalls (only safe/necessary ones allowed) |
| **Namespaces** | PID, network, mount, and user namespaces isolate the plugin from the host and other plugins |
| **cgroups** | CPU, memory, and I/O limits are enforced via cgroups v2 |

```bash
# Sandbox resource limits
--memory=256m
--memory-swap=256m        # No swap
--cpus=0.5                # Max 50% of one CPU core
--pids-limit=100          # Max 100 processes
--read-only               # Read-only root filesystem
--tmpfs /tmp:size=100m    # Only writable directory
--cap-drop=ALL            # Drop all capabilities
```

#### 11.2.2 Docker Container Isolation

For plugins with special requirements (native dependencies, specific system libraries), a **Docker container** sandbox is available (requires approval):

```dockerfile
# Plugin container template
FROM python:3.11-slim

# Plugin user (non-root)
RUN useradd -m -u 1001 plugin
USER plugin

# Plugin code is mounted at runtime
WORKDIR /app

# No network except what's in manifest
# (enforced by container network policy)
```

**Docker sandbox enhancements:**

| Feature | Subprocess | Docker |
|---------|------------|--------|
| Isolation level | OS (namespaces) | Full container |
| Startup time | < 100ms | ~500ms |
| Memory overhead | ~5 MB | ~30 MB |
| Native dependencies | ❌ (host libs only) | ✅ (custom Dockerfile) |
| GPU access | ❌ | ✅ (with approval) |
| Persistent state | ❌ (ephemeral) | ❌ (ephemeral) |

### 11.3 Frontend Isolation

UI extensions are rendered with DOM isolation:

```typescript
// The SDK wraps all UI components in Shadow DOM
// for CSS and DOM encapsulation
import { ShadowRoot } from '@amc/sdk';

function PluginWidget() {
    return (
        <ShadowRoot>
            <style>{/* Scoped styles */}</style>
            <div>{/* Plugin content */}</div>
        </ShadowRoot>
    );
}
```

**Frontend isolation layers:**

| Layer | Protection |
|-------|-----------|
| **Shadow DOM** | CSS scoping — plugin styles cannot leak out; host styles cannot leak in |
| **Content Security Policy (CSP)** | Plugin iframes have `sandbox` attribute: `allow-scripts allow-same-origin` (no `allow-top-navigation`, no `allow-popups`) |
| **PostMessage Bridge** | Communication with host is through a strict `postMessage` protocol. Only specific message types are accepted. |
| **No Cookie Access** | Plugin UI code cannot read document.cookie (HttpOnly cookies for session) |
| **No Local Storage** | Plugin code cannot access localStorage (host uses sessionStorage with HttpOnly cookies) |
| **Sanitized Input** | All data passed from plugin to host is sanitized (no XSS vectors) |

### 11.4 Network Isolation

Network access is the most tightly controlled dimension:

```mermaid
flowchart TD
    Plugin["Plugin Code"] --> DNS["DNS Resolver\n(Intercepted)"]
    DNS --> Check{"Domain in\nmanifest.allow?"}
    Check -->|"Yes"| Resolve["Resolve DNS"]
    Check -->|"No"| Block["Block (NXDOMAIN)"]
    
    Resolve --> Connect["TCP Connection"]
    Connect --> FW["Firewall\n(nftables)"]
    FW --> FWCheck{"Destination\nallowed?"}
    FWCheck -->|"Yes"| SSL["TLS Handshake\n(MITM inspection)"]
    FWCheck -->|"No"| Drop["Drop Connection"]
    SSL --> App["Application Layer\n(HTTP, etc.)"]
    App --> AppCheck{"Domain match\nTLS SNI?"}
    AppCheck -->|"Match"| Allow["Allow"]
    AppCheck -->|"Mismatch"| Block2["Block"]
```

**Network enforcement layers:**

| Layer | Enforcement | Bypass Difficulty |
|-------|-------------|-------------------|
| **DNS** | Custom DNS resolver that only resolves allowed domains | Medium (hardcoded IPs) |
| **TCP (nftables)** | Per-process firewall rules | Hard (no CAP_NET_ADMIN) |
| **TLS** | SNI inspection at proxy level | Very hard (network proxy) |
| **Application (SDK)** | SDK HTTP client double-checks destination | Easy (use raw sockets, but see above) |

### 11.5 Data Isolation

| Data Type | Access Method | Isolation |
|-----------|--------------|-----------|
| **AMC Database** | AMC REST API only (no direct connections) | RLS enforces tenant boundaries on every query |
| **Plugin Key-Value Store** | SDK `Storage` API | Per-installation namespace; encrypted at rest with installation-specific key |
| **Temporary Files** | Ephemeral `/tmp` | Per-process temp directory; cleaned on exit |
| **Secrets** | SDK `Storage` API (secret type) | Encrypted with a separate key; never logged; never returned in API responses |

### 11.6 Permission Model

#### 11.6.1 Permission Declaration

Plugins declare required permissions in the manifest:

```yaml
permissions:
  - crm:contact:read
  - crm:contact:write
  - notification:send
```

#### 11.6.2 Permission Approval

On installation, the admin user sees a permission summary:

```
Plugin "My Plugin" is requesting the following permissions:

  ✓ crm:contact:read       Read contacts in your workspace
  ✓ crm:contact:write      Create and update contacts
  ✓ notification:send      Send notifications to workspace members

[Approve] [Deny]
```

#### 11.6.3 Least Privilege Enforcement

At runtime, every API call is checked against the granted permissions:

```python
# The SDK handles permission checking automatically
class MyPlugin(AmcPlugin):
    async def on_contact_created(self, event):
        # This call is allowed because plugin has crm:contact:read
        contact = await self.api.crm.contacts.get(event.data.contact_id)

        # This call would fail with PermissionDeniedError
        # because plugin does NOT have crm:contact:delete
        # await self.api.crm.contacts.delete(event.data.contact_id)
```

#### 11.6.4 Permission Revocation

Admins can revoke specific permissions at any time:

```python
# When a permission is revoked, the SDK throws PermissionDeniedError
# for any operation requiring that permission
try:
    await self.api.crm.contacts.create(contact_data)
except PermissionDeniedError as e:
    self.logger.error(f"Permission denied: {e}")
    await self.handle_permission_issue(e)
```

**Permission groups:**

| Group | Permissions | Use Case |
|-------|-------------|----------|
| `read-only` | `*:read` | Analytics, reporting, monitoring |
| `crm-basic` | `crm:contact:read`, `crm:company:read` | CRM tools, enrichment |
| `crm-full` | `crm:*:*` | Full CRM integration |
| `marketing-basic` | `marketing:campaign:read`, `marketing:template:read` | Analytics, reporting |
| `marketing-full` | `marketing:*:*` | Full marketing integration |
| `admin` | `workspace:*:*` | Admin tools, configuration |

### 11.7 Code Scanning

Every submission goes through static analysis:

```bash
# AMC Code Scanner checks:
$ amc scan submit/package.zip
# ✓ Malware scan:       Clean
# ✓ Secret scan:        No secrets detected
# ✓ Dependency audit:   3 warnings (minor)
# ✓ Static analysis:    0 errors, 5 warnings
# ✓ Permission audit:   Permissions match usage
# ✓ Network audit:      All domains declared in manifest
# ✓ UI rendering test:  All components render
# ✓ Size check:         1.2 MB (limit: 50 MB)
# 
# Result: PASSED (warnings are advisory)
```

**Scanner rules (non-exhaustive):**

| Rule | Severity | Detection |
|------|----------|-----------|
| Hardcoded credential | 🚫 Fail | Regex patterns for API keys, tokens, passwords |
| Suspicious import | 🚫 Fail | `subprocess`, `ctypes`, `socket` (without network manifest) |
| Crypto miner | 🚫 Fail | Known crypto mining signatures |
| Obfuscated code | 🚫 Fail | Entropy analysis, base64/hex encoding |
| Dynamic eval | ⚠️ Warning | `eval()`, `exec()`, `__import__()` |
| Insecure dependency | ⚠️ Warning | Known CVEs in dependencies |
| Large binary blob | ⚠️ Warning | Files > 1 MB that aren't media/assets |
| Excessive permissions | ⚠️ Warning | Plugin requests more permissions than typical for its category |

### 11.8 Secrets Management

Sensitive plugin data is stored with additional encryption:

```python
# Python SDK — Secrets storage
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Store a secret (encrypted with plugin-specific key)
        await self.storage.set_secret("api_key", "sk_live_xxxxxxxxxxxx")
        await self.storage.set_secret("webhook_secret", "whsec_xxxxxxxxxxxx")

        # Read a secret
        api_key = await self.storage.get_secret("api_key")

        # Secrets have additional protections:
        # - Not included in log output
        # - Not returned in storage.keys() listing
        # - Not visible in the Developer Portal
        # - Encrypted with a separate key (not the same as regular storage)
```

**Secret storage differences:**

| Feature | Regular Storage | Secrets Storage |
|---------|----------------|-----------------|
| Encryption key | Per-installation key | Per-installation key + separate encryption key |
| Log visibility | Visible (value masked) | Never logged |
| List API | Included | Excluded |
| Export/backup | Included | Excluded |
| Developer Portal | Visible (value masked) | Not visible |
| Max value size | 64 KB | 4 KB |
| Max count | 1,000 keys | 100 keys |

### 11.9 Rate Limiting

Per-plugin, per-tenant rate limits:

| Dimension | Limit | Applies To |
|-----------|-------|------------|
| **API calls** | 100 req/min (free), 500 req/min (paid) | AMC API calls from plugin |
| **Event delivery** | 5 events/sec (free), 20 events/sec (paid) | Events delivered to plugin |
| **Webhook calls** | 50 req/min (inbound) | Incoming webhook requests |
| **Storage operations** | 1,000 ops/min | Storage read/write/delete |

**Rate limit headers:**

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1624105800
```

### 11.10 Quotas

Beyond rate limits, plugins have hard quotas:

| Quota | Limit | Exceeded? |
|-------|-------|-----------|
| **Storage (KV)** | 10 MB per installation | Storage writes fail with `QuotaExceededError` |
| **API calls per month** | 50,000 (free), 500,000 (paid) | Additional calls blocked or billed (usage-based) |
| **Compute time per day** | 1 hour (cumulative) | Plugin disabled until next day |
| **Concurrent instances** | 5 per workspace | New events queued |
| **Log volume per day** | 100 MB | Older logs dropped |
| **Max plugin package size** | 50 MB | Submission rejected |

---

## 12. Developer Portal

### 12.1 Developer Dashboard

The Developer Portal (accessible at `https://marketplace.amc.io/developer`) provides a comprehensive dashboard:

```
┌─────────────────────────────────────────────────────────────┐
│  🔧 Developer Dashboard                   [Profile] [Docs]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │
│  │ 12      │ │ 4,523   │ │ $3,847  │ │ $12,450 │          │
│  │ Plugins │ │ Installs │ │ MRR     │ │ LTV     │          │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │
├─────────────────────────────────────────────────────────────┤
│  Revenue (Last 12 Months)                      [Export ▾]  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  📈 Bar chart showing monthly revenue                │  │
│  │     Net: $3,847 / Gross: $5,496 (70% share)          │  │
│  └──────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Plugin Performance                                        │
│  ┌──────────┬────────┬────────┬────────┬────────┬────────┐ │
│  │ Plugin   │ Installs│Active │ Rating │ Revenue│ Churn  │ │
│  ├──────────┼────────┼────────┼────────┼────────┼────────┤ │
│  │ Slack    │ 2,341  │ 1,892 │ ⭐4.7  │ $2,150 │ 3.2%   │ │
│  │ Sentiment│ 1,203  │ 987   │ ⭐4.2  │ $890   │ 5.1%   │ │
│  │ GA4      │ 879    │ 654   │ ⭐4.5  │ $807   │ 2.8%   │ │
│  └──────────┴────────┴────────┴────────┴────────┴────────┘ │
├─────────────────────────────────────────────────────────────┤
│  Recent Activity                                            │
│  • 2026-06-19 14:30  New install: Acme Corp (Slack)       │
│  • 2026-06-19 13:15  Subscription canceled: Beta Inc      │
│  • 2026-06-19 11:00  Review update: v2.1.0 approved       │
│  • 2026-06-18 22:30  Payout issued: $1,247.50             │
└─────────────────────────────────────────────────────────────┘
```

### 12.2 Plugin Management

CRUD operations for plugins:

| Operation | API Endpoint | Description |
|-----------|-------------|-------------|
| Create | `POST /api/v1/marketplace/plugins` | Create a new plugin listing |
| Read | `GET /api/v1/marketplace/plugins/{id}` | Get plugin details |
| Update | `PATCH /api/v1/marketplace/plugins/{id}` | Update plugin metadata |
| Delete | `DELETE /api/v1/marketplace/plugins/{id}` | Delete plugin (only if no installations) |
| List | `GET /api/v1/marketplace/plugins` | List all plugins for developer |
| Submit | `POST /api/v1/marketplace/plugins/{id}/submit` | Submit for review |
| Publish | `POST /api/v1/marketplace/plugins/{id}/publish` | Publish approved version |

### 12.3 Version Management

| Operation | API Endpoint | Description |
|-----------|-------------|-------------|
| Upload version | `POST /api/v1/marketplace/plugins/{id}/versions` | Upload new plugin version |
| List versions | `GET /api/v1/marketplace/plugins/{id}/versions` | List all versions |
| Get version | `GET /api/v1/marketplace/plugins/{id}/versions/{version}` | Get version details |
| Update version | `PATCH /api/v1/marketplace/plugins/{id}/versions/{version}` | Update version metadata |
| Set as latest | `POST /api/v1/marketplace/plugins/{id}/versions/{version}/promote` | Set version as latest |

### 12.4 Analytics

```python
# Python SDK — Analytics access
from amc_sdk import AMCClient

client = AMCClient(api_key="amc_dev_xxx")

# Get install analytics
installs = client.marketplace.analytics.installs(
    plugin_id="com.example.my-plugin",
    period="last_30_days",
    granularity="day"
)
# Returns: [{"date": "2026-06-01", "new_installs": 12, "uninstalls": 3}, ...]

# Get revenue analytics
revenue = client.marketplace.analytics.revenue(
    plugin_id="com.example.my-plugin",
    period="this_month"
)
# Returns: {"gross": 549.60, "commission": 164.88, "net": 384.72}

# Get usage stats
usage = client.marketplace.analytics.usage(
    plugin_id="com.example.my-plugin",
    metrics=["api_calls", "storage_mb"],
    period="last_30_days"
)
```

**Analytics available in Developer Portal:**

| Report | Description | Granularity |
|--------|-------------|-------------|
| **Unique Installs** | Number of unique workspaces that installed | Daily, weekly, monthly |
| **Active Installations** | Currently active installations | Daily, weekly, monthly |
| **Install/Uninstall Rate** | New installs minus uninstalls | Daily, weekly, monthly |
| **Revenue** | Gross, net, commission breakdown | Daily, weekly, monthly |
| **MRR/ARR** | Monthly/Annual recurring revenue | Monthly |
| **Churn Rate** | % of installations that unsubscribed | Monthly |
| **LTV** | Lifetime value per installation | Monthly |
| **Rating Trends** | Average rating over time | Weekly, monthly |
| **Usage Metrics** | API calls, storage, compute time | Daily, weekly, monthly |
| **Geographic Distribution** | Installs by country/region | Monthly |
| **Version Adoption** | Which plugin versions are installed | Real-time |
| **Feature Usage** | Which features are used most | Daily |

### 12.5 Documentation & Guides

The Developer Portal includes a comprehensive documentation hub:

- **Getting Started Guide** — Tutorial for first plugin
- **SDK Reference** — Full API documentation for Python and TypeScript SDKs
- **UI Component Library** — Interactive showcase of all UI extension points
- **Design Guidelines** — Best practices for UI extensions (consistent with AMC design system)
- **API Reference** — OpenAPI 3.1 specification for all marketplace APIs
- **Migration Guides** — How to upgrade between SDK major versions
- **FAQ** — Common questions and answers
- **Changelog** — SDK and marketplace platform changelog

### 12.6 API Playground

Interactive API explorer at `https://marketplace.amc.io/developer/playground`:

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔌 API Playground                                  [Auth: ✅ Dev] │
├─────────────────────────────────────────────────────────────────────┤
│  Method: [GET ▾]  URL: [/api/v1/marketplace/plugins ▾]            │
│                                                                     │
│  Headers:                                                            │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Authorization: Bearer amc_dev_xxxxxxxxxxxxxxxx              │   │
│  │ Content-Type: application/json                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  Request Body: [None]                                               │
│                                                                     │
│  [▶ Send Request]                                                   │
│                                                                     │
│  Response:                                                          │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ HTTP 200 OK                                                   │   │
│  │ {                                                             │   │
│  │   "items": [                                                  │   │
│  │     { "id": "com.example...", "name": "My Plugin", ... }     │   │
│  │   ],                                                          │   │
│  │   "total": 12                                                 │   │
│  │ }                                                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 12.7 Support Ticket System

Developers can create and track support tickets related to:

| Category | Response Time | Examples |
|----------|--------------|----------|
| Review status | 4 hours | "How long until my plugin is reviewed?" |
| Technical issues | 8 hours | "My webhook endpoint is returning 500" |
| Billing/payments | 24 hours | "Why was my payout $0 this month?" |
| Account issues | 24 hours | "I lost access to my developer account" |
| Appeals | 48 hours | "My plugin was rejected, I'd like to appeal" |
| Policy questions | 48 hours | "Can my plugin use WebAssembly?" |

### 12.8 Community Forum

The Developer Portal includes a community forum with categories:

- **Announcements** — SDK updates, marketplace changes, platform releases
- **Show & Tell** — Developers showcase their plugins
- **Q&A** — Technical questions and answers
- **Feature Requests** — SDK and marketplace feature suggestions
- **Bug Reports** — SDK bugs and issues
- **Best Practices** — Community-contributed guides and tips

---

## 13. SDK Reference (Python)

### 13.1 Core Class: `AmcPlugin`

```python
from amc_sdk import AmcPlugin, Application

class MyPlugin(AmcPlugin):
    """Base class for all AMC plugins.

    Your plugin class must inherit from AmcPlugin and implement
    the desired lifecycle methods and event handlers.
    """

    # ── Lifecycle Methods ──────────────────────────────────

    async def on_install(self):
        """Called once when the plugin is first installed.
        
        Use this to set up initial configuration, migrate data,
        or register webhooks that persist across sessions.
        """
        await self.storage.set("installed_at", self.context.now().isoformat())
        self.logger.info("Plugin installed")

    async def on_uninstall(self):
        """Called when the plugin is being uninstalled.
        
        Clean up external resources: delete webhooks, revoke
        API tokens, notify external services.
        """
        await self.cleanup_external_resources()
        self.logger.info("Plugin uninstalled")

    async def on_enable(self):
        """Called when the plugin is activated (after install or re-enable).
        
        Register webhooks, start background tasks, validate configuration.
        """
        if not await self.storage.get("api_key"):
            self.logger.warning("API key not configured — some features disabled")
        await self.register_webhooks()

    async def on_disable(self):
        """Called when the plugin is disabled by the user."""
        self.logger.info("Plugin disabled")

    async def on_update(self, old_version: str, new_version: str):
        """Called after the plugin is updated to a new version.
        
        Use for data migration between versions.
        
        Args:
            old_version: The previous version string
            new_version: The new version string
        """
        self.logger.info(f"Updated from {old_version} to {new_version}")
        if self._version_lt(old_version, "2.0.0") and self._version_gte(new_version, "2.0.0"):
            await self.migrate_v1_to_v2()
```

### 13.2 Application Entry Point

```python
# server.py — Plugin entry point
from amc_sdk import Application
from my_plugin import MyPlugin

# Create the application
app = Application(
    plugin_class=MyPlugin,
    manifest_path="plugin.yaml"  # Auto-loaded, but can specify path
)

# Run the plugin server
if __name__ == "__main__":
    app.run()
```

### 13.3 Context

```python
class PluginContext:
    """Context available to all plugin handlers."""
    
    # Identifiers
    tenant_id: str              # Tenant (organization) ID
    workspace_id: str           # Workspace ID within tenant
    user_id: str                # Current user ID (or system user for events)
    user_email: str             # Current user's email
    user_role: str              # Current user's role (admin, member, etc.)
    installation_id: str        # Unique ID of this plugin installation
    
    # Locale and timezone
    locale: str                 # e.g., "en-US", "de-DE", "ja-JP"
    timezone: str               # e.g., "America/New_York", "Europe/Berlin"
    
    # Plugin metadata
    plugin_id: str              # Plugin ID from manifest
    plugin_version: str         # Current installed version
    plugin_type: str            # Plugin type from manifest
    
    # Utilities
    def now(self) -> datetime:
        """Returns current time in the workspace timezone."""
    
    def utcnow(self) -> datetime:
        """Returns current UTC time."""
```

### 13.4 API Client

```python
# Typed API client hierarchy
self.api.crm.contacts          # Contact operations
self.api.crm.companies         # Company operations
self.api.crm.deals             # Deal operations
self.api.crm.leads             # Lead operations
self.api.crm.lists             # List operations
self.api.crm.segments          # Segment operations

self.api.marketing.campaigns   # Campaign operations
self.api.marketing.emails      # Email operations
self.api.marketing.templates   # Email template operations
self.api.marketing.landing_pages  # Landing page operations
self.api.marketing.forms       # Form operations
self.api.marketing.audiences   # Audience operations

self.api.projects.projects     # Project operations
self.api.projects.tasks        # Task operations
self.api.projects.milestones   # Milestone operations

self.api.knowledge.documents   # Document operations
self.api.knowledge.articles    # Article operations
self.api.knowledge.categories  # Category operations

self.api.analytics.reports     # Report operations
self.api.analytics.dashboards  # Dashboard operations
self.api.analytics.metrics     # Metric operations

self.api.automation.workflows  # Workflow operations
self.api.automation.executions # Workflow execution operations

self.api.ai.complete           # AI completion
self.api.ai.agents             # AI agent operations
self.api.ai.credits            # AI credit operations

self.api.notification.send     # Send notifications
self.api.storage.upload        # Upload files
self.api.storage.download      # Download files
```

**Common API methods:**

```python
# CRUD pattern
await self.api.crm.contacts.get(contact_id)          # GET /crm/contacts/{id}
await self.api.crm.contacts.list(filters={...})       # GET /crm/contacts
await self.api.crm.contacts.create(data={...})        # POST /crm/contacts
await self.api.crm.contacts.update(id, data={...})    # PATCH /crm/contacts/{id}
await self.api.crm.contacts.delete(id)                # DELETE /crm/contacts/{id}
await self.api.crm.contacts.count(filters={...})      # GET /crm/contacts/count
await self.api.crm.contacts.search(query="...")       # GET /crm/contacts/search
```

### 13.5 Event Handling

```python
from amc_sdk import AmcPlugin, event_handler

class MyPlugin(AmcPlugin):
    
    # ── Decorator-based event handlers ───────────────────
    
    @event_handler("crm.contact.created")
    async def on_contact_created(self, event):
        """Handle new contact creation."""
        contact = event.data  # Type: Contact
        self.logger.info(f"Contact created: {contact.email}")
    
    @event_handler("crm.contact.updated")
    async def on_contact_updated(self, event):
        """Handle contact updates with before/after data."""
        before = event.data.before  # Type: Contact
        after = event.data.after    # Type: Contact
        self.logger.info(f"Contact updated: {before.email} → {after.email}")
    
    @event_handler("campaign.sent", filters={"type": "email"})
    async def on_email_campaign_sent(self, event):
        """Handle sent email campaigns (filtered)."""
        campaign = event.data  # Type: Campaign
        await self.post_to_slack(f"Campaign '{campaign.name}' sent!")
    
    # ── Dynamic subscription ─────────────────────────────
    
    async def custom_subscribe(self):
        await self.events.subscribe("crm.deal.won", self.on_deal_won)
    
    async def on_deal_won(self, event):
        deal = event.data  # Type: Deal
        self.logger.info(f"Deal won: {deal.name} (${deal.amount})")
    
    async def custom_unsubscribe(self):
        await self.events.unsubscribe("crm.deal.won", self.on_deal_won)
```

### 13.6 Storage API

```python
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def storage_example(self):
        # ── Regular Storage ──
        
        # Set a value
        await self.storage.set("config_key", {"nested": "value"})
        
        # Set with TTL (auto-expire after 1 hour)
        await self.storage.set("temp_token", "abc123", ttl_seconds=3600)
        
        # Get a value
        value = await self.storage.get("config_key")  # Returns dict or None
        
        # Get with default
        value = await self.storage.get("missing_key", default="fallback")
        
        # List keys
        all_keys = await self.storage.keys()  # Returns list of strings
        
        # List keys with prefix
        config_keys = await self.storage.keys(prefix="config_")
        
        # Delete a key
        await self.storage.delete("temp_token")
        
        # Check if key exists
        exists = await self.storage.exists("config_key")
        
        # Get storage usage
        usage = await self.storage.usage()  # Returns UsageStats
        
        # Clear all data (use with caution)
        await self.storage.clear()
        
        # ── Secrets Storage ──
        
        # Store secret (encrypted with separate key)
        await self.storage.set_secret("api_key", "sk_live_xxx")
        
        # Get secret
        api_key = await self.storage.get_secret("api_key")
        
        # Delete secret
        await self.storage.delete_secret("api_key")
        
        # ── Counter Operations ──
        
        # Increment a counter
        count = await self.storage.increment("page_views")  # Returns new value
        count = await self.storage.increment("page_views", by=5)
        
        # Decrement
        count = await self.storage.decrement("credits_remaining")
```

### 13.7 Billing API

```python
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def billing_example(self):
        # ── Report Usage ──
        
        # Report a single usage metric
        await self.billing.report(
            metric="api_calls",
            value=1,
            metadata={"endpoint": "/analyze", "duration_ms": 245}
        )
        
        # Report multiple metrics in batch
        await self.billing.report_batch([
            {"metric": "api_calls", "value": 1},
            {"metric": "ai_tokens", "value": 150},
            {"metric": "storage_mb", "value": 2.5},
        ])
        
        # ── Query Usage ──
        
        # Get usage for current billing period
        usage = await self.billing.get_usage(metric="api_calls")
        # Returns: UsageMetric(total=1234, unit="calls")
        
        # Get usage for a specific period
        monthly = await self.billing.get_usage(
            metric="api_calls",
            period="current_month"
        )
        
        # Get all metrics usage
        all_usage = await self.billing.get_all_usage()
        # Returns: {"api_calls": UsageMetric(...), "ai_tokens": UsageMetric(...)}
        
        # ── Subscription Info ──
        
        # Check if the installation has an active subscription
        subscription = await self.billing.get_subscription()
        # Returns: Subscription(active=True, tier="pro", next_billing_date="...")
        
        # ── License Validation ──
        
        # Validate a license key (for on-prem or external deployments)
        result = await self.billing.validate_license("AMC-LIC-XXXX-XXXX")
        # Returns: {"valid": True, "features": ["premium", "unlimited"], "expires": "..."}
```

### 13.8 Logging API

```python
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def logging_example(self):
        # Structured logging with context
        self.logger.debug("Detailed debug info", extra={
            "function": "logging_example",
            "iteration": 42
        })
        
        self.logger.info("Operation completed", extra={
            "operation": "data_sync",
            "records_processed": 1000,
            "duration_ms": 4520
        })
        
        self.logger.warning("Configuration missing", extra={
            "config_key": "api_key",
            "feature": "slack_integration"
        })
        
        self.logger.error("Failed to process request", extra={
            "contact_id": "c_123",
            "error_code": "TIMEOUT"
        }, exc_info=True)
        
        self.logger.critical("Data integrity violation detected", extra={
            "entity": "contact",
            "entity_id": "c_123",
            "discrepancy": "email_mismatch"
        })
        
        # ── Metrics logging ──
        self.logger.metric("api_latency_ms", 245, tags={"endpoint": "/analyze"})
        self.logger.metric("records_processed", 1000)
```

### 13.9 Webhook Registration

```python
from amc_sdk import AmcPlugin, webhook

class MyPlugin(AmcPlugin):
    async def on_enable(self):
        # Register webhooks
        self.register_webhook("/slack/events", self.handle_slack, methods=["POST"])
        self.register_webhook("/github/events", self.handle_github, methods=["POST"])
        self.register_webhook("/health", self.health_check, methods=["GET"])
        
        # Register webhook with custom auth
        self.register_webhook(
            "/custom/webhook",
            self.handle_custom,
            methods=["POST"],
            auth_required=True,
            auth_handler=self.verify_custom_auth
        )
    
    async def handle_slack(self, request):
        """Handle webhook request.
        
        Args:
            request: WebhookRequest with .json(), .body, .headers, .method, .query_params
        Returns:
            Tuple of (response_body, status_code) or just response_body
        """
        payload = request.json()
        
        # Verify Slack signature
        signature = request.headers.get("X-Slack-Signature", "")
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        if not self.verify_slack_signature(request.body, signature, timestamp):
            return {"error": "invalid signature"}, 401
        
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload["challenge"]}
        
        return {"status": "ok"}
    
    async def health_check(self, request):
        """Simple health endpoint."""
        return {
            "status": "healthy",
            "version": self.context.plugin_version,
            "uptime_hours": await self.get_uptime()
        }
```

**WebhookRequest object:**

```python
class WebhookRequest:
    """Incoming webhook request."""
    
    method: str                 # HTTP method (GET, POST, etc.)
    path: str                   # Path relative to webhook base
    headers: dict               # Request headers
    query_params: dict          # Query string parameters
    body: bytes                 # Raw request body
    content_type: str           # Content-Type header
    
    def json(self) -> dict:
        """Parse body as JSON."""
    
    def form(self) -> dict:
        """Parse body as form data."""
    
    def text(self) -> str:
        """Decode body as text."""
```

### 13.10 HTTP Client

```python
from amc_sdk import AmcPlugin

class MyPlugin(AmcPlugin):
    async def http_example(self):
        # The SDK provides an HTTP client for external API calls
        # (only to domains declared in manifest)
        
        # GET request
        response = await self.http.get(
            "https://api.example.com/data",
            headers={"Accept": "application/json"},
            params={"page": 1, "limit": 50}
        )
        data = response.json()
        
        # POST request
        response = await self.http.post(
            "https://api.example.com/webhook",
            json={"event": "test", "data": {}},
            headers={"Authorization": "Bearer token"}
        )
        
        # POST with form data
        response = await self.http.post(
            "https://api.example.com/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "...",
                "client_secret": "..."
            }
        )
        
        # PUT
        response = await self.http.put(
            "https://api.example.com/resource/123",
            json={"status": "updated"}
        )
        
        # DELETE
        response = await self.http.delete(
            "https://api.example.com/resource/123"
        )
        
        # File upload (multipart)
        response = await self.http.upload(
            "https://api.example.com/files",
            file_path="/tmp/report.pdf",
            field_name="file",
            extra_fields={"description": "Monthly report"}
        )
```

### 13.11 Scheduler

```python
from amc_sdk import AmcPlugin, scheduled_task

class MyPlugin(AmcPlugin):
    
    # Scheduled tasks are declared in manifest hooks,
    # but can also be registered dynamically:
    
    async def on_enable(self):
        # Register dynamic schedule
        await self.scheduler.every_hour(self.hourly_task)
        await self.scheduler.every_day("0 3 * * *", self.daily_cleanup)  # cron
        await self.scheduler.interval(minutes=15, handler=self.frequent_check)
    
    async def hourly_task(self):
        """Runs every hour."""
        self.logger.info("Hourly maintenance running")
        await self.sync_data()
    
    async def daily_cleanup(self):
        """Runs daily at 3 AM."""
        self.logger.info("Daily cleanup running")
        cutoff = self.context.now() - timedelta(days=30)
        await self.cleanup_old_records(cutoff)
    
    async def frequent_check(self):
        """Runs every 15 minutes."""
        await self.check_webhook_health()
    
    async def on_disable(self):
        # Unregister dynamic schedules
        await self.scheduler.cancel(self.hourly_task)
```

---

## 14. SDK Reference (TypeScript/React)

### 14.1 Core Hook: `useAmcPlugin()`

```typescript
import { useAmcPlugin } from '@amc/sdk';

function MyComponent() {
    const {
        context,         // PluginContext — workspace, user, locale, etc.
        api,             // AmcApiClient — full AMC API
        storage,         // StorageAPI — key-value storage
        billing,         // BillingAPI — usage metering
        logger,          // Logger — structured logging
        currentUser,     // User — current user info
        events,          // EventSystem — subscribe/unsubscribe
    } = useAmcPlugin();

    // Typed context
    console.log(context.workspaceId);   // string
    console.log(context.tenantId);      // string
    console.log(context.userId);        // string
    console.log(context.locale);        // 'en-US'
    console.log(context.timezone);      // 'America/New_York'
    console.log(context.installationId); // string
    console.log(context.pluginVersion);  // '1.0.0'

    return <div>{/* Component JSX */}</div>;
}
```

**PluginContext type:**

```typescript
interface PluginContext {
    tenantId: string;
    workspaceId: string;
    userId: string;
    userEmail: string;
    userRole: 'admin' | 'member' | 'viewer';
    installationId: string;
    pluginId: string;
    pluginVersion: string;
    locale: string;
    timezone: string;
    now(): Date;           // Current time in workspace timezone
    utcnow(): Date;        // Current UTC time
}
```

### 14.2 Hook: `useAmcApi()`

```typescript
import { useAmcApi } from '@amc/sdk';

function ContactList() {
    const api = useAmcApi();
    const [contacts, setContacts] = useState<Contact[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function load() {
            const result = await api.crm.contacts.list({
                limit: 50,
                filters: { status: 'active' },
                sort: '-created_at'
            });
            setContacts(result.items);
            setLoading(false);
        }
        load();
    }, []);

    if (loading) return <Spinner />;

    return (
        <ul>
            {contacts.map(c => (
                <li key={c.id}>{c.firstName} {c.lastName} — {c.email}</li>
            ))}
        </ul>
    );
}
```

**Typed API methods:**

```typescript
// Read operations
api.crm.contacts.get(id: string): Promise<Contact>
api.crm.contacts.list(params?: ListParams): Promise<PaginatedResponse<Contact>>
api.crm.contacts.count(filters?: Filters): Promise<number>
api.crm.contacts.search(query: string): Promise<PaginatedResponse<Contact>>

// Write operations
api.crm.contacts.create(data: CreateContactInput): Promise<Contact>
api.crm.contacts.update(id: string, data: UpdateContactInput): Promise<Contact>
api.crm.contacts.delete(id: string): Promise<void>

// Same pattern for all entities:
// api.crm.companies.*
// api.crm.deals.*
// api.marketing.campaigns.*
// api.marketing.emails.*
// api.projects.tasks.*
// api.knowledge.documents.*
// api.analytics.reports.*
// api.automation.workflows.*
// api.ai.*
```

### 14.3 Hook: `useAmcEvent()`

```typescript
import { useAmcEvent } from '@amc/sdk';

function ContactActivityFeed() {
    const [events, setEvents] = useState<Event[]>([]);

    // Subscribe to events — automatically cleaned up on unmount
    useAmcEvent('crm.contact.created', async (event: CloudEvent<Contact>) => {
        setEvents(prev => [{
            type: 'created',
            contact: event.data,
            timestamp: event.time
        }, ...prev]);
    });

    useAmcEvent('crm.contact.updated', async (event: CloudEvent<ContactChange>) => {
        setEvents(prev => [{
            type: 'updated',
            contact: event.data.after,
            changes: getChangedFields(event.data.before, event.data.after),
            timestamp: event.time
        }, ...prev]);
    });

    // Filtered subscription
    useAmcEvent('campaign.sent', async (event: CloudEvent<Campaign>) => {
        if (event.data.type === 'email') {
            console.log('Email campaign sent:', event.data.name);
        }
    }, { filters: { type: 'email' } });

    // Dynamic subscribe/unsubscribe
    const { subscribe, unsubscribe } = useAmcEventSystem();

    useEffect(() => {
        const handler = async (event: CloudEvent) => {
            console.log('Deal won:', event.data.name);
        };
        subscribe('crm.deal.won', handler);
        return () => unsubscribe('crm.deal.won', handler);
    }, []);
}
```

### 14.4 Hooks: `useAmcCurrentUser()` and `useAmcCurrentWorkspace()`

```typescript
import { useAmcCurrentUser, useAmcCurrentWorkspace } from '@amc/sdk';

function UserProfile() {
    const user = useAmcCurrentUser();
    // Returns: { id, email, firstName, lastName, role, avatarUrl, locale }

    return (
        <div>
            <img src={user.avatarUrl} alt={user.firstName} />
            <h3>{user.firstName} {user.lastName}</h3>
            <p>{user.email} — {user.role}</p>
        </div>
    );
}

function WorkspaceInfo() {
    const workspace = useAmcCurrentWorkspace();
    // Returns: { id, name, slug, tier, logoUrl, timezone, locale }

    return (
        <div>
            <h2>{workspace.name}</h2>
            <p>Tier: {workspace.tier} | Timezone: {workspace.timezone}</p>
        </div>
    );
}
```

### 14.5 Reusable UI Components

```typescript
import {
    AmcDataTable,
    AmcForm,
    AmcModal,
    AmcDashboardCard,
    AmcButton,
    AmcFormField,
    AmcSelect,
    AmcDatePicker,
    AmcFileUpload,
    AmcToast,
    AmcSpinner,
    AmcEmptyState,
    AmcErrorBoundary,
    AmcBreadcrumbs,
    AmcTabs,
    AmcBadge,
    AmcAvatar,
    AmcTooltip,
    AmcConfirmDialog,
} from '@amc/sdk/components';

// AmcDataTable — Typed data table with built-in pagination, sorting, filtering
function ContactsTable() {
    const api = useAmcApi();

    return (
        <AmcDataTable<Contact>
            columns={[
                { key: 'firstName', title: 'First Name', sortable: true },
                { key: 'lastName', title: 'Last Name', sortable: true },
                { key: 'email', title: 'Email', sortable: true },
                {
                    key: 'status',
                    title: 'Status',
                    render: (value: string) => (
                        <AmcBadge variant={value === 'active' ? 'success' : 'neutral'}>
                            {value}
                        </AmcBadge>
                    )
                },
                {
                    key: 'id',
                    title: 'Actions',
                    render: (_: string, row: Contact) => (
                        <AmcButton size="sm" onClick={() => handleEdit(row)}>
                            Edit
                        </AmcButton>
                    )
                }
            ]}
            fetchData={(params) => api.crm.contacts.list(params)}
            pageSize={25}
            selectable
            onSelectionChange={(selected) => console.log(selected)}
        />
    );
}

// AmcForm — Form with validation
function SettingsForm() {
    const { storage } = useAmcPlugin();
    const [values, setValues] = useState({ webhookUrl: '', channel: '' });

    const handleSubmit = async (formData: Record<string, any>) => {
        await storage.set('webhook_url', formData.webhookUrl);
        await storage.set('channel', formData.channel);
        AmcToast.show({ message: 'Settings saved!', type: 'success' });
    };

    return (
        <AmcForm
            initialValues={values}
            onSubmit={handleSubmit}
            validation={{
                webhookUrl: [
                    (v: string) => v.startsWith('https://') || 'Must start with https://'
                ]
            }}
        >
            <AmcFormField
                name="webhookUrl"
                label="Webhook URL"
                help="The Slack incoming webhook URL"
            >
                <input type="url" />
            </AmcFormField>

            <AmcFormField name="channel" label="Default Channel">
                <input type="text" placeholder="#general" />
            </AmcFormField>

            <AmcButton type="submit">Save</AmcButton>
        </AmcForm>
    );
}

// AmcModal — Accessible modal dialogs
function ConfirmActionModal({ isOpen, onClose, onConfirm, itemName }) {
    return (
        <AmcModal
            isOpen={isOpen}
            onClose={onClose}
            title="Confirm Action"
            size="sm"
        >
            <p>Are you sure you want to delete <strong>{itemName}</strong>?</p>
            <p>This action cannot be undone.</p>

            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
                <AmcButton variant="secondary" onClick={onClose}>Cancel</AmcButton>
                <AmcButton variant="danger" onClick={onConfirm}>Delete</AmcButton>
            </div>
        </AmcModal>
    );
}

// AmcDashboardCard — Wrapper for dashboard widgets
function StatsWidget() {
    const api = useAmcApi();
    const [stats, setStats] = useState(null);

    useEffect(() => {
        api.crm.contacts.count({ filters: { status: 'active' } }).then(count => {
            setStats({ activeContacts: count });
        });
    }, []);

    return (
        <AmcDashboardCard
            title="Contact Stats"
            loading={!stats}
            refreshInterval={60000}
            onRefresh={() => window.location.reload()}
            headerActions={
                <AmcButton size="sm" variant="ghost">View All</AmcButton>
            }
        >
            {stats && (
                <div className="stats-grid">
                    <div className="stat">
                        <span className="stat-value">{stats.activeContacts}</span>
                        <span className="stat-label">Active Contacts</span>
                    </div>
                </div>
            )}
        </AmcDashboardCard>
    );
}
```

### 14.6 Storage API (TypeScript)

```typescript
import { useAmcPlugin } from '@amc/sdk';

function useStorageExample() {
    const { storage } = useAmcPlugin();

    // ── Storage Operations ──

    const config = await storage.get('config_key');
    // Returns: any | null

    await storage.set('config_key', { nested: 'value' });
    await storage.set('temp_key', 'expiring', { ttl: 3600 }); // 1 hour TTL

    const keys = await storage.keys();
    // Returns: string[]

    const prefixed = await storage.keys({ prefix: 'config_' });

    await storage.delete('temp_key');

    const exists = await storage.exists('config_key');
    // Returns: boolean

    const usage = await storage.usage();
    // Returns: { keyCount: number, totalBytes: number }

    await storage.clear();

    // ── Secrets Storage ──

    await storage.setSecret('api_key', 'sk_live_xxx');
    const apiKey = await storage.getSecret('api_key');
    await storage.deleteSecret('api_key');

    // ── Counter Operations ──

    const count = await storage.increment('page_views');
    const countBy5 = await storage.increment('page_views', 5);
    const decremented = await storage.decrement('credits');
}
```

### 14.7 Billing API (TypeScript)

```typescript
import { useAmcPlugin } from '@amc/sdk';

function useBillingExample() {
    const { billing } = useAmcPlugin();

    // Report usage
    await billing.report('api_calls', 1, { endpoint: '/analyze' });

    // Batch report
    await billing.reportBatch([
        { metric: 'api_calls', value: 1 },
        { metric: 'ai_tokens', value: 150 },
    ]);

    // Get usage
    const usage = await billing.getUsage('api_calls');
    // Returns: { total: number, unit: string }

    const monthly = await billing.getUsage('api_calls', { period: 'current_month' });

    // Get all usage
    const allUsage = await billing.getAllUsage();
    // Returns: Record<string, { total: number, unit: string }>

    // Subscription info
    const subscription = await billing.getSubscription();
    // Returns: { active: boolean, tier: string, nextBillingDate: string }
}
```

### 14.8 Logging API (TypeScript)

```typescript
import { useAmcPlugin } from '@amc/sdk';

function useLoggingExample() {
    const { logger } = useAmcPlugin();

    logger.debug('Debug message', { function: 'example', iteration: 42 });
    logger.info('Operation completed', {
        operation: 'data_sync',
        recordsProcessed: 1000
    });
    logger.warn('Configuration missing', {
        key: 'api_key',
        feature: 'slack_integration'
    });
    logger.error('Request failed', {
        contactId: 'c_123',
        errorCode: 'TIMEOUT'
    });
    logger.critical('Data integrity violation', {
        entity: 'contact',
        entityId: 'c_123'
    });

    // Metrics
    logger.metric('api_latency_ms', 245, { endpoint: '/analyze' });
}
```

### 14.9 Registration Pattern

```typescript
// index.ts — Plugin entry point
import { registerPlugin } from '@amc/sdk';
import { ContactSidebar } from './components/ContactSidebar';
import { AnalyticsWidget } from './components/AnalyticsWidget';
import { PluginSettings } from './components/PluginSettings';
import { onContactCreated, onCampaignSent } from './handlers';
import { sentimentAnalyze } from './tools';

registerPlugin({
    // ── Identity ──
    id: 'com.example.my-plugin',
    name: 'My Plugin',
    version: '1.0.0',

    // ── UI Components ──
    // Map component names to implementations and locations
    components: {
        ContactSidebar: {
            component: ContactSidebar,
            locations: ['sidebar.crm'],
            title: 'My Plugin',
            icon: 'puzzle',
            priority: 10,
        },
        AnalyticsWidget: {
            component: AnalyticsWidget,
            locations: ['dashboard.widget'],
            title: 'Campaign Overview',
            size: 'md',
        },
        PluginSettings: {
            component: PluginSettings,
            locations: ['settings.plugin'],
            title: 'My Plugin Settings',
            icon: 'cog',
        },
    },

    // ── AI Tools ──
    tools: [sentimentAnalyze],

    // ── Modals ──
    modals: {
        'confirm-action': ConfirmActionModal,
        'data-preview': DataPreviewModal,
    },

    // ── Event Handlers ──
    handlers: {
        'crm.contact.created': onContactCreated,
        'campaign.sent': onCampaignSent,
    },

    // ── Lifecycle ──
    onInstall: async () => {
        console.log('Plugin installed');
    },
    onUninstall: async () => {
        console.log('Plugin uninstalled');
    },
    onEnable: async () => {
        console.log('Plugin enabled');
    },
    onDisable: async () => {
        console.log('Plugin disabled');
    },
});
```

### 14.10 Error Handling

```typescript
import { AmcErrorBoundary } from '@amc/sdk/components';

// Wrap plugin components with error boundary
function PluginWidget() {
    return (
        <AmcErrorBoundary
            fallback={({ error, resetError }) => (
                <div className="error-state">
                    <h3>Something went wrong</h3>
                    <p>{error.message}</p>
                    <button onClick={resetError}>Retry</button>
                </div>
            )}
        >
            <MyWidgetContent />
        </AmcErrorBoundary>
    );
}
```

**Error types:**

```typescript
// Permission errors
try {
    await api.crm.contacts.delete(id);
} catch (error) {
    if (error instanceof PermissionDeniedError) {
        logger.warn('Permission denied for contact deletion');
        showPermissionWarning();
    }
}

// Rate limiting
try {
    await api.crm.contacts.list();
} catch (error) {
    if (error instanceof RateLimitError) {
        logger.info('Rate limited, backing off');
        await delay(error.retryAfter * 1000);
    }
}

// Validation errors
try {
    await api.crm.contacts.create(invalidData);
} catch (error) {
    if (error instanceof ValidationError) {
        // error.fields contains per-field validation messages
        setFormErrors(error.fields);
    }
}

// Quota exceeded
try {
    await storage.set('key', largeValue);
} catch (error) {
    if (error instanceof QuotaExceededError) {
        logger.warn('Storage quota exceeded');
    }
}
```

---

## 15. Example Plugins

### 15.1 Slack Integration Plugin

A full-featured integration that sends AMC events to Slack channels and receives Slack commands.

#### 15.1.1 Project Structure

```
slack-integration/
├── plugin.yaml
├── server.py
├── frontend/
│   ├── index.ts
│   ├── Settings.tsx
│   ├── SlackWidget.tsx
│   └── SendToSlackButton.tsx
├── handlers.py
├── utils.py
├── assets/
│   ├── icon.svg
│   └── screenshots/
│       ├── dashboard-widget.png
│       └── settings-page.png
├── README.md
└── CHANGELOG.md
```

#### 15.1.2 Manifest

```yaml
# plugin.yaml
id: com.amc.slack-integration
name: Slack Integration
version: 2.3.0
type: plugin
description: Send AMC events to Slack channels and receive Slack commands
author: AMC Ecosystem Team
icon: icon.svg

min_amc_version: "1.2.0"

categories:
  - communication
  - productivity
tags:
  - slack
  - notifications
  - messaging

permissions:
  - crm:contact:read
  - crm:contact:write
  - crm:deal:read
  - marketing:campaign:read
  - notification:send
  - workspace:settings:read

hooks:
  - event: crm.contact.created
    handler: notify_contact_created
  - event: crm.deal.won
    handler: notify_deal_won
  - event: campaign.sent
    handler: notify_campaign_sent
  - event: schedule.hourly
    handler: check_health

ui:
  - location: dashboard.widget
    component: SlackWidget
    title: Slack Activity
    size: sm
  - location: settings.plugin
    component: SlackSettings
    title: Slack Integration
    icon: slack
    category: integrations
  - location: toolbar.contacts.list
    component: SendToSlackButton
    title: Send to Slack
    icon: slack
  - location: toolbar.campaign.detail
    component: PostToSlackButton
    title: Post to Slack
    icon: slack

backend:
  entry: server.py
  type: python
  timeout: 30
  async_timeout: 300
  memory: 128

network:
  allow:
    - slack.com
    - hooks.slack.com
    - api.slack.com

billing:
  type: subscription
  price: 4.99
  currency: USD
  billing_interval: monthly
  trial_days: 14
```

#### 15.1.3 Backend Implementation

```python
# server.py
from amc_sdk import Application
from slack_plugin import SlackPlugin

app = Application(plugin_class=SlackPlugin)

if __name__ == "__main__":
    app.run()
```

```python
# slack_plugin.py
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from amc_sdk import AmcPlugin, event_handler, webhook


class SlackPlugin(AmcPlugin):
    """Slack Integration Plugin — sends AMC events to Slack."""

    # ── Lifecycle ──────────────────────────────────────────

    async def on_install(self):
        """Initialize default configuration."""
        await self.storage.set("config", {
            "webhook_url": "",
            "channel": "#notifications",
            "notify_contact_created": True,
            "notify_deal_won": True,
            "notify_campaign_sent": False,
            "bot_token": "",
            "signing_secret": "",
        })
        self.logger.info("Slack plugin installed")

    async def on_enable(self):
        """Register webhook endpoints for Slack Events API."""
        self.register_webhook("/slack/events", self.handle_slack_event, methods=["POST"])
        self.register_webhook("/slack/interactive", self.handle_interactive, methods=["POST"])
        self.logger.info("Slack plugin enabled")

    async def on_disable(self):
        """Clean up on disable."""
        self.logger.info("Slack plugin disabled")

    # ── Event Handlers ─────────────────────────────────────

    @event_handler("crm.contact.created")
    async def notify_contact_created(self, event):
        """Send notification when a new contact is created."""
        config = await self.storage.get("config")
        if not config.get("notify_contact_created"):
            return

        contact = event.data
        await self.send_slack_message(
            channel=config.get("channel", "#notifications"),
            text=f":bust_in_silhouette: *New Contact Created*\n"
                 f"• Name: {contact.first_name} {contact.last_name}\n"
                 f"• Email: {contact.email}\n"
                 f"• Company: {contact.company_name or 'N/A'}\n"
                 f"• <{self._contact_url(contact.id)}|View in AMC>"
        )

    @event_handler("crm.deal.won")
    async def notify_deal_won(self, event):
        """Send notification when a deal is won."""
        config = await self.storage.get("config")
        if not config.get("notify_deal_won"):
            return

        deal = event.data
        await self.send_slack_message(
            channel=config.get("channel", "#notifications"),
            text=f":tada: *Deal Won!*\n"
                 f"• Deal: {deal.name}\n"
                 f"• Amount: ${deal.amount:,.2f}\n"
                 f"• Company: {deal.company_name}\n"
                 f"• Owner: {deal.owner_name}\n"
                 f"• <{self._deal_url(deal.id)}|View in AMC>"
        )

    @event_handler("campaign.sent")
    async def notify_campaign_sent(self, event):
        """Send notification when a campaign is sent."""
        config = await self.storage.get("config")
        if not config.get("notify_campaign_sent"):
            return

        campaign = event.data
        await self.send_slack_message(
            channel=config.get("channel", "#notifications"),
            text=f":email: *Campaign Sent*\n"
                 f"• Campaign: {campaign.name}\n"
                 f"• Recipients: {campaign.recipient_count:,}\n"
                 f"• Type: {campaign.type}\n"
                 f"• <{self._campaign_url(campaign.id)}|View Stats>"
        )

    @event_handler("schedule.hourly")
    async def check_health(self, event):
        """Hourly health check — verify Slack webhook is working."""
        config = await self.storage.get("config")
        webhook_url = config.get("webhook_url", "")
        if webhook_url:
            try:
                await self.send_slack_message(
                    channel=config.get("channel", "#notifications"),
                    text=f":white_check_mark: Slack Integration — Hourly Health Check OK\n"
                         f"• Time: {self.context.now().strftime('%Y-%m-%d %H:%M:%S %Z')}"
                )
            except Exception as e:
                self.logger.error("Health check failed", extra={"error": str(e)})

    # ── Webhook Handlers (Slack Events API) ────────────────

    async def handle_slack_event(self, request):
        """Handle incoming Slack Events API requests."""
        payload = request.json()

        # URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload["challenge"]}

        # Verify signature
        signing_secret = (await self.storage.get("config", {})).get("signing_secret", "")
        if signing_secret and not self._verify_slack_signature(
            request.body,
            request.headers.get("X-Slack-Signature", ""),
            request.headers.get("X-Slack-Request-Timestamp", "")
        ):
            return {"error": "invalid signature"}, 401

        # Process the event
        event_data = payload.get("event", {})
        event_type = event_data.get("type")

        if event_type == "message" and "subtype" not in event_data:
            await self.handle_slack_message(event_data)
        elif event_type == "app_mention":
            await self.handle_app_mention(event_data)

        return {"status": "ok"}

    async def handle_interactive(self, request):
        """Handle Slack interactive components (buttons, modals)."""
        payload = json.loads(request.form().get("payload", "{}"))

        action = payload.get("actions", [{}])[0]
        action_id = action.get("action_id", "")

        if action_id == "view_in_amc":
            # User clicked "View in AMC" button
            entity_url = action.get("value", "")
            return {"response_action": "none"}
        elif action_id == "create_contact":
            # User wants to create a contact from Slack
            await self.open_create_contact_modal(payload["trigger_id"])

        return {"status": "ok"}

    # ── Helper Methods ─────────────────────────────────────

    async def send_slack_message(self, channel: str, text: str):
        """Send a message to a Slack channel via webhook."""
        config = await self.storage.get("config")
        webhook_url = config.get("webhook_url", "")
        if not webhook_url:
            self.logger.warning("Slack webhook URL not configured")
            return

        await self.http.post(webhook_url, json={
            "channel": channel,
            "text": text,
            "mrkdwn": True,
            "unfurl_links": False,
        })

    async def handle_slack_message(self, event_data: dict):
        """Process a Slack message."""
        text = event_data.get("text", "").lower()
        channel = event_data.get("channel")

        if "list contacts" in text:
            contacts = await self.api.crm.contacts.list(limit=5)
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": "*Recent Contacts:*"}}
            ]
            for c in contacts.items:
                blocks.append({
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"• {c.first_name} {c.last_name} — {c.email}"}
                })
            await self.send_slack_block(channel, blocks)

    async def send_slack_block(self, channel: str, blocks: list):
        """Send a block-style message to Slack."""
        config = await self.storage.get("config")
        webhook_url = config.get("webhook_url", "")
        if webhook_url:
            await self.http.post(webhook_url, json={"channel": channel, "blocks": blocks})

    def _verify_slack_signature(self, body: bytes, signature: str, timestamp: str) -> bool:
        """Verify Slack request signature."""
        if not signature or not timestamp:
            return False
        # Check timestamp is within 5 minutes
        try:
            request_time = int(timestamp)
            if abs(datetime.utcnow().timestamp() - request_time) > 300:
                return False
        except ValueError:
            return False

        sig_basestring = f"v0:{timestamp}:".encode() + body
        secret = (self.storage.get("config") or {}).get("signing_secret", "")
        if not secret:
            return False
        my_signature = "v0=" + hmac.new(
            secret.encode(), sig_basestring, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(my_signature, signature)

    def _contact_url(self, contact_id: str) -> str:
        return f"https://{self.context.workspace_id}.amc.io/crm/contacts/{contact_id}"

    def _deal_url(self, deal_id: str) -> str:
        return f"https://{self.context.workspace_id}.amc.io/crm/deals/{deal_id}"

    def _campaign_url(self, campaign_id: str) -> str:
        return f"https://{self.context.workspace_id}.amc.io/marketing/campaigns/{campaign_id}"
```

#### 15.1.4 Frontend Implementation

```typescript
// frontend/index.ts
import { registerPlugin } from '@amc/sdk';
import { SlackSettings } from './Settings';
import { SlackWidget } from './SlackWidget';
import { SendToSlackButton } from './SendToSlackButton';

registerPlugin({
    id: 'com.amc.slack-integration',
    name: 'Slack Integration',
    version: '2.3.0',
    components: {
        SlackWidget: {
            component: SlackWidget,
            locations: ['dashboard.widget'],
            title: 'Slack Activity',
            size: 'sm',
        },
        SlackSettings: {
            component: SlackSettings,
            locations: ['settings.plugin'],
            title: 'Slack Integration',
            icon: 'slack',
            category: 'integrations',
        },
        SendToSlackButton: {
            component: SendToSlackButton,
            locations: ['toolbar.contacts.list'],
            title: 'Send to Slack',
            icon: 'slack',
        },
    },
    handlers: {},
});
```

```typescript
// frontend/Settings.tsx
import React, { useState, useEffect } from 'react';
import { useAmcPlugin } from '@amc/sdk';
import { AmcForm, AmcFormField, AmcButton, AmcToast } from '@amc/sdk/components';

interface SlackConfig {
    webhook_url: string;
    channel: string;
    notify_contact_created: boolean;
    notify_deal_won: boolean;
    notify_campaign_sent: boolean;
    bot_token: string;
    signing_secret: string;
}

export function SlackSettings() {
    const { storage } = useAmcPlugin();
    const [config, setConfig] = useState<SlackConfig | null>(null);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        storage.get('config').then(setConfig);
    }, []);

    const handleSave = async (values: Record<string, any>) => {
        setSaving(true);
        await storage.set('config', values);
        setSaving(false);
        AmcToast.show({ message: 'Settings saved!', type: 'success' });
    };

    const handleTestConnection = async () => {
        setTesting(true);
        try {
            // Trigger a test event
            await fetch('/api/v1/plugins/com.amc.slack-integration/webhook/test', {
                method: 'POST'
            });
            AmcToast.show({ message: 'Test message sent to Slack!', type: 'success' });
        } catch (err) {
            AmcToast.show({ message: 'Failed to send test message', type: 'error' });
        }
        setTesting(false);
    };

    if (!config) return <div>Loading...</div>;

    return (
        <div>
            <h2>Slack Integration Settings</h2>

            <AmcForm initialValues={config} onSubmit={handleSave}>
                <AmcFormField
                    name="webhook_url"
                    label="Webhook URL"
                    help="The incoming webhook URL from Slack"
                    validation={[
                        (v: string) => v.startsWith('https://hooks.slack.com/')
                            || 'Must be a valid Slack webhook URL'
                    ]}
                >
                    <input
                        type="url"
                        placeholder="https://hooks.slack.com/services/..."
                    />
                </AmcFormField>

                <AmcFormField
                    name="channel"
                    label="Default Channel"
                    help="Where notifications will be posted"
                >
                    <input type="text" placeholder="#notifications" />
                </AmcFormField>

                <AmcFormField
                    name="signing_secret"
                    label="Signing Secret"
                    help="From Slack App Credentials (for Events API)"
                    type="password"
                >
                    <input type="password" placeholder="Starts with abcd..." />
                </AmcFormField>

                <h3>Notification Preferences</h3>

                <AmcFormField name="notify_contact_created" label="New Contacts">
                    <input type="checkbox" />
                </AmcFormField>

                <AmcFormField name="notify_deal_won" label="Won Deals">
                    <input type="checkbox" />
                </AmcFormField>

                <AmcFormField name="notify_campaign_sent" label="Campaign Sent">
                    <input type="checkbox" />
                </AmcFormField>

                <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
                    <AmcButton type="submit" loading={saving}>
                        Save Settings
                    </AmcButton>
                    <AmcButton
                        variant="secondary"
                        onClick={handleTestConnection}
                        loading={testing}
                    >
                        Test Connection
                    </AmcButton>
                </div>
            </AmcForm>
        </div>
    );
}
```

### 15.2 AI Sentiment Analyzer

A custom AI tool that analyzes text sentiment and can be invoked by AI agents.

#### 15.2.1 Manifest

```yaml
# plugin.yaml
id: com.amc.sentiment-analyzer
name: AI Sentiment Analyzer
version: 1.0.0
type: tool
description: Analyzes text sentiment with multi-language support
author: AMC Ecosystem Team
icon: icon.svg

min_amc_version: "1.0.0"

categories:
  - ai
  - analytics
tags:
  - sentiment
  - nlp
  - analysis

permissions:
  - crm:contact:read

backend:
  entry: server.py
  type: python
  timeout: 10
  memory: 128

network:
  allow:
    - api.example-ai.com

billing:
  type: usage-based
  usage_metrics:
    - name: api_calls
      display_name: API Calls
      unit: call
      price_per_unit: 0.01
  minimum_monthly: 4.99
```

#### 15.2.2 Backend Implementation

```python
# server.py
from amc_sdk import Application, AmcPlugin, ai_tool

class SentimentPlugin(AmcPlugin):
    """AI-powered sentiment analysis tool for agents."""

    @ai_tool(
        name="sentiment_analyze",
        description="Analyze the sentiment of a text. Returns positive, negative, or neutral with confidence score.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze"
                },
                "language": {
                    "type": "string",
                    "enum": ["en", "es", "fr", "de", "ja", "zh", "pt", "it", "nl"],
                    "description": "Language code (ISO 639-1)",
                    "default": "en"
                },
                "include_details": {
                    "type": "boolean",
                    "description": "Include detailed breakdown (entities, key phrases)",
                    "default": False
                }
            },
            "required": ["text"]
        }
    )
    async def sentiment_analyze(self, params: dict) -> dict:
        """Analyze sentiment of the given text."""
        text = params["text"]
        language = params.get("language", "en")
        include_details = params.get("include_details", False)

        # Report usage for billing
        await self.billing.report("api_calls", 1)

        # Call external sentiment API
        response = await self.http.post(
            "https://api.example-ai.com/v1/sentiment",
            json={
                "text": text,
                "language": language,
                "include_details": include_details
            },
            headers={"Authorization": f"Bearer {await self._get_api_key()}"}
        )

        result = response.json()

        return {
            "sentiment": result["label"],      # "positive", "negative", "neutral"
            "score": result["score"],            # 0.0 to 1.0
            "confidence": result["confidence"],  # 0.0 to 1.0
            "details": result.get("details", {}),
            "summary": f"Sentiment is {result['label']} "
                      f"(confidence: {result['confidence']:.1%})"
        }

    @ai_tool(
        name="sentiment_batch",
        description="Analyze sentiment for multiple texts in batch",
        parameters={
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of texts to analyze"
                },
                "language": {
                    "type": "string",
                    "default": "en"
                }
            },
            "required": ["texts"]
        }
    )
    async def sentiment_batch(self, params: dict) -> dict:
        """Analyze sentiment for multiple texts."""
        texts = params["texts"]
        language = params.get("language", "en")

        results = []
        for text in texts:
            result = await self.sentiment_analyze({
                "text": text,
                "language": language,
                "include_details": False
            })
            results.append({"text": text, **result})

        return {
            "results": results,
            "overall": self._compute_overall(results),
            "count": len(results)
        }

    def _compute_overall(self, results: list) -> dict:
        """Compute overall sentiment across multiple texts."""
        positive = sum(1 for r in results if r["sentiment"] == "positive")
        negative = sum(1 for r in results if r["sentiment"] == "negative")
        neutral = sum(1 for r in results if r["sentiment"] == "neutral")
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0

        if positive > negative and positive > neutral:
            overall = "positive"
        elif negative > positive and negative > neutral:
            overall = "negative"
        else:
            overall = "neutral"

        return {
            "overall": overall,
            "average_score": round(avg_score, 3),
            "distribution": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral
            }
        }

    async def _get_api_key(self) -> str:
        """Get the external API key from storage."""
        return await self.storage.get_secret("sentiment_api_key") or ""
```

### 15.3 Google Analytics Connector

A dashboard widget + backend sync integration that brings Google Analytics data into AMC.

#### 15.3.1 Manifest

```yaml
id: com.amc.ga4-connector
name: Google Analytics Connector
version: 1.5.0
type: integration
description: Sync Google Analytics 4 data into AMC dashboards and reports
author: AMC Ecosystem Team
icon: ga4-icon.svg

min_amc_version: "1.2.0"

categories:
  - analytics
  - integrations
tags:
  - google
  - analytics
  - ga4
  - reporting

permissions:
  - analytics:report:read
  - analytics:report:write
  - analytics:dashboard:read
  - analytics:dashboard:write
  - workspace:settings:read

hooks:
  - event: schedule.every_15_minutes
    handler: sync_realtime_data
  - event: schedule.hourly
    handler: sync_hourly_data
  - event: schedule.daily
    handler: sync_daily_data
    cron: "0 2 * * *"

ui:
  - location: dashboard.widget
    component: GA4Widget
    title: Google Analytics
    size: lg
  - location: settings.plugin
    component: GA4Settings
    title: Google Analytics
    icon: chart-bar
    category: integrations

backend:
  entry: server.py
  type: python
  timeout: 60
  async_timeout: 300
  memory: 256

network:
  allow:
    - analyticsdata.googleapis.com
    - oauth2.googleapis.com
    - www.googleapis.com

billing:
  type: free
```

#### 15.3.2 Backend (OAuth + Data Sync)

```python
# server.py
from amc_sdk import Application, AmcPlugin, event_handler

class GA4Plugin(AmcPlugin):
    """Google Analytics 4 connector — syncs data into AMC dashboards."""

    async def on_enable(self):
        # Check if OAuth is configured
        tokens = await self.storage.get_secret("ga4_tokens")
        if not tokens:
            self.logger.warning("GA4 not authenticated — sync disabled")

    @event_handler("schedule.every_15_minutes")
    async def sync_realtime_data(self, event):
        """Sync realtime analytics data."""
        tokens = await self.storage.get_secret("ga4_tokens")
        if not tokens:
            return

        property_id = await self.storage.get("ga4_property_id")
        if not property_id:
            return

        # Fetch realtime data
        data = await self._fetch_analytics_data(
            property_id,
            metrics=["activeUsers", "screenPageViews"],
            dimensions=["minutesAgo"],
            limit=5
        )

        # Update AMC dashboard widget
        await self.api.analytics.dashboards.update_widget(
            widget_key="ga4_realtime",
            data={
                "active_users": data.get("activeUsers", 0),
                "page_views": data.get("screenPageViews", 0),
                "updated_at": self.context.utcnow().isoformat()
            }
        )

    @event_handler("schedule.hourly")
    async def sync_hourly_data(self, event):
        """Sync hourly aggregated data."""
        # ... implementation similar to realtime but with hourly aggregation

    @event_handler("schedule.daily")
    async def sync_daily_data(self, event):
        """Sync daily data and create AMC reports."""
        # ... creates AMC analytics reports from GA4 data

    async def _fetch_analytics_data(self, property_id: str, metrics: list,
                                     dimensions: list, limit: int = 10) -> dict:
        """Fetch data from Google Analytics Data API."""
        tokens = await self.storage.get_secret("ga4_tokens")
        access_token = tokens.get("access_token")

        response = await self.http.post(
            f"https://analyticsdata.googleapis.com/v1beta/"
            f"properties/{property_id}:runReport",
            json={
                "metrics": [{"name": m} for m in metrics],
                "dimensions": [{"name": d} for d in dimensions],
                "limit": limit,
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        return response.json()
```

### 15.4 Custom Invoice Template (PDF Generator)

A plugin that generates PDF invoices from AMC deal data and attaches them to deals.

#### 15.4.1 Manifest

```yaml
id: com.amc.invoice-generator
name: Custom Invoice Template
version: 1.2.0
type: extension
description: Generate branded PDF invoices from deal data
author: AMC Ecosystem Team
icon: invoice-icon.svg

min_amc_version: "1.0.0"

categories:
  - productivity
  - crm
tags:
  - invoice
  - pdf
  - billing

permissions:
  - crm:deal:read
  - crm:deal:write
  - crm:contact:read
  - crm:company:read
  - storage:plugin:write

hooks:
  - event: crm.deal.won
    handler: generate_invoice

backend:
  entry: server.py
  type: python
  timeout: 30
  memory: 256

network:
  allow: []  # No external network needed

billing:
  type: one-time
  price: 19.99
  currency: USD
```

#### 15.4.2 Backend

```python
# server.py
from amc_sdk import Application, AmcPlugin, event_handler
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

class InvoicePlugin(AmcPlugin):
    """Generates PDF invoices from won deals."""

    @event_handler("crm.deal.won")
    async def generate_invoice(self, event):
        """Generate a PDF invoice when a deal is won."""
        deal = event.data

        # Fetch related data
        contact = await self.api.crm.contacts.get(deal.contact_id)
        company = await self.api.crm.companies.get(deal.company_id)

        # Generate invoice PDF
        invoice_path = await self._create_invoice_pdf(deal, contact, company)

        # Store the invoice
        await self.api.storage.upload(
            path=f"invoices/{deal.id}/invoice.pdf",
            file_path=invoice_path
        )

        # Add note to deal
        await self.api.crm.deals.add_note(
            deal_id=deal.id,
            content=f"Invoice generated for ${deal.amount:,.2f} — "
                    f"attached to deal on {self.context.now().strftime('%Y-%m-%d')}"
        )

        self.logger.info(f"Invoice generated for deal {deal.id}")

    async def _create_invoice_pdf(self, deal, contact, company) -> str:
        """Create a PDF invoice using ReportLab."""
        temp_dir = os.environ.get("AMC_TEMP_DIR", "/tmp")
        path = os.path.join(temp_dir, f"invoice-{deal.id}.pdf")

        c = canvas.Canvas(path, pagesize=A4)
        c.setFont("Helvetica-Bold", 24)
        c.drawString(50, 800, "INVOICE")

        c.setFont("Helvetica", 12)
        c.drawString(50, 760, f"Invoice #: INV-{deal.id[-8:]}")
        c.drawString(50, 740, f"Date: {self.context.now().strftime('%B %d, %Y')}")

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, 700, "Bill To:")
        c.setFont("Helvetica", 12)
        c.drawString(50, 680, f"{contact.first_name} {contact.last_name}")
        c.drawString(50, 660, contact.email)
        c.drawString(50, 640, company.name)

        # Line items
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, 590, "Line Items")
        c.setFont("Helvetica", 12)
        c.drawString(50, 570, deal.name or deal.description)
        c.drawString(450, 570, f"${deal.amount:,.2f}")

        # Total
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 520, f"Total: ${deal.amount:,.2f}")

        c.showPage()
        c.save()

        return path
```

### 15.5 Multi-language Translation AI Tool

An AI tool that translates content between languages, usable by AI agents.

#### 15.5.1 Manifest

```yaml
id: com.amc.translation-tool
name: Multi-language Translation
version: 1.0.0
type: tool
description: Translate content between 50+ languages using AI
author: AMC Ecosystem Team
icon: translate-icon.svg

min_amc_version: "1.0.0"

categories:
  - ai
  - productivity
tags:
  - translation
  - i18n
  - localization

permissions:
  - ai:credits:read
  - ai:credits:consume

backend:
  entry: server.py
  type: python
  timeout: 30
  memory: 128

network:
  allow:
    - api.example-translate.com

billing:
  type: usage-based
  usage_metrics:
    - name: characters_translated
      display_name: Characters Translated
      unit: character
      price_per_unit: 0.00002  # $0.02 per 1000 chars
  minimum_monthly: 0
```

#### 15.5.2 Backend

```python
# server.py
from amc_sdk import Application, AmcPlugin, ai_tool

LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "ru": "Russian",
    "ja": "Japanese", "ko": "Korean", "zh": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)", "ar": "Arabic", "hi": "Hindi",
    "tr": "Turkish", "pl": "Polish", "sv": "Swedish", "da": "Danish",
    "fi": "Finnish", "no": "Norwegian", "cs": "Czech", "hu": "Hungarian",
    "ro": "Romanian", "th": "Thai", "vi": "Vietnamese", "id": "Indonesian",
    "ms": "Malay", "uk": "Ukrainian", "el": "Greek", "he": "Hebrew",
}

class TranslationPlugin(AmcPlugin):
    """Multi-language translation tool for AI agents."""

    @ai_tool(
        name="translate_text",
        description="Translate text from one language to another. Supports 50+ languages.",
        parameters={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to translate"
                },
                "source_language": {
                    "type": "string",
                    "enum": list(LANGUAGES.keys()),
                    "description": "Source language code (auto-detect if empty)"
                },
                "target_language": {
                    "type": "string",
                    "enum": list(LANGUAGES.keys()),
                    "description": "Target language code"
                },
                "preserve_formatting": {
                    "type": "boolean",
                    "description": "Preserve markdown/HTML formatting in translation",
                    "default": True
                }
            },
            "required": ["text", "target_language"]
        }
    )
    async def translate_text(self, params: dict) -> dict:
        """Translate text between languages."""
        text = params["text"]
        target = params["target_language"]
        source = params.get("source_language", "")
        preserve = params.get("preserve_formatting", True)

        # Validate
        if target not in LANGUAGES:
            return {"error": f"Unsupported target language: {target}"}

        # Report usage
        char_count = len(text)
        await self.billing.report("characters_translated", char_count)

        # Call translation API
        response = await self.http.post(
            "https://api.example-translate.com/v1/translate",
            json={
                "text": text,
                "source_lang": source or None,
                "target_lang": target,
                "preserve_formatting": preserve,
            },
            headers={"Authorization": f"Bearer {await self._get_api_key()}"}
        )

        result = response.json()

        return {
            "translated_text": result["translation"],
            "detected_source_language": result.get("detected_source", source),
            "source_language_name": LANGUAGES.get(source, "Auto-detected"),
            "target_language_name": LANGUAGES[target],
            "character_count": char_count,
            "summary": f"Translated {char_count} characters "
                      f"from {result.get('detected_source', source) or 'auto-detected'} "
                      f"to {LANGUAGES[target]}"
        }

    @ai_tool(
        name="batch_translate",
        description="Translate multiple texts in batch for efficiency",
        parameters={
            "type": "object",
            "properties": {
                "texts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of texts to translate"
                },
                "target_language": {
                    "type": "string",
                    "description": "Target language code"
                },
                "source_language": {
                    "type": "string",
                    "description": "Source language code (optional, auto-detect if empty)"
                }
            },
            "required": ["texts", "target_language"]
        }
    )
    async def batch_translate(self, params: dict) -> dict:
        """Translate multiple texts in batch."""
        texts = params["texts"]
        target = params["target_language"]
        source = params.get("source_language", "")

        total_chars = sum(len(t) for t in texts)
        await self.billing.report("characters_translated", total_chars)

        response = await self.http.post(
            "https://api.example-translate.com/v1/batch-translate",
            json={
                "texts": texts,
                "source_lang": source or None,
                "target_lang": target,
            },
            headers={"Authorization": f"Bearer {await self._get_api_key()}"}
        )

        result = response.json()
        return {
            "translations": result["translations"],
            "count": len(result["translations"]),
            "total_characters": total_chars
        }

    @ai_tool(
        name="get_supported_languages",
        description="Get the list of supported languages for translation",
        parameters={
            "type": "object",
            "properties": {}
        }
    )
    async def get_supported_languages(self, params: dict) -> dict:
        """Return supported languages."""
        return {
            "languages": [
                {"code": code, "name": name}
                for code, name in sorted(LANGUAGES.items(), key=lambda x: x[1])
            ],
            "count": len(LANGUAGES)
        }

    async def _get_api_key(self) -> str:
        return await self.storage.get_secret("translation_api_key") or ""
```

---

## Appendices

### Appendix A: Marketplace API Reference

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/marketplace/plugins` | GET | List marketplace plugins | Public (filtered) |
| `/api/v1/marketplace/plugins/{id}` | GET | Get plugin details | Public |
| `/api/v1/marketplace/plugins/{id}/versions` | GET | List plugin versions | Public |
| `/api/v1/marketplace/plugins/{id}/reviews` | GET | List plugin reviews | Public |
| `/api/v1/marketplace/categories` | GET | List categories | Public |
| `/api/v1/marketplace/search` | GET | Search plugins | Public |
| `/api/v1/marketplace/developer/plugins` | GET/POST | Developer plugin management | Developer |
| `/api/v1/marketplace/developer/plugins/{id}` | GET/PATCH/DELETE | Single plugin management | Developer |
| `/api/v1/marketplace/developer/plugins/{id}/versions` | POST | Upload version | Developer |
| `/api/v1/marketplace/developer/plugins/{id}/submit` | POST | Submit for review | Developer |
| `/api/v1/marketplace/developer/plugins/{id}/publish` | POST | Publish approved version | Developer |
| `/api/v1/marketplace/developer/analytics/installs` | GET | Install analytics | Developer |
| `/api/v1/marketplace/developer/analytics/revenue` | GET | Revenue analytics | Developer |
| `/api/v1/marketplace/install` | POST | Install plugin | Admin |
| `/api/v1/marketplace/install/{id}` | DELETE | Uninstall plugin | Admin |
| `/api/v1/marketplace/install/{id}/enable` | POST | Enable plugin | Admin |
| `/api/v1/marketplace/install/{id}/disable` | POST | Disable plugin | Admin |

### Appendix B: SDK Package Contents

**Python SDK (`amc-sdk`):**

```
amc_sdk/
├── __init__.py              # Public API exports
├── application.py           # Application entry point
├── plugin.py                # AmcPlugin base class
├── context.py               # PluginContext
├── api/
│   ├── __init__.py
│   ├── client.py            # AMCApiClient
│   ├── crm.py               # CRM endpoints
│   ├── marketing.py         # Marketing endpoints
│   ├── projects.py          # Projects endpoints
│   ├── knowledge.py         # Knowledge endpoints
│   ├── analytics.py         # Analytics endpoints
│   ├── automation.py        # Automation endpoints
│   ├── ai.py                # AI endpoints
│   └── storage.py           # Storage endpoints
├── events/
│   ├── __init__.py
│   ├── system.py            # Event system
│   └── decorators.py        # @event_handler decorator
├── storage.py               # Storage API
├── billing.py               # Billing metering API
├── logging.py               # Logger
├── webhook.py               # Webhook registration
├── scheduler.py             # Scheduler
├── http.py                  # HTTP client
└── models/
    ├── __init__.py
    ├── crm.py               # Contact, Deal, Company, etc.
    ├── marketing.py         # Campaign, Email, etc.
    └── common.py            # PaginatedResponse, CloudEvent, etc.
```

**TypeScript SDK (`@amc/sdk`):**

```
@amc/sdk/
├── index.ts                    # Public API exports
├── plugin.ts                   # registerPlugin()
├── hooks/
│   ├── useAmcPlugin.ts
│   ├── useAmcApi.ts
│   ├── useAmcEvent.ts
│   ├── useAmcCurrentUser.ts
│   └── useAmcCurrentWorkspace.ts
├── api/
│   ├── client.ts
│   ├── crm.ts
│   ├── marketing.ts
│   ├── projects.ts
│   ├── knowledge.ts
│   ├── analytics.ts
│   ├── automation.ts
│   ├── ai.ts
│   └── storage.ts
├── storage.ts
├── billing.ts
├── logging.ts
├── events.ts
├── components/
│   ├── index.ts
│   ├── AmcDataTable.tsx
│   ├── AmcForm.tsx
│   ├── AmcModal.tsx
│   ├── AmcDashboardCard.tsx
│   ├── AmcButton.tsx
│   ├── AmcFormField.tsx
│   ├── AmcErrorBoundary.tsx
│   ├── AmcToast.tsx
│   ├── ShadowRoot.tsx
│   └── ...
└── types/
    ├── index.ts
    ├── crm.ts
    ├── marketing.ts
    └── events.ts
```

### Appendix C: Glossary

| Term | Definition |
|------|------------|
| **AMC** | Aegis Marketing Cloud |
| **Developer** | A registered marketplace developer who creates and publishes plugins |
| **Extension** | Any marketplace listing that extends AMC functionality |
| **Installation** | A specific instance of a plugin installed in a workspace |
| **Listing** | A marketplace entry (plugin, tool, agent, theme, etc.) |
| **Manifest** | The metadata file (`plugin.yaml`) that describes a plugin |
| **Marketplace** | The store where plugins are listed, discovered, and installed |
| **Plugin** | The most comprehensive extension type with UI + backend |
| **Sandbox** | Isolated execution environment for plugin code |
| **SDK** | Software Development Kit for building plugins |
| **Tenant** | An organization/customer in the multi-tenant platform |
| **Workspace** | A project/team space within a tenant |

### Appendix D: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | June 2026 | Platform & Ecosystem Team | Initial release |
