# Volume 4: System Architecture

> **Document Version:** 1.0  
> **Classification:** Internal — Engineering  
> **Date:** June 2026  
> **Author:** Architecture Team  
> **Status:** ✅ Complete

---

## Table of Contents

1. [Architecture Overview & Philosophy](#1-architecture-overview--philosophy)
2. [High-Level Architecture Diagram](#2-high-level-architecture-diagram)
3. [Presentation Layer](#3-presentation-layer)
4. [API Gateway Layer](#4-api-gateway-layer)
5. [Service Layer](#5-service-layer)
6. [AI Layer Architecture](#6-ai-layer-architecture)
7. [Data Layer](#7-data-layer)
8. [n8n Integration Architecture](#8-n8n-integration-architecture)
9. [Scalability & Performance](#9-scalability--performance)
10. [High Availability Design](#10-high-availability-design)
11. [Deployment Architecture](#11-deployment-architecture)
12. [Observability Architecture](#12-observability-architecture)
13. [Security Architecture](#13-security-architecture)
14. [Technology Rationale](#14-technology-rationale)

---

## 1. Architecture Overview & Philosophy

### 1.1 Architectural Style: Microservices + Modular Monolith Hybrid

AMC employs a **hybrid architecture** that combines the organizational clarity of a **modular monolith** with the scalability boundaries of **microservices**. This is not a compromise — it is a deliberate strategy to match architectural complexity to the actual needs of each subsystem.

#### The Rationale

| Dimension | Modular Monolith | Microservices | AMC Approach |
|-----------|-----------------|---------------|--------------|
| **Development velocity** | High — single deployable, shared types | Low — cross-service coordination overhead | Monolith for core business logic (CRM, Marketing, Projects) |
| **Scalability** | Coarse-grained | Fine-grained per service | Microservices for hot paths (AI inference, media processing, notifications) |
| **Team autonomy** | Requires disciplined module boundaries | Natural team-per-service | Monolith + clear bounded contexts; extract to microservice when needed |
| **Operational complexity** | Low | High (service mesh, observability, CI/CD per service) | Start simple, split when scaling pressure demands it |

#### The Hybrid Model

```
┌─────────────────────────────────────────────────────────┐
│                   API Gateway (FastAPI)                   │
└──────────┬──────────┬──────────┬────────────┬───────────┘
           │          │          │            │
┌──────────▼──┐ ┌─────▼─────┐ ┌▼──────────┐ ┌▼───────────┐
│  Modular    │ │ Extracted │ │  AI Layer  │ │Infrastructure│
│  Monolith   │ │Microservices│ │  (Agents)  │ │ Services    │
│             │ │           │ │            │ │             │
│ • CRM       │ │ • Auth    │ │ • Hermes   │ │ • n8n       │
│ • Marketing │ │ • Billing │ │ • Orchestr.│ │ • Media     │
│ • Projects  │ │ • Notif.  │ │ • Memory   │ │ • Analytics │
│ • Knowledge │ │ • Admin   │ │ • NIM      │ │ • Marketplace│
└─────────────┘ └───────────┘ └────────────┘ └─────────────┘
```

**Migration path:** Every module in the monolith is built behind a **service interface** (Python Protocol/ABC). When a module demands independent scaling — e.g., the AI layer's inference load exceeds the monolith's deployment capacity — it is extracted into a standalone service with zero changes to callers.

### 1.2 Design Principles

#### API-First

Every capability in AMC is exposed through a well-defined API before any UI is built. The API contract is the source of truth.

- **Contract-driven development:** OpenAPI 3.1 (REST) + GraphQL schema (Strawberry) are authored alongside feature specs
- **UI is a client:** The Next.js frontend consumes the same APIs as third-party integrations, AI agents, and n8n workflows
- **Forward compatibility:** All API changes are additive for at least one major version; breaking changes are signaled via the `Sunset` header 12+ months before deprecation

#### Tenant-Isolated

Multi-tenancy is not an afterthought — it is the default operating mode of every layer.

- **Database:** Row-Level Security (RLS) on PostgreSQL — every query is scoped to `tenant_id` by policy, not by application code
- **Cache:** Redis key namespacing per tenant (`tenant:<id>:<key>`)
- **AI Memory:** Qdrant collections sharded by `tenant_id`
- **Object Storage:** MinIO bucket per tenant with IAM-style policies
- **Workflows:** n8n workflows tagged with `owner_workspace_id` — execution context is tenant-scoped
- **Agents:** Agent instances are created per-workspace with isolated state

#### Observability-Native

Observability is not bolted on — it is built into every service, every middleware, every agent.

- **Every request** carries a correlation ID (W3C `traceparent`) from API gateway through every service
- **Every log** is structured JSON with `service`, `tenant_id`, `trace_id`, `span_id`, and `duration_ms`
- **Every metric** is tagged with `service`, `endpoint`, `tenant_tier` (but never raw `tenant_id` to avoid high-cardinality)
- **Every agent action** is recorded as an event trace in the audit log
- **Default dashboards** for service health, business metrics, and cost per tenant ship with the platform

#### Event-Driven

Synchronous request-response is reserved for read operations and simple commands. All cross-module coordination, state changes, and long-running operations use events.

```
┌──────────┐   ┌──────────────┐   ┌───────────┐
│ Service A │──►│   RabbitMQ   │──►│ Service B │
│ (emits)   │   │  (exchange)  │   │ (consumes)│
└──────────┘   └──────────────┘   └───────────┘
                    │
                    ▼
              ┌───────────┐
              │ Dead Letter│──► Retry/DLQ processing
              │ Queue      │
              └───────────┘
```

Event types:
- **Domain events:** `campaign.launched`, `contact.created`, `invoice.paid`
- **Integration events:** `n8n.workflow.completed`, `media.processed`
- **Observability events:** `ai.inference.completed`, `cache.miss`
- **Lifecycle events:** `tenant.provisioned`, `user.invited`

---

## 2. High-Level Architecture Diagram

The following Mermaid diagram shows the complete system architecture from presentation through infrastructure:

```mermaid
graph TB
    %% ── Presentation Layer ──
    subgraph Presentation["Presentation Layer"]
        NEXT["Next.js 14<br/>App Router"]
        PWA["PWA Service Worker<br/>Offline Cache + Background Sync"]
        WS["WebSocket / SSE<br/>Real-time Updates"]
        MD["Atomic Design<br/>Component Library"]
    end

    %% ── CDN / Edge ──
    CDN["CDN (CloudFront / Cloudflare)"]

    %% ── API Gateway Layer ──
    subgraph Gateway["API Gateway Layer"]
        FASTAPI["FastAPI Gateway"]
        GRAPHQL["GraphQL (Strawberry)"]
        MIDDLEWARE["Middleware Chain"]
        AUTH["Auth<br/>Middleware"]
        TENANT["Tenant<br/>Resolution"]
        RATE["Rate<br/>Limiting"]
        LOG["Logging &<br/>Tracing"]
        CORS["CORS & CSP"]
    end

    %% ── Service Layer ──
    subgraph Services["Service Layer"]
        MONOLITH["Modular Monolith"]
        CRM["CRM<br/>Module"]
        MKTG["Marketing<br/>Module"]
        PROJ["Projects<br/>Module"]
        KNOW["Knowledge<br/>Module"]

        EXTRACTED["Extracted Microservices"]
        AUTH_SVC["auth-service"]
        BILL["billing-service"]
        NOTIF["notification-service"]
        ADMIN["admin-service"]

        AI_SVC["ai-service<br/>(Orchestrator)"]
        MEDIA["media-service"]
        ANALYTICS["analytics-service"]
        MKT_PLACE["marketplace-service"]
        N8N_SVC["automation-service<br/>(n8n wrapper)"]
    end

    %% ── AI Layer ──
    subgraph AI["AI Layer"]
        HERMES["Hermes Agent<br/>Framework"]
        ORCH["Agent Orchestrator<br/>Scheduler + Work Queue"]
        AGENTS["Agent Pool<br/>(Marketing Director, SEO,<br/>Content Writer, ...)"]
        MEMORY["Memory Layer<br/>Short-term: Redis<br/>Long-term: Qdrant"]
        TOOLS["Tool Registry"]
        NIM["NVIDIA NIM<br/>Inference Endpoint"]
        PROVIDER["AI Provider<br/>Abstraction Layer"]
    end

    %% ── Data Layer ──
    subgraph Data["Data Layer"]
        PG[("PostgreSQL<br/>Primary + Replicas")]
        PGBOUNCER["PgBouncer<br/>Connection Pool"]
        REDIS[("Redis<br/>Cache + Pub/Sub + Queue")]
        QDRANT[("Qdrant<br/>Vector Database")]
        MINIO[("MinIO<br/>Object Storage")]
        RABBIT[("RabbitMQ<br/>Message Broker")]
    end

    %% ── Infrastructure ──
    subgraph Infra["Infrastructure & Observability"]
        DOCKER["Docker / Swarm / K8s"]
        GHA["GitHub Actions<br/>CI/CD"]
        PROM["Prometheus<br/>Metrics"]
        GRAF["Grafana<br/>Dashboards + Alerting"]
        LOKI["Loki<br/>Logs"]
        TEMPO["Tempo<br/>Distributed Tracing"]
        VAULT["Vault<br/>Secrets Management"]
        N8N["n8n<br/>Workflow Engine"]
    end

    %% ── Connections ──
    Browser["Browser"] --> CDN
    CDN --> NEXT
    NEXT --> WS
    PWA --> NEXT

    NEXT --> FASTAPI
    NEXT --> GRAPHQL

    FASTAPI --> MIDDLEWARE
    MIDDLEWARE --> AUTH
    MIDDLEWARE --> TENANT
    MIDDLEWARE --> RATE
    MIDDLEWARE --> LOG
    MIDDLEWARE --> CORS

    FASTAPI --> MONOLITH
    FASTAPI --> EXTRACTED
    FASTAPI --> AI_SVC
    FASTAPI --> MEDIA
    FASTAPI --> ANALYTICS
    FASTAPI --> MKT_PLACE

    MONOLITH --> CRM
    MONOLITH --> MKTG
    MONOLITH --> PROJ
    MONOLITH --> KNOW

    AI_SVC --> HERMES
    HERMES --> ORCH
    ORCH --> AGENTS
    AGENTS --> MEMORY
    AGENTS --> TOOLS
    AGENTS --> PROVIDER
    PROVIDER --> NIM

    MONOLITH --> PGBOUNCER
    EXTRACTED --> PGBOUNCER
    PGBOUNCER --> PG

    MONOLITH --> REDIS
    EXTRACTED --> REDIS

    AGENTS --> QDRANT
    KNOW --> QDRANT

    MEDIA --> MINIO
    MONOLITH --> MINIO

    MONOLITH --> RABBIT
    EXTRACTED --> RABBIT
    AI_SVC --> RABBIT
    N8N_SVC --> RABBIT

    N8N_SVC --> N8N

    MONOLITH --> PROM
    EXTRACTED --> PROM
    AI_SVC --> PROM
    N8N_SVC --> PROM

    MONOLITH --> LOKI
    EXTRACTED --> LOKI
    AI_SVC --> LOKI

    MONOLITH --> TEMPO
    EXTRACTED --> TEMPO

    GHA --> DOCKER
    DOCKER --> VAULT

    style Browser fill:#f9f9f9,stroke:#333
    style NEXT fill:#0070f3,color:#fff
    style FASTAPI fill:#009688,color:#fff
    style MONOLITH fill:#673ab7,color:#fff
    style HERMES fill:#e91e63,color:#fff
    style NIM fill:#76b900,color:#fff
    style PG fill:#336791,color:#fff
    style REDIS fill:#dc382d,color:#fff
    style QDRANT fill:#5c2d91,color:#fff
    style MINIO fill:#f05138,color:#fff
    style RABBIT fill:#ff6600,color:#fff
    style PROM fill:#e6522c,color:#fff
    style GRAF fill:#f46800,color:#fff
    style N8N fill:#ea4b71,color:#fff
```

### 2.1 Layer Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **1. Presentation** | Next.js 14 (App Router) + PWA | User interface, server/client components, offline support |
| **2. Edge / CDN** | CloudFront / Cloudflare | Static asset delivery, SSL termination, DDoS protection |
| **3. API Gateway** | FastAPI + Strawberry GraphQL | Request routing, authentication, tenant resolution, rate limiting |
| **4. Service Layer** | Python (modular monolith + extracted microservices) | Business logic; CRM, Marketing, Projects, Knowledge, plus standalone services |
| **5. AI Layer** | Hermes Agents + NVIDIA NIM | Multi-agent orchestration, inference, memory, tool calling |
| **6. Data Layer** | PostgreSQL, Redis, Qdrant, MinIO, RabbitMQ | Persistence, caching, vector search, object storage, messaging |
| **7. Infrastructure** | Docker, GitHub Actions, Prometheus, Grafana, Loki | Deployment, CI/CD, monitoring, logging, alerting |

---

## 3. Presentation Layer

### 3.1 Next.js 14 App Router Architecture

The frontend is built with **Next.js 14** using the **App Router** (`app/` directory), leveraging React Server Components (RSC) as the default rendering strategy. This provides optimal performance out of the box — pages are rendered on the server, streaming HTML to the client with zero client-side JavaScript until interactivity is needed.

#### Project Structure

```
frontend/
├── app/                          # App Router pages
│   ├── (auth)/                   # Auth route group (login, signup, reset-password)
│   │   ├── login/
│   │   ├── signup/
│   │   └── reset-password/
│   ├── (dashboard)/              # Dashboard route group (requires auth)
│   │   ├── dashboard/
│   │   ├── crm/
│   │   ├── marketing/
│   │   ├── projects/
│   │   ├── analytics/
│   │   ├── settings/
│   │   └── ...
│   ├── api/                      # API route handlers (thin BFF layer)
│   │   └── [...proxy]/           # Optional: proxy to FastAPI backend
│   ├── layout.tsx                # Root layout (providers, fonts, meta)
│   └── page.tsx                  # Landing / marketing page
├── components/                   # UI components (Atomic Design)
│   ├── atoms/                    # Button, Input, Label, Icon
│   ├── molecules/                # FormField, Card, SearchBar
│   ├── organisms/                # DataTable, CampaignBuilder, KanbanBoard
│   ├── templates/                # DashboardLayout, SettingsLayout
│   └── pages/                    # Full page compositions
├── lib/                          # Utility functions, API clients, types
│   ├── api/                      # API client (fetch wrapper, GraphQL client)
│   │   ├── client.ts
│   │   ├── queries/              # GraphQL query/mutation definitions
│   │   └── mutations/
│   ├── state/                    # Zustand stores
│   ├── utils/                    # Formatting, validation, helpers
│   └── types/                    # TypeScript types (shared with API schema)
├── hooks/                        # React hooks
│   ├── useAuth.ts
│   ├── useTenant.ts
│   ├── useWebSocket.ts
│   └── usePWA.ts
├── public/                       # Static assets, service worker
│   ├── sw.js                     # Service worker
│   ├── manifest.json             # PWA manifest
│   └── icons/                    # App icons
├── styles/                       # Global styles, CSS modules, Tailwind
│   ├── globals.css
│   └── tailwind.config.ts
├── middleware.ts                 # Next.js middleware (auth checks, redirects)
├── next.config.js
├── package.json
└── tsconfig.json
```

### 3.2 Server Components vs Client Components Strategy

AMC follows a deliberate, performance-first split:

| Rendering Strategy | When to Use | Examples |
|-------------------|-------------|----------|
| **Server Component** (default) | Static content, SEO pages, data fetching without interactivity | Dashboard shells, campaign lists, report snapshots, knowledge base articles |
| **Client Component** (`'use client'`) | Interactivity, browser APIs, lifecycle effects, state hooks | Forms, drag-and-drop campaign builder, real-time analytics charts, modals |
| **Streaming / Suspense** | Progressive rendering of async content | Skeleton-loading campaign analytics while data streams in |
| **ISR (Incremental Static Regeneration)** | Semi-static content that changes infrequently | Marketing pages, pricing tiers, documentation |

**Strategy guidelines:**
- **Push state down:** Client boundaries are as deep in the tree as possible. A page shell is a server component; only the interactive form field is `'use client'`.
- **Compose, don't switch:** Server components can import client components, but not vice versa. Server components wrap client components, passing data as props.
- **Data fetching:** Server components fetch data directly from the API gateway. Client components use React Query or server actions for mutations.

```typescript
// ✅ Server Component (default, no 'use client')
// app/dashboard/campaigns/page.tsx
async function CampaignsPage() {
  const campaigns = await api.getCampaigns(); // Direct fetch on server
  return (
    <div>
      <h1>Campaigns</h1>
      <CampaignList campaigns={campaigns} /> {/* Could be client or server */}
    </div>
  );
}

// ✅ Client Component (only where interactivity is needed)
// 'use client'
function CampaignForm() {
  const [name, setName] = useState('');
  const mutation = useMutation(createCampaign);
  return <form onSubmit={mutation.mutate}>...</form>;
}
```

### 3.3 State Management

AMC uses a **layered state management** approach, choosing the right tool for each type of state:

| State Type | Technology | Rationale |
|------------|-----------|-----------|
| **Server state** (data from API) | TanStack React Query | Caching, deduplication, background refetch, optimistic updates, pagination |
| **Client state** (UI-only) | Zustand | Lightweight (1KB), no boilerplate, works outside React components, middleware for persistence |
| **Form state** | React Hook Form + Zod | Performant form state with schema-based validation |
| **URL state** (params, search) | Next.js `useSearchParams` + `useRouter` | Native to Next.js, shareable URLs for deep linking |
| **GraphQL cache** | Strawberry + urql (or Apollo Client) | Normalized cache for GraphQL queries |

#### Zustand Store Architecture

```typescript
// stores/ui-store.ts — global UI state
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

// stores/workspace-store.ts — current workspace context
interface WorkspaceState {
  currentWorkspaceId: string | null;
  workspaces: Workspace[];
  switchWorkspace: (id: string) => void;
}
```

#### React Query Configuration

```typescript
// lib/api/query-client.ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,          // 30s before background refetch
      gcTime: 5 * 60_000,         // 5min garbage collection
      retry: 2,
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: 0,
      onError: (error) => toast.error(error.message),
    },
  },
});
```

### 3.4 PWA Architecture

AMC is built as a **Progressive Web Application** from day one, ensuring functionality even in offline or low-connectivity scenarios — critical for marketing teams working on-site at events or in transit.

#### Service Worker Lifecycle

```
SW Install ──► Cache Static Assets (App Shell)
     │
     ▼
SW Activate ──► Clean Old Caches
     │
     ▼
SW Fetch ──► Network First (with cache fallback)
     │          ├── Online → Serve from network, cache response
     │          └── Offline → Serve from cache
     │
     ▼
Background Sync ──► Queue mutations made offline
     │                  ├── On connectivity restore
     │                  └── Replay queued mutations in order
     ▼
Push Events ──► Display notification
```

#### Caching Strategy

| Resource Type | Strategy | Cache Name | Max Age |
|--------------|----------|------------|---------|
| App shell (HTML, JS, CSS) | Cache First | `amc-shell-v1` | 7 days |
| Static assets (images, fonts) | Cache First | `amc-static-v1` | 30 days |
| API responses (GET) | Network First | `amc-api-v1` | 5 minutes |
| GraphQL queries | Network First | `amc-graphql-v1` | 5 minutes |
| User uploads / media | Cache First (if thumbnail) | `amc-media-v1` | 7 days |

#### Background Sync

```javascript
// sw.js — Background Sync registration
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-campaign-changes') {
    event.waitUntil(syncPendingChanges());
  }
});

async function syncPendingChanges() {
  const db = await openOfflineDB();
  const pending = await db.getAll('pendingMutations');
  for (const mutation of pending) {
    try {
      await fetch(mutation.url, {
        method: mutation.method,
        body: JSON.stringify(mutation.body),
        headers: { 'Content-Type': 'application/json' },
      });
      await db.delete('pendingMutations', mutation.id);
    } catch (err) {
      // Leave in queue for next sync attempt
      console.error('Sync failed, will retry:', err);
    }
  }
}
```

#### Offline-First Data Flow

```mermaid
sequenceDiagram
    participant User
    participant SW as Service Worker
    participant Cache as IndexedDB
    participant API as API Gateway

    User->>SW: Request campaign list
    alt Online
        SW->>API: Fetch from network
        API-->>SW: Response
        SW->>Cache: Update cache
        SW-->>User: Return fresh data
    else Offline
        SW->>Cache: Read from IndexedDB
        Cache-->>SW: Cached data
        SW-->>User: Return stale data + "Offline" indicator
    end

    User->>SW: Create campaign (offline)
    SW->>Cache: Save to pendingMutations queue
    SW-->>User: Optimistic UI update
    Note over SW,API: Later, when connectivity restores...
    SW->>API: Background sync replay
    API-->>SW: 201 Created
    SW->>Cache: Clear pending mutation
    SW-->>User: Toast "Changes synced"
```

### 3.5 Real-Time Updates

AMC uses **Server-Sent Events (SSE)** as the primary real-time transport, with WebSocket fallback for bidirectional needs (e.g., collaborative campaign editing).

| Use Case | Transport | Direction | Rationale |
|----------|-----------|-----------|-----------|
| Dashboard metrics refresh | SSE | Server → Client | Simpler than WebSocket, auto-reconnect, works through HTTP/2 |
| Campaign status changes | SSE | Server → Client | Fire-and-forget status updates |
| AI agent streaming responses | SSE | Server → Client | Stream partial tokens for real-time typing effect |
| Notification delivery | SSE | Server → Client | Push notifications to connected clients |
| Collaborative editing | WebSocket | Bidirectional | Requires acknowledgments and conflict resolution |
| n8n workflow execution log | SSE | Server → Client | Stream workflow execution steps |

#### SSE Implementation

```typescript
// hooks/useSSE.ts
function useSSE<T>(url: string, onMessage: (data: T) => void) {
  useEffect(() => {
    const eventSource = new EventSource(url, {
      withCredentials: true,
    });

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    eventSource.onerror = () => {
      // Auto-reconnect is built into EventSource spec
      console.warn('SSE connection error, will retry...');
    };

    return () => eventSource.close();
  }, [url]);
}
```

### 3.6 Component Architecture — Atomic Design Methodology

AMC's UI component library follows **Atomic Design** (Brad Frost), providing a consistent, scalable, and composable component hierarchy.

```
ATOMS         MOLECULES       ORGANISMS        TEMPLATES         PAGES
┌─────┐      ┌──────────┐    ┌────────────┐   ┌──────────┐     ┌──────────┐
│Button│      │FormField │    │ DataTable  │   │Dashboard │     │Campaign  │
│Input │─────►│SearchBar │───►│ Campaign  │──►│  Layout   │────►│ List     │
│Label │      │Card      │    │ Builder   │   │ Settings │     │ View     │
│Icon  │      │Modal     │    │ Kanban    │   │ Layout   │     │ Detail   │
└─────┘      └──────────┘    └────────────┘   └──────────┘     └──────────┘
```

**Implementation:**

```typescript
// atoms/Button.tsx — smallest, most reusable
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'ghost' | 'danger';
  size: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
}

// molecules/SearchBar.tsx — composed of atoms
interface SearchBarProps {
  placeholder: string;
  onSearch: (query: string) => void;
  filters?: FilterChip[];
}

// organisms/CampaignTable.tsx — composed of molecules
interface CampaignTableProps {
  campaigns: Campaign[];
  onSelect: (id: string) => void;
  onBulkAction: (action: string, ids: string[]) => void;
}
```

---

## 4. API Gateway Layer

### 4.1 FastAPI Application Structure

The API Gateway is built with **FastAPI** (Python), chosen for its async-native architecture, automatic OpenAPI generation, and Pydantic-based validation.

```
backend/
├── api_gateway/
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration (env vars, settings)
│   ├── middleware/
│   │   ├── auth.py                # JWT validation middleware
│   │   ├── tenant.py              # Tenant resolution middleware
│   │   ├── rate_limit.py          # Rate limiting middleware
│   │   ├── logging.py             # Structured logging middleware
│   │   ├── tracing.py             # OpenTelemetry tracing middleware
│   │   ├── cors.py                # CORS middleware
│   │   └── request_id.py          # Correlation ID injection
│   ├── routers/
│   │   ├── v1/
│   │   │   ├── auth.py            # /api/v1/auth/*
│   │   │   ├── crm.py             # /api/v1/crm/*
│   │   │   ├── marketing.py       # /api/v1/marketing/*
│   │   │   ├── campaigns.py       # /api/v1/campaigns/*
│   │   │   ├── projects.py        # /api/v1/projects/*
│   │   │   ├── analytics.py       # /api/v1/analytics/*
│   │   │   ├── media.py           # /api/v1/media/*
│   │   │   ├── notifications.py   # /api/v1/notifications/*
│   │   │   ├── billing.py         # /api/v1/billing/*
│   │   │   ├── admin.py           # /api/v1/admin/*
│   │   │   ├── ai.py              # /api/v1/ai/*
│   │   │   ├── automation.py      # /api/v1/automation/*
│   │   │   ├── marketplace.py     # /api/v1/marketplace/*
│   │   │   └── knowledge.py       # /api/v1/knowledge/*
│   │   └── graphql.py             # GraphQL endpoint /api/v1/graphql
│   ├── dependencies/
│   │   ├── auth.py                # Dependency injection for current user
│   │   ├── tenant.py              # Dependency injection for current tenant
│   │   └── db.py                  # Database session dependency
│   ├── graphql/
│   │   ├── schema.py              # Strawberry GraphQL schema
│   │   ├── types/                 # GraphQL type definitions
│   │   ├── queries/               # Query resolvers
│   │   └── mutations/             # Mutation resolvers
│   ├── models/
│   │   ├── auth.py                # Pydantic models for auth
│   │   ├── crm.py                 # Pydantic models for CRM
│   │   └── ...
│   └── exceptions/
│       ├── handlers.py            # Global exception handlers
│       └── errors.py              # Custom exception classes
```

### 4.2 GraphQL Integration (Strawberry)

GraphQL is exposed at `/api/v1/graphql` alongside REST endpoints. The gateway uses **Strawberry** for its modern Python async support and tight Pydantic integration.

#### Schema Design Principles

```python
# api_gateway/graphql/schema.py
import strawberry

@strawberry.type
class Query:
    @strawberry.field
    async def campaigns(
        self,
        workspace_id: strawberry.ID,
        status: CampaignStatus | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedCampaigns:
        """Fetch campaigns for a workspace with optional status filter."""
        ...

    @strawberry.field
    async def contact(
        self,
        id: strawberry.ID,
    ) -> Contact | None:
        """Fetch a single contact by ID."""
        ...

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_campaign(
        self,
        input: CreateCampaignInput,
    ) -> Campaign:
        """Create a new marketing campaign."""
        ...

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

**REST vs GraphQL decision guide:**

| Criteria | REST | GraphQL |
|----------|------|---------|
| Simple CRUD operations | ✅ Preferred | ⚠️ Possible but verbose |
| Complex nested data fetching | ⚠️ Multiple requests | ✅ Single query |
| Real-time subscriptions | SSE endpoint | ✅ GraphQL subscriptions |
| File upload / streaming | ✅ REST native | ⚠️ Requires multipart |
| Caching (HTTP cache) | ✅ Built-in (ETag, Cache-Control) | ⚠️ More complex |
| 3rd-party API consumers | ✅ Universal | ⚠️ Requires GraphQL client |

**Decision:** Both are offered. REST is the default for external integrations and simple operations. GraphQL is recommended for the frontend and complex nested queries.

### 4.3 API Versioning Strategy

AMC uses **URL-based versioning** (`/api/v1/...`).

```
/api/v1/campaigns          # Current stable version
/api/v2/campaigns          # Next major version (when needed)
/api/beta/campaigns        # Experimental features
```

**Version lifecycle:**

| Phase | Duration | Behavior |
|-------|----------|----------|
| **Alpha** (`/api/alpha`) | Internal | No guarantees, may change without notice |
| **Beta** (`/api/beta`) | 1–3 months | Subject to change, documented as draft |
| **Stable** (`/api/v{n}`) | 12+ months | Backward compatible within version |
| **Deprecated** | 6 month sunset period | `Sunset: <date>` header returned |
| **Retired** | After sunset | Returns `410 Gone` |

**Versioning rules:**
- Breaking changes require a new version (`/api/v2/...`)
- Additive changes (new fields, new endpoints) are backward-compatible within a version
- New fields in responses are always additive (clients must ignore unknown fields)
- Deprecated fields are annotated with `x-deprecated` in OpenAPI spec

### 4.4 Middleware Chain

The middleware chain executes in a specific order, each middleware adding context to the request or enforcing policy:

```
Incoming Request
      │
      ▼
┌─────────────────┐   1. Request ID — Inject correlation ID (traceparent)
│  request_id     │      (If missing from client, generate W3C traceparent)
└────────┬────────┘
         ▼
┌─────────────────┐   2. CORS — Enforce Cross-Origin Resource Sharing policy
│  cors           │      (Allowlist of trusted origins per tier)
└────────┬────────┘
         ▼
┌─────────────────┐   3. Logging — Log incoming request (method, path, tenant_id)
│  logging        │      (Attach structured logger to request state)
└────────┬────────┘
         ▼
┌─────────────────┐   4. Tracing — Start OpenTelemetry span
│  tracing        │      (Propagate context from incoming headers)
└────────┬────────┘
         ▼
┌─────────────────┐   5. Auth — Validate JWT access token
│  auth           │      (Extract user_id, role, permissions)
└────────┬────────┘
         ▼
┌─────────────────┐   6. Tenant — Resolve current tenant
│  tenant         │      (From JWT claims, header, or path param)
└────────┬────────┘
         ▼
┌─────────────────┐   7. Rate Limit — Enforce rate limits per user/tenant/IP
│  rate_limit     │      (Sliding window via Redis)
└────────┬────────┘
         ▼
    Route Handler
```

```python
# api_gateway/main.py
from fastapi import FastAPI
from .middleware import (
    RequestIDMiddleware,
    CORSMiddleware,
    LoggingMiddleware,
    TracingMiddleware,
    AuthMiddleware,
    TenantMiddleware,
    RateLimitMiddleware,
)

app = FastAPI(title="Aegis Marketing Cloud API", version="1.0.0")

# Middleware order is critical — applied in REVERSE order of declaration
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(CORSMiddleware)
app.add_middleware(RequestIDMiddleware)
```

### 4.5 Request Lifecycle Diagram

```mermaid
sequenceDiagram
    participant B as Browser / Client
    participant CDN as CDN
    participant GW as API Gateway (FastAPI)
    participant M1 as RequestID MW
    participant M2 as CORS MW
    participant M3 as Logging MW
    participant M4 as Tracing MW
    participant M5 as Auth MW
    participant M6 as Tenant MW
    participant M7 as RateLimit MW
    participant SVC as Service Layer
    participant DB as PostgreSQL
    participant RD as Redis
    participant RQ as RabbitMQ

    B->>CDN: HTTPS Request
    CDN->>GW: Forward to origin

    Note over GW: Middleware Chain (executed in order)
    GW->>M1: 1. Request ID
    M1->>M1: Generate/inject traceparent
    M1->>M2: 2. CORS
    M2->>M2: Check Origin header
    M2->>M3: 3. Logging
    M3->>M3: Log incoming request
    M3->>M4: 4. Tracing
    M4->>M4: Start OpenTelemetry span
    M4->>M5: 5. Auth
    M5->>RD: Check JWT blacklist
    RD-->>M5: Token valid
    M5->>M5: Decode JWT, extract user_id
    M5->>M6: 6. Tenant
    M6->>RD: Resolve tenant context
    RD-->>M6: tenant_id, plan_tier
    M6->>M7: 7. Rate Limit
    M7->>RD: INCR & EXPIRE sliding window
    RD-->>M7: Request count within limit
    M7->>SVC: Forward to route handler

    Note over SVC: Business Logic
    alt Read Operation
        SVC->>DB: SELECT with RLS (tenant_id)
        DB-->>SVC: Result set
    else Write Operation
        SVC->>DB: INSERT/UPDATE with RLS
        DB-->>SVC: Success
        SVC->>RQ: Emit domain event
    end

    SVC-->>GW: Response data
    GW->>M4: Close tracing span
    GW->>M3: Log response (status, duration)
    GW-->>CDN: HTTP Response
    CDN-->>B: Response with caching headers
```

---

## 5. Service Layer

### 5.1 Service Decomposition: Microservices vs Modules Within Monolith

AMC's service decomposition follows a **cost-of-splitting** analysis for every bounded context:

| Service | Initial Form | Split Condition | Split Trigger |
|---------|-------------|----------------|---------------|
| **auth-service** | Microservice | Always standalone | Security isolation, independent scaling for SSO token validation |
| **tenant-service** | Microservice | Always standalone | Tenant provisioning must be available even if monolith is down |
| **crm-service** | Monolith module | When team > 5 engineers | Conway's Law — team autonomy |
| **marketing-service** | Monolith module | When campaign dispatch throughput exceeds 10K/min | Independent scaling of campaign execution workers |
| **ai-service** | Microservice | Always standalone | GPU/NIM inference has different scaling, deployment, and cost profile |
| **automation-service** | Microservice | Always standalone | n8n has its own lifecycle and scaling needs |
| **billing-service** | Microservice | Always standalone | PCI scope boundaries, financial audit isolation |
| **notification-service** | Microservice | Early split (v1.2) | High throughput, multiple channels (email, SMS, push, WhatsApp) |
| **analytics-service** | Microservice | Always standalone | Heavy aggregations must not impact transactional queries |
| **media-service** | Microservice | Early split (v1.0) | Image/video processing is CPU-intensive, different scaling |
| **marketplace-service** | Monolith module | When 50+ plugins published | Plugin sandboxing requires separate runtime |
| **knowledge-service** | Monolith module | When Qdrant integration demands dedicated workers | Vector indexing is resource-intensive |
| **admin-service** | Microservice | Always standalone | Admin operations must bypass normal tenant checks |

### 5.2 Service Descriptions

#### auth-service

```
Purpose:     Authentication, authorization, SSO, MFA, session management
Tech stack:  FastAPI + PostgreSQL (auth tables) + Redis (sessions)
Endpoints:   POST /login, POST /refresh, POST /logout, GET /sso/{provider}
             POST /mfa/verify, POST /password/reset
Protocol:    REST (public) + gRPC (internal — token validation for other services)
Data owned:  users, sessions, oauth_providers, mfa_configs, api_keys
Key feature: Supports OIDC, SAML (Enterprise), social login, API key auth
```

#### tenant-service

```
Purpose:     Tenant (workspace) lifecycle management, provisioning, billing sync
Tech stack:  FastAPI + PostgreSQL (tenant tables)
Endpoints:   POST /tenants, GET /tenants/{id}, PATCH /tenants/{id}
             POST /tenants/{id}/suspend, POST /tenants/{id}/activate
Protocol:    REST (management UI) + RabbitMQ events (tenant.provisioned, tenant.suspended)
Data owned:  tenants, workspaces, tenant_settings, tenant_quotas
Key feature: Automated provisioning: create tenant → create database schema → init RLS policies
```

#### crm-service (Monolith Module)

```
Purpose:     Contact management, lead scoring, pipeline management, activity tracking
Tech stack:  Python (async) + PostgreSQL (CRM tables)
APIs:        REST /api/v1/crm/contacts, /api/v1/crm/leads, /api/v1/crm/pipelines
             GraphQL queries for complex contact enrichment
Data owned:  contacts, leads, pipelines, stages, deals, activities, tags, segments
Key feature: AI-powered lead scoring via ai-service integration
```

#### marketing-service (Monolith Module)

```
Purpose:     Campaign management, email marketing, social scheduling, ad management
Tech stack:  Python (async) + PostgreSQL (marketing tables) + RabbitMQ (dispatch)
APIs:        REST /api/v1/marketing/campaigns, /api/v1/marketing/emails
             /api/v1/marketing/social-posts, /api/v1/marketing/ads
Data owned:  campaigns, emails, templates, social_posts, ad_accounts, ad_sets
Key feature: Campaign dispatch via RabbitMQ — workers process channel-specific delivery
```

#### ai-service (Orchestrator)

See [Section 6: AI Layer Architecture](#6-ai-layer-architecture) for full details.

```
Purpose:     AI agent orchestration, inference routing, memory management
Tech stack:  Python + Hermes Agents framework + Redis (short-term) + Qdrant (long-term)
APIs:        REST /api/v1/ai/chat, /api/v1/ai/agents, /api/v1/ai/generate
             WebSocket /api/v1/ai/stream (streaming responses)
Key feature: Multi-agent orchestration with tool calling and NVIDIA NIM inference
```

#### automation-service (n8n Wrapper)

See [Section 8: n8n Integration Architecture](#8-n8n-integration-architecture) for full details.

```
Purpose:     n8n workflow execution, template management, credential storage
Tech stack:  Python (wrapper) + n8n (embedded or cluster) + PostgreSQL (workflow metadata)
APIs:        REST /api/v1/automation/workflows, /api/v1/automation/executions
             /api/v1/automation/templates
Key feature: Embed n8n API — users build workflows in n8n UI, executions are tracked
```

#### billing-service

```
Purpose:     Subscription management, usage metering, invoicing, payment processing
Tech stack:  FastAPI + PostgreSQL (billing tables) + Stripe API
APIs:        REST /api/v1/billing/subscriptions, /api/v1/billing/invoices
             /api/v1/billing/usage, /api/v1/billing/payment-methods
Data owned:  subscriptions, invoices, payments, usage_records, credits
Key feature: Usage-based billing — AI credits, API calls, storage, contacts
             Stripe integration for payment processing
```

#### notification-service

```
Purpose:     Multi-channel notification delivery (email, SMS, push, WhatsApp, in-app)
Tech stack:  Python + RabbitMQ (consume events) + SendGrid (email) +
             Twilio (SMS/WhatsApp) + Web Push API
Consumes:    RabbitMQ `notification.*` events
Data owned:  notification_templates, delivery_logs, channel_configs
Key feature: Template-driven, multi-channel with fallback (if email bounces, fallback to SMS)
```

#### analytics-service

```
Purpose:     Aggregated analytics, reporting, dashboards, exports
Tech stack:  FastAPI + ClickHouse (or PostgreSQL for smaller tenants) + Redis (cached aggregations)
APIs:        REST /api/v1/analytics/dashboards, /api/v1/analytics/reports
             /api/v1/analytics/export
Data owned:  (reads from all other services via event-sourced aggregation tables)
Key feature: Materialized aggregate tables refreshed via event consumption
```

#### media-service

```
Purpose:     Image/video upload, processing, optimization, CDN distribution
Tech stack:  FastAPI + MinIO (storage) + Sharp/FFmpeg (processing)
APIs:        REST /api/v1/media/upload, /api/v1/media/{id}, /api/v1/media/process
Data owned:  media_assets, asset_versions, processing_jobs
Key feature: Async processing: upload → process (resize, optimize, generate thumbnails) → CDN push
```

#### marketplace-service

```
Purpose:     Plugin/extension marketplace, installation, licensing
Tech stack:  Python (module) + PostgreSQL + MinIO (plugin packages)
APIs:        REST /api/v1/marketplace/plugins, /api/v1/marketplace/install
Data owned:  plugins, plugin_versions, installations, reviews
Key feature: Sandboxed plugin execution via subprocess/container isolation
```

#### knowledge-service

```
Purpose:     Centralized knowledge base, brand guidelines, strategy documents
Tech stack:  Python (module) + PostgreSQL (metadata) + Qdrant (vector search)
APIs:        REST /api/v1/knowledge/articles, /api/v1/knowledge/search
Data owned:  articles, categories, embeddings, vector indexes
Key feature: AI agents query knowledge base for context-aware responses
```

#### admin-service

```
Purpose:     Platform administration, tenant management, system health, global settings
Tech stack:  FastAPI + PostgreSQL (admin tables)
APIs:        REST /api/v1/admin/tenants, /api/v1/admin/users, /api/v1/admin/health
             /api/v1/admin/feature-flags
Data owned:  audit_log, feature_flags, system_settings, admin_users
Key feature: Admin-only endpoints with elevated privileges (bypass tenant isolation)
```

### 5.3 Internal Communication

AMC uses three internal communication mechanisms, each chosen for specific use cases:

| Mechanism | Use Case | Protocol | Libraries |
|-----------|----------|----------|-----------|
| **gRPC** | Service-to-service synchronous calls (high-performance, typed) | HTTP/2 + Protocol Buffers | `grpcio`, `grpcio-tools` |
| **Redis Pub/Sub** | Lightweight real-time notifications within a service boundary | Redis | `redis-py` |
| **RabbitMQ** | Cross-service event-driven communication, durable message delivery | AMQP 0-9-1 | `aio-pika`, `pika` |

#### Communication Pattern Selection

```
┌──────────────┐    gRPC (typed, fast)    ┌──────────────┐
│  API Gateway │ ───────────────────────►  │  auth-service│
│              │                          │              │
│              │    RabbitMQ (events)     │              │
│              │ ───────────────────────►  │  monolith    │
└──────────────┘                          └──────────────┘
       │                                        │
       │  RabbitMQ domain events                │  RabbitMQ
       ▼                                        ▼
┌──────────────┐                          ┌──────────────┐
│ notification │                          │  analytics   │
│ -service     │                          │  -service    │
└──────────────┘                          └──────────────┘
```

#### gRPC Service Definitions

```protobuf
// proto/auth-service.proto
service AuthService {
  rpc ValidateToken (ValidateTokenRequest) returns (ValidateTokenResponse);
  rpc GetUserPermissions (GetUserPermissionsRequest) returns (GetUserPermissionsResponse);
}

message ValidateTokenRequest {
  string access_token = 1;
  string requested_tenant_id = 2;
}

message ValidateTokenResponse {
  bool valid = 1;
  string user_id = 2;
  string tenant_id = 3;
  repeated string roles = 4;
  int64 expires_at = 5;
}
```

#### RabbitMQ Event Taxonomy

```python
# Domain events — emitted by services, consumed by interested parties
EVENT_TOPOLOGY = {
    "campaign": {
        "campaign.created": ["analytics", "notification", "automation"],
        "campaign.launched": ["analytics", "notification", "billing"],
        "campaign.completed": ["analytics", "knowledge"],
    },
    "contact": {
        "contact.created": ["analytics", "automation"],
        "contact.updated": ["analytics", "automation"],
        "contact.segment_changed": ["marketing", "automation"],
    },
    "tenant": {
        "tenant.provisioned": ["billing", "notification", "admin"],
        "tenant.suspended": ["billing", "auth", "notification"],
    },
    "billing": {
        "billing.plan_changed": ["tenant", "notification"],
        "billing.payment_failed": ["tenant", "notification"],
        "billing.usage_threshold": ["notification"],
    },
    "ai": {
        "ai.inference.completed": ["analytics", "billing"],
        "ai.agent.action": ["analytics", "audit"],
    },
    "automation": {
        "automation.workflow.completed": ["analytics", "notification"],
        "automation.workflow.failed": ["notification", "admin"],
    },
}
```

### 5.4 Service Mesh / Service Discovery Strategy

For the initial modular monolith + few microservices deployment, a **simplified service discovery** approach is used:

| Environment | Discovery Method | Notes |
|-------------|-----------------|-------|
| **Development** (Docker Compose) | Docker DNS (`service_name:port`) | Built-in Compose networking |
| **Production** (Docker Swarm) | Swarm DNS + VIP | Built-in Swarm service discovery |
| **Future** (Kubernetes) | K8s Services + CoreDNS | Standard K8s service discovery |

**For service mesh**, AMC defers to Docker Swarm's built-in load balancing and TLS in production. If K8s is adopted, **Linkerd** (not Istio) is the preferred service mesh due to its lighter resource footprint and simpler architecture.

### 5.5 Circuit Breaker and Retry Patterns

All inter-service calls implement **circuit breakers** and **retry with exponential backoff**:

```python
# lib/circuit_breaker.py
import asyncio
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing — reject immediately
    HALF_OPEN = "half_open"  # Testing if service recovered

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0.0

    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError()

        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise
```

**Retry configuration by service type:**

| Service | Max Retries | Backoff | Jitter | Notes |
|---------|-------------|---------|--------|-------|
| auth-service | 2 | 100ms, 500ms | ±50ms | Token validation is fast, retry quickly |
| ai-service | 3 | 500ms, 2s, 5s | ±250ms | Inference can be slow, allow longer backoff |
| billing-service | 0 | — | — | Never retry payment operations automatically |
| notification-service | 3 | 1s, 5s, 30s | ±500ms | Channel delivery may be temporarily unavailable |
| database queries | 2 | 50ms, 200ms | ±10ms | Transient connection failures |

---

## 6. AI Layer Architecture

### 6.1 Hermes Agent Framework Integration

AMC integrates the **Hermes Agent framework** as the core AI orchestration runtime. Hermes provides the agent runtime, tool-calling mechanism, and multi-agent coordination primitives that AMC builds upon.

```
┌────────────────────────────────────────────────────────────┐
│                   AMC AI Layer                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Agent        │  │ Agent        │  │ Agent        │      │
│  │ Orchestrator │  │ Registry     │  │ Scheduler    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│  ┌──────▼─────────────────▼─────────────────▼───────┐      │
│  │              Hermes Agent Runtime                  │      │
│  │  (Agent lifecycle, tool execution, memory R/W)    │      │
│  └──────────────────────┬────────────────────────────┘      │
│                         │                                    │
│  ┌──────────────────────▼────────────────────────────┐      │
│  │           AI Provider Abstraction Layer             │      │
│  │  ┌─────────┐ ┌──────────┐ ┌──────────────────┐    │      │
│  │  │ NVIDIA  │ │ OpenAI   │ │ Anthropic / Other │    │      │
│  │  │ NIM     │ │ Compat   │ │ Providers         │    │      │
│  │  └─────────┘ └──────────┘ └──────────────────┘    │      │
│  └────────────────────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Agent Orchestrator Design

The Agent Orchestrator is the central scheduler that manages agent workload:

```python
# ai_service/orchestrator.py
class AgentOrchestrator:
    """Central orchestrator for multi-agent execution."""

    def __init__(self):
        self.scheduler = WorkScheduler()
        self.registry = AgentRegistry()
        self.work_queue = RedisWorkQueue()
        self.memory_manager = MemoryManager()

    async def dispatch_task(self, task: AgentTask) -> TaskResult:
        """Route a task to the appropriate agent(s)."""
        # 1. Determine required agent types
        agent_types = self._resolve_agent_types(task)

        # 2. Check if single or multi-agent
        if len(agent_types) == 1:
            return await self._single_agent_execution(agent_types[0], task)
        else:
            return await self._multi_agent_execution(agent_types, task)

    async def _single_agent_execution(
        self, agent_type: str, task: AgentTask
    ) -> TaskResult:
        """Execute task with a single agent."""
        agent = await self.registry.get_agent(agent_type, task.workspace_id)
        context = await self.memory_manager.build_context(task.workspace_id, task)
        return await agent.execute(task, context)

    async def _multi_agent_execution(
        self, agent_types: list[str], task: AgentTask
    ) -> TaskResult:
        """Coordinate multiple agents for complex tasks."""
        supervisor = await self.registry.get_agent("supervisor", task.workspace_id)
        plan = await supervisor.create_plan(task)
        results = []
        for step in plan.steps:
            agent = await self.registry.get_agent(step.agent_type, task.workspace_id)
            result = await agent.execute(step.subtask, task.context)
            results.append(result)
        return supervisor.synthesize(results)
```

#### Scheduler and Work Queue

```python
# ai_service/scheduler.py
class WorkScheduler:
    """
    Schedules AI agent tasks with priority, deduplication, and rate limiting.

    Priority tiers:
      0 — Real-time (user waiting for response)  — max 10s
      1 — Interactive (agent-initiated question)  — max 30s
      2 — Background (async processing)           — max 5min
      3 — Batch (overnight processing)            — no SLA
    """

    async def enqueue(self, task: AgentTask, priority: int = 2):
        """Enqueue a task for async execution."""
        key = f"ai:queue:{priority}"
        await self.redis.rpush(key, task.json())
        await self.redis.publish("ai:new_task", task.task_id)

    async def dequeue(self) -> AgentTask | None:
        """Pop the highest-priority available task."""
        for priority in range(4):
            task_data = await self.redis.lpop(f"ai:queue:{priority}")
            if task_data:
                return AgentTask.parse_raw(task_data)
        return None
```

### 6.3 Agent Lifecycle Management

```
                    ┌─────────────┐
                    │   CREATED   │
                    └──────┬──────┘
                           │ register()
                           ▼
                    ┌─────────────┐
                    │   IDLE      │ ←── Pool of warm agents
                    └──────┬──────┘
                           │ execute()
                           ▼
                    ┌─────────────┐
             ┌─────│  EXECUTING  │─────┐
             │     └──────┬──────┘     │
             │            │            │
             ▼            ▼            ▼
     ┌──────────┐  ┌──────────┐  ┌──────────┐
     │ COMPLETED│  │  FAILED  │  │ TIMEOUT  │
     └──────────┘  └────┬─────┘  └──────────┘
                        │ retry?
                        ▼
                   ┌──────────┐
                   │  RETRY   │──► EXECUTING
                   └──────────┘
```

```python
# ai_service/agent_lifecycle.py
class AgentInstance:
    """Represents a running agent instance for a specific workspace."""

    def __init__(self, agent_type: str, workspace_id: str):
        self.state = AgentState.CREATED
        self.workspace_id = workspace_id
        self.agent_type = agent_type
        self.created_at = datetime.utcnow()
        self.max_execution_time = 60  # seconds
        self.max_retries = 2

    async def execute(self, task: AgentTask) -> AgentResult:
        self.state = AgentState.EXECUTING
        try:
            result = await asyncio.wait_for(
                self._run(task),
                timeout=self.max_execution_time,
            )
            self.state = AgentState.COMPLETED
            return result
        except asyncio.TimeoutError:
            self.state = AgentState.TIMEOUT
            if self.retry_count < self.max_retries:
                self.state = AgentState.RETRY
                return await self.execute(task)
            raise
        except Exception as e:
            self.state = AgentState.FAILED
            raise
```

### 6.4 Multi-Agent Communication Protocol

AMC agents communicate via the **event bus** (RabbitMQ) rather than direct agent-to-agent calls. This provides:

1. **Decoupling** — Agents don't need to know each other's addresses
2. **Durability** — Messages persist if the receiving agent is busy
3. **Audit trail** — Every inter-agent message is logged
4. **Scalability** — Multiple instances of an agent can consume from the same queue

```
                  ┌──────────────────┐
                  │   Event Bus      │
                  │  (RabbitMQ)      │
                  └──┬────┬────┬────┘
           ┌─────────┘    │    └──────────┐
           ▼              ▼               ▼
     ┌──────────┐  ┌──────────┐   ┌──────────┐
     │Marketing │  │   SEO    │   │ Content  │
     │Director  │  │Specialist│   │  Writer  │
     └──────────┘  └──────────┘   └──────────┘
```

Agent message schema:

```python
@dataclass
class AgentMessage:
    message_id: str            # UUID
    source_agent: str          # "marketing_director"
    target_agent: str | None   # None = broadcast, "seo_specialist" = directed
    message_type: str          # "request", "response", "broadcast", "error"
    conversation_id: str       # Conversation thread
    payload: dict              # Domain-specific data
    timestamp: datetime
    ttl: int                   # Time-to-live in seconds
```

### 6.5 Memory Architecture

AMC's memory architecture is split between **short-term** (working memory, ephemeral) and **long-term** (persistent knowledge, retrievable).

```
                    Agent Memory
                         │
           ┌─────────────┴─────────────┐
           ▼                           ▼
  ┌─────────────────┐       ┌─────────────────────┐
  │  Short-Term      │       │   Long-Term          │
  │  (Redis)         │       │   (Qdrant)           │
  │                  │       │                      │
  │ • Session state  │       │ • Conversation       │
  │ • Task context   │       │   history (summary)  │
  │ • Tool call      │       │ • Knowledge base     │
  │   results (TTL)  │       │   embeddings         │
  │ • Cache of       │       │ • Brand guidelines   │
  │   recent queries │       │ • Campaign insights  │
  │ • Agent scratch  │       │ • Customer segments  │
  │   pad            │       │ • Past decisions     │
  └─────────────────┘       └─────────────────────┘
```

#### Short-Term Memory (Redis)

```
Key pattern:  ai:memory:{workspace_id}:{conversation_id}:{key}
TTL:          30 minutes (sliding window — extends on access)
```

```python
class ShortTermMemory:
    def __init__(self, redis_client):
        self.redis = redis_client

    async def set_context(self, workspace_id: str, conversation_id: str, context: dict):
        key = f"ai:memory:{workspace_id}:{conversation_id}:context"
        await self.redis.setex(key, 1800, json.dumps(context))  # 30 min TTL

    async def get_context(self, workspace_id: str, conversation_id: str) -> dict | None:
        key = f"ai:memory:{workspace_id}:{conversation_id}:context"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def append_tool_result(self, workspace_id: str, conversation_id: str, result: dict):
        key = f"ai:memory:{workspace_id}:{conversation_id}:tool_results"
        await self.redis.rpush(key, json.dumps(result))
        await self.redis.expire(key, 1800)
```

#### Long-Term Memory (Qdrant)

```
Collection:   ai_memory_{workspace_id}
Payload:      conversation_id, agent_type, timestamp, summary, metadata
Vector:       OpenAI text-embedding-3-large (3072 dimensions)
```

```python
class LongTermMemory:
    def __init__(self, qdrant_client):
        self.qdrant = qdrant_client

    async def store_memory(
        self,
        workspace_id: str,
        conversation_id: str,
        agent_type: str,
        content: str,
        metadata: dict,
    ):
        """Store a conversation summary as a retrievable memory."""
        vector = await self._embed(content)
        await self.qdrant.upsert(
            collection_name=f"ai_memory_{workspace_id}",
            points=[PointStruct(
                id=uuid4(),
                vector=vector,
                payload={
                    "conversation_id": conversation_id,
                    "agent_type": agent_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "content": content,
                    **metadata,
                },
            )],
        )

    async def search_memories(
        self,
        workspace_id: str,
        query: str,
        limit: int = 5,
        agent_type: str | None = None,
    ) -> list[MemoryResult]:
        """Semantic search across past conversations."""
        query_vector = await self._embed(query)
        filter_condition = (
            Filter(must=[FieldCondition(key="agent_type", match=MatchValue(value=agent_type))])
            if agent_type else None
        )
        results = await self.qdrant.search(
            collection_name=f"ai_memory_{workspace_id}",
            query_vector=query_vector,
            limit=limit,
            query_filter=filter_condition,
        )
        return [MemoryResult(
            score=r.score,
            content=r.payload["content"],
            metadata={k: v for k, v in r.payload.items() if k != "content"},
        ) for r in results]
```

### 6.6 Tool Registry and Calling Mechanism

Agents interact with the platform through **tools** — registered functions that agents can invoke. The Tool Registry manages discovery, invocation, and result processing.

```python
# ai_service/tool_registry.py
class ToolRegistry:
    """Registry of tools that agents can call."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition):
        """Register a tool for agent use."""
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, agent_type: str | None = None) -> list[ToolDefinition]:
        """List tools, optionally filtered by agent type."""
        if agent_type:
            return [t for t in self._tools.values() if agent_type in t.allowed_agents]
        return list(self._tools.values())

    async def execute_tool(self, name: str, params: dict, context: ExecutionContext) -> ToolResult:
        """Execute a tool with validation and telemetry."""
        tool = self.get_tool(name)
        if not tool:
            raise ToolNotFoundError(f"Tool '{name}' not found")

        # Validate parameters against schema
        validated = tool.schema(**params)

        # Execute with timing
        start = time.monotonic()
        try:
            result = await tool.handler(validated, context)
            duration = time.monotonic() - start
            metrics.tool_execution_time.labels(tool=name).observe(duration)
            return ToolResult(success=True, data=result, duration_ms=duration * 1000)
        except Exception as e:
            duration = time.monotonic() - start
            metrics.tool_execution_errors.labels(tool=name).inc()
            return ToolResult(success=False, error=str(e), duration_ms=duration * 1000)
```

#### Tool Categories

| Category | Examples | Allowed Agents |
|----------|----------|---------------|
| **CRM Tools** | `get_contact`, `create_contact`, `search_contacts`, `update_pipeline` | marketing_director, sales_agent, customer_success |
| **Marketing Tools** | `create_campaign`, `get_campaign_analytics`, `send_email`, `schedule_social_post` | marketing_director, content_writer |
| **Knowledge Tools** | `search_knowledge_base`, `create_article`, `update_brand_guidelines` | all agents |
| **Analytics Tools** | `get_dashboard_metrics`, `run_report`, `export_data` | marketing_director, seo_specialist, analytics_agent |
| **Automation Tools** | `trigger_workflow`, `get_workflow_status`, `list_workflows` | marketing_director, operations_agent |
| **System Tools** | `get_current_time`, `send_notification`, `escalate_to_human` | all agents |

#### Tool Definition Schema

```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    schema: type[BaseModel]       # Pydantic model for parameter validation
    handler: Callable             # Async function implementing the tool
    allowed_agents: list[str]     # Agent types that can call this tool
    rate_limit: int | None = None # Max calls per minute (None = unlimited)
    timeout: int = 30             # Max execution time in seconds
    cache_ttl: int | None = None  # Cache result for this many seconds
```

### 6.7 NVIDIA NIM Integration

**NVIDIA NIM** (NVIDIA Inference Microservice) is the primary inference provider for AMC. It provides optimized inference containers for a range of open-source and NVIDIA-optimized models.

#### Inference Endpoint Configuration

```yaml
# ai_service/nim_config.yaml
nim:
  endpoints:
    - name: "mixtral-8x22b"
      url: "https://nim-dgx.internal:8000/v1/chat/completions"
      model: "mistralai/mixtral-8x22b-instruct-v0.1"
      tier: "premium"
      max_tokens: 8192
      cost_per_1k_tokens: 0.0005

    - name: "llama-3-70b"
      url: "https://nim-dgx.internal:8001/v1/chat/completions"
      model: "meta/llama-3-70b-instruct"
      tier: "standard"
      max_tokens: 4096
      cost_per_1k_tokens: 0.0003

    - name: "llama-3-8b"
      url: "https://nim-dgx.internal:8002/v1/chat/completions"
      model: "meta/llama-3-8b-instruct"
      tier: "economy"
      max_tokens: 2048
      cost_per_1k_tokens: 0.0001

    - name: "nemotron-4-340b"
      url: "https://nim-dgx.internal:8003/v1/chat/completions"
      model: "nvidia/nemotron-4-340b-instruct"
      tier: "premium"
      max_tokens: 4096
      cost_per_1k_tokens: 0.001
```

#### Model Routing Logic

```python
class ModelRouter:
    """Routes inference requests to the appropriate NIM endpoint."""

    def __init__(self, config: NIMConfig):
        self.endpoints = config.endpoints
        self.cache = TTLCache(maxsize=1000, ttl=300)  # 5-min cache

    async def route(self, request: InferenceRequest) -> InferenceEndpoint:
        """Select the best endpoint based on request characteristics."""

        # 1. Check cache (identical requests)
        cache_key = self._cache_key(request)
        if cache_key in self.cache and not request.bypass_cache:
            return self.cache[cache_key]

        # 2. Tenant tier override (Enterprise → premium only)
        if request.tenant_tier == "enterprise":
            endpoint = self._select_by_tier("premium")
            self.cache[cache_key] = endpoint
            return endpoint

        # 3. Complexity-based routing
        if request.complexity == "high" or request.task_type == "reasoning":
            endpoint = self._select_by_tier("standard", min_preferred="standard")
        elif request.task_type in ("summarization", "classification"):
            endpoint = self._select_by_tier("economy")
        else:
            # Dynamic selection — balance cost and performance
            endpoint = self._select_by_tier(request.preferred_tier or "standard")

        # 4. Load-aware routing (avoid overloaded endpoints)
        endpoint = await self._load_balance(endpoint)

        self.cache[cache_key] = endpoint
        return endpoint

    def _select_by_tier(self, tier: str, min_preferred: str | None = None) -> InferenceEndpoint:
        """Select an endpoint matching the requested tier."""
        candidates = [e for e in self.endpoints if e.tier == tier]
        if not candidates and min_preferred:
            # Fall up to a higher tier
            tiers = ["economy", "standard", "premium"]
            idx = tiers.index(tier)
            for higher_tier in tiers[idx + 1:]:
                candidates = [e for e in self.endpoints if e.tier == higher_tier]
                if candidates:
                    break
        return random.choice(candidates) if candidates else self.endpoints[0]
```

#### Fallback Chain

```mermaid
flowchart TD
    A[Inference Request] --> B{Tenant Tier?}
    B -->|Enterprise| C[Premium Endpoint]
    B -->|Standard| D[Standard Endpoint]
    B -->|Free| E[Economy Endpoint]

    C --> F{Response OK?}
    D --> F
    E --> F

    F -->|Yes| G[Return Response]
    F -->|No - Timeout| H{Next tier available?}
    F -->|No - Error| H

    H -->|Yes| I[Fallback to next higher tier]
    I --> F
    H -->|No| J[Return error + cache bust]
```

### 6.8 AI Provider Abstraction Layer

To avoid vendor lock-in and enable cost optimization, all AI interactions go through a provider abstraction layer:

```python
# ai_service/providers/base.py
class AIProvider(ABC):
    """Abstract base for all AI inference providers."""

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> ChatResult | AsyncIterator[StreamChunk]:
        ...

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str,
    ) -> list[list[float]]:
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        ...

# ai_service/providers/nim_provider.py
class NIMProvider(AIProvider):
    """NVIDIA NIM provider implementation."""

    def __init__(self, config: NIMConfig):
        self.config = config
        self.session = aiohttp.ClientSession()

    async def chat_completion(self, ...):
        # Call NIM endpoint with OpenAI-compatible API
        ...

# ai_service/providers/openai_provider.py
class OpenAIProvider(AIProvider):
    """Fallback OpenAI-compatible provider (for redundancy)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

# ai_service/providers/provider_manager.py
class ProviderManager:
    """Manages multiple providers with health checks and failover."""

    def __init__(self):
        self.providers: dict[str, AIProvider] = {}
        self.health_status: dict[str, bool] = {}

    async def get_provider(self, preferred: str = "nim") -> AIProvider:
        """Get the preferred provider or the first healthy fallback."""
        if preferred in self.providers and self.health_status.get(preferred, False):
            return self.providers[preferred]
        for name, provider in self.providers.items():
            if self.health_status.get(name, False):
                return provider
        raise NoHealthyProviderError()
```

### 6.9 Prompt Management System

Prompts are version-controlled, A/B testable, and environment-aware:

```
prompts/
├── production/
│   ├── marketing-director/
│   │   ├── v1.0.md              # Original prompt
│   │   ├── v1.1.md              # Updated for campaign context
│   │   └── v1.2.md              # Latest (symlinked to current.md)
│   ├── content-writer/
│   │   ├── v1.0.md
│   │   └── v2.0.md              # Major rewrite
│   └── seo-specialist/
│       └── v1.0.md
├── staging/
│   └── ... (pre-release versions)
├── experiments/
│   ├── marketing-director/
│   │   ├── v1.3-experimental.md
│   │   └── v1.4-experimental.md
│   └── content-writer/
│       └── v2.1-experimental.md
└── templates/
    ├── system-prompt.j2          # Jinja2 template for system prompts
    └── few-shot.j2               # Few-shot example template
```

```python
class PromptManager:
    """Version-controlled prompt management with A/B testing."""

    def __init__(self, storage: MinIOStorage | FileStorage):
        self.storage = storage

    async def get_prompt(
        self,
        agent_type: str,
        version: str | None = None,
        workspace_id: str | None = None,
    ) -> str:
        """Get a prompt, resolving version and workspace overrides."""
        if version:
            path = f"prompts/production/{agent_type}/v{version}.md"
        else:
            # Check workspace-specific override first
            if workspace_id:
                override = await self._check_override(agent_type, workspace_id)
                if override:
                    return override
            # A/B test assignment
            variant = await self._resolve_ab_test(agent_type, workspace_id)
            path = f"prompts/production/{agent_type}/v{variant}.md"
        return await self.storage.read(path)

    async def _resolve_ab_test(self, agent_type: str, workspace_id: str | None) -> str:
        """Determine which prompt variant a workspace should use."""
        ab_config = await self._get_ab_config(agent_type)
        if not ab_config or not workspace_id:
            return "current"
        # Deterministic assignment based on workspace_id hash
        bucket = hash(f"{agent_type}:{workspace_id}") % 100
        for variant in ab_config.variants:
            if bucket < variant.traffic_percent:
                return variant.version
            bucket -= variant.traffic_percent
        return "current"
```

---

## 7. Data Layer

### 7.1 PostgreSQL Architecture

PostgreSQL is the primary operational database for AMC. All transactional data — CRM, marketing, projects, billing, users — lives in PostgreSQL.

#### Partitioning Strategy

| Table | Partition Strategy | Partition Key | Retention |
|-------|-------------------|---------------|-----------|
| `campaign_events` | Range (monthly) | `created_at` | 24 months |
| `email_sends` | Range (monthly) | `sent_at` | 12 months |
| `contact_activities` | Range (monthly) | `created_at` | 18 months |
| `audit_logs` | Range (monthly) | `created_at` | 12 months |
| `analytics_events` | Range (daily) | `event_time` | 90 days raw, then rollup |

```sql
-- Example: Monthly partition on campaign_events
CREATE TABLE campaign_events (
    id UUID DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    campaign_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- Create monthly partitions
CREATE TABLE campaign_events_2026_01
    PARTITION OF campaign_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE campaign_events_2026_02
    PARTITION OF campaign_events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

#### Connection Pooling with PgBouncer

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  API        │────►│              │────►│  PostgreSQL   │
│  Gateway    │     │  PgBouncer   │     │  Primary      │
├─────────────┤     │  (transaction│     ├──────────────┤
│  Services   │────►│   pooling)   │────►│  Replica 1    │
├─────────────┤     │              │     ├──────────────┤
│  Workers    │────►│              │────►│  Replica 2    │
└─────────────┘     └──────────────┘     └──────────────┘
```

PgBouncer configuration:

```ini
[databases]
; Transaction pooling — best for many short-lived connections
amc = host=pg-primary port=5432 dbname=amc
amc_readonly = host=pg-replica port=5432 dbname=amc

[pgbouncer]
pool_mode = transaction
default_pool_size = 50
max_client_conn = 500
max_db_connections = 100
listen_port = 6432
listen_addr = 0.0.0.0
```

#### Row-Level Security (RLS) Policy Design

RLS is the **cornerstone of tenant isolation** in AMC. Every query is automatically scoped to the current tenant by database policies, making it impossible for application code to accidentally leak data across tenants.

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
-- ... all tables

-- Unified RLS policy pattern
CREATE POLICY tenant_isolation ON contacts
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- Similar policy for every tenant-scoped table
CREATE POLICY tenant_isolation ON campaigns
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID)
    WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- Admin bypass policy (for admin-service)
CREATE POLICY admin_bypass ON contacts
    FOR ALL
    USING (current_setting('app.user_role') = 'admin' OR
           tenant_id = current_setting('app.current_tenant_id')::UUID);
```

**Flow:**

```mermaid
sequenceDiagram
    participant App as Application
    participant PgB as PgBouncer
    participant PG as PostgreSQL

    App->>PgB: SET app.current_tenant_id = 'tenant-abc-123'
    App->>PgB: SET app.user_role = 'member'
    App->>PgB: SELECT * FROM contacts WHERE id = '...'
    PgB->>PG: Forward query with session context
    PG->>PG: RLS policy adds: AND tenant_id = 'tenant-abc-123'
    PG-->>PgB: Filtered results
    PgB-->>App: Response (only tenant's data)
```

### 7.2 Redis Topology

Redis serves multiple roles in AMC, each with specific data structures and eviction policies:

| Use Case | Data Type | Key Pattern | Persistence | Eviction |
|----------|-----------|-------------|-------------|----------|
| **Cache** (API responses) | String | `cache:{endpoint}:{params_hash}` | None | LRU (maxmemory 2GB) |
| **Session Store** | String | `session:{session_id}` | RDB snapshots | TTL-based (24h) |
| **Rate Limiter** | Sorted Set | `ratelimit:{tenant_id}:{endpoint}` | None | TTL-based (sliding window) |
| **Pub/Sub** | Channel | Various | N/A | N/A |
| **Job Queue** | List | `queue:{name}` | AOF (every sec) | None (processed jobs removed) |
| **Short-term AI Memory** | String + List | `ai:memory:{workspace_id}:*` | None | TTL-based (30min) |
| **Distributed Lock** | String | `lock:{resource}` | None | TTL-based (10s max) |

#### Cache Topology

```
                    ┌─────────────────────┐
                    │  Redis Cache Node    │
                    │  (Cluster, 6 shards) │
                    │  maxmemory=2GB/node  │
                    │  eviction=allkeys-lru│
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
   ┌───────────┐       ┌───────────┐       ┌───────────┐
   │  Shard 1   │       │  Shard 2   │       │  Shard 3   │
   │  (master)  │       │  (master)  │       │  (master)  │
   └─────┬─────┘       └─────┬─────┘       └─────┬─────┘
         │                   │                   │
         ▼                   ▼                   ▼
   ┌───────────┐       ┌───────────┐       ┌───────────┐
   │  Replica 1 │       │  Replica 1 │       │  Replica 1 │
   └───────────┘       └───────────┘       └───────────┘
```

#### Redis Sentinel (High Availability)

```yaml
# sentinel.conf
sentinel monitor amc-cache redis-cache-1 6379 2
sentinel down-after-milliseconds amc-cache 5000
sentinel failover-timeout amc-cache 60000
sentinel parallel-syncs amc-cache 1
```

### 7.3 Qdrant Cluster Configuration

Qdrant is the vector database powering AI long-term memory, semantic search in knowledge base, and similarity search for campaign content.

#### Cluster Topology

```yaml
# qdrant/cluster.yaml
cluster:
  # 3-node cluster with Raft consensus
  nodes:
    - host: qdrant-1.internal
      port: 6335
    - host: qdrant-2.internal
      port: 6335
    - host: qdrant-3.internal
      port: 6335

  # Replication factor: 2 (each shard on 2 nodes)
  replication_factor: 2

  # Write consistency: quorum (2 of 3 nodes must confirm)
  write_consistency_factor: 2

  # Sharding: auto-shard per collection
  # Each collection gets 6 shards (2x nodes)
  shard_number: 6
```

#### Collection Design

| Collection | Vector Size | Distance | Payload Indexes | Use Case |
|-----------|-------------|----------|----------------|----------|
| `ai_memory_{workspace_id}` | 3072 | Cosine | `agent_type`, `timestamp` | Agent conversation history |
| `knowledge_base_{workspace_id}` | 3072 | Cosine | `category`, `status`, `author` | Brand guidelines, docs |
| `campaign_content` | 1536 | Cosine | `tenant_id`, `campaign_id`, `content_type` | Duplicate detection, similarity |
| `customer_segments` | 768 | Cosine | `tenant_id`, `segment_type` | Look-alike audience discovery |

#### Indexing Strategy

```yaml
# Per-collection index configuration
indexing:
  # HNSW (Hierarchical Navigable Small World) — default for all collections
  hnsw:
    m: 16              # Number of bi-directional links (higher = better recall, more memory)
    ef_construct: 200  # Search width during construction (higher = better recall, slower build)
    full_scan_threshold: 10000  # Threshold for switching to full scan

  # Quantization — reduce memory for large collections
  quantization:
    scalar:
      type: scalar
      quantile: 0.99
      always_ram: true

  # Payload indexing — for filtered searches
  on_disk_payload: true  # Store payload on disk, keep vectors in RAM
```

### 7.4 MinIO Object Storage

MinIO provides S3-compatible object storage for media assets, exports, backups, and plugin packages.

#### Bucket Per Tenant Strategy

```
minio/
├── tenant-abc-123/
│   ├── media/
│   │   ├── images/
│   │   ├── videos/
│   │   ├── documents/
│   │   └── thumbnails/
│   ├── exports/
│   │   ├── campaigns/
│   │   └── reports/
│   └── backups/
│       └── config/
├── tenant-def-456/
│   └── ...
├── system/
│   ├── plugins/
│   ├── templates/
│   └── backups/
└── shared/
    └── marketplace/
```

#### Lifecycle Policies

```json
// MinIO bucket lifecycle rule for tenant media
{
  "Rules": [
    {
      "ID": "expire-temp-uploads",
      "Status": "Enabled",
      "Filter": {"Prefix": "media/temp/"},
      "Expiration": {"Days": 1}
    },
    {
      "ID": "expire-thumbnails-v1",
      "Status": "Enabled",
      "Filter": {"Prefix": "media/thumbnails/"},
      "Expiration": {"Days": 90}
    },
    {
      "ID": "transition-exports-to-glacier",
      "Status": "Enabled",
      "Filter": {"Prefix": "exports/"},
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ]
    }
  ]
}
```

### 7.5 RabbitMQ Topology

#### Exchange and Queue Architecture

```
                     ┌──────────────────────┐
                     │   Topic Exchange      │
                     │   amc.events          │
                     └────┬────┬────┬────┬───┘
                          │    │    │    │
         ┌────────────────┘    │    │    └────────────────┐
         │                     │    │                     │
         ▼                     ▼    ▼                     ▼
   ┌──────────┐        ┌─────────────┐           ┌──────────────┐
   │ Queue    │        │ Queue       │           │ Queue        │
   │ campaign │        │ notification│           │ analytics    │
   │ .created │        │ .all        │           │ .all         │
   └────┬─────┘        └──────┬──────┘           └──────┬───────┘
        │                     │                         │
        ▼                     ▼                         ▼
   ┌──────────┐        ┌─────────────┐           ┌──────────────┐
   │ campaign │        │ notification│           │ analytics    │
   │ -service │        │ -service    │           │ -service     │
   └──────────┘        └─────────────┘           └──────────────┘
```

#### Dead Letter and Retry

```python
# RabbitMQ topology setup
RABBITMQ_TOPOLOGY = {
    "exchanges": {
        "amc.events": {
            "type": "topic",
            "durable": True,
        },
        "amc.dlx": {  # Dead Letter Exchange
            "type": "direct",
            "durable": True,
        },
        "amc.retry": {  # Retry Exchange
            "type": "direct",
            "durable": True,
        },
    },
    "queues": {
        "campaign.created": {
            "exchange": "amc.events",
            "routing_key": "campaign.created",
            "dead_letter_exchange": "amc.dlx",
            "dead_letter_routing_key": "campaign.created.dlx",
        },
        "campaign.created.retry": {
            "exchange": "amc.retry",
            "routing_key": "campaign.created.retry",
            "message_ttl": 30_000,  # 30s before retry
            "dead_letter_exchange": "amc.events",
            "dead_letter_routing_key": "campaign.created",
        },
        "campaign.created.dlx": {
            "exchange": "amc.dlx",
            "routing_key": "campaign.created.dlx",
            "message_ttl": 300_000,  # 5min for manual inspection
        },
    },
}
```

#### Retry Flow

```
Message consumed → Processing fails
       │
       ▼
Publish to amc.retry (with TTL=30s)
       │
       ▼
Message expires from retry queue
       │
       ▼
Routed back to original queue via DLX
       │
       ▼
Retry (up to 3 times)
       │
       ├── Success → Ack
       │
       └── Failed 3× → Move to DLX queue → Admin notification
```

### 7.6 Data Flow Diagrams for Critical Paths

#### Campaign Dispatch Flow

```mermaid
sequenceDiagram
    participant UI as User (Browser)
    participant API as API Gateway
    participant MKT as Marketing Module
    participant RQ as RabbitMQ
    participant WKR as Campaign Workers
    participant DB as PostgreSQL
    participant EML as Email Service (SendGrid)
    participant SMS as SMS Service (Twilio)
    participant SOC as Social API
    participant ANL as Analytics

    UI->>API: POST /api/v1/marketing/campaigns/{id}/launch
    API->>MKT: Route to marketing module
    MKT->>DB: Validate campaign status = DRAFT
    MKT->>DB: Update campaign status → LAUNCHING
    MKT->>DB: Create campaign_launch record
    MKT-->>API: 202 Accepted (launch initiated)
    API-->>UI: { status: "launching", campaign_id }

    MKT->>RQ: Publish campaign.launched
    Note over MKT,RQ: Payload: campaign_id, workspace_id, channels, schedule

    RQ->>WKR: Deliver to campaign dispatch workers

    WKR->>DB: Fetch campaign full config + segments
    WKR->>DB: Fetch target contacts (paginated)

    par Email Channel
        WKR->>EML: Submit batch email send
        EML-->>WKR: Batch accepted
        WKR->>DB: Log email_sends
    and SMS Channel
        WKR->>SMS: Submit SMS batch
        SMS-->>WKR: Batch accepted
        WKR->>DB: Log sms_sends
    and Social Channel
        WKR->>SOC: Schedule social posts
        SOC-->>WKR: Posts scheduled
        WKR->>DB: Log social_posts
    end

    WKR->>DB: Update campaign status → ACTIVE / SCHEDULED
    WKR->>RQ: Publish campaign.dispatch_completed

    RQ->>ANL: analytics.campaign_dispatched
    ANL->>ANL: Update materialized analytics
```

#### Multi-Tenant Data Isolation Flow

```mermaid
sequenceDiagram
    participant U1 as User A (Tenant 1)
    participant U2 as User B (Tenant 2)
    participant GW as API Gateway
    participant SVC as Service Layer
    participant DB as PostgreSQL
    participant RD as Redis
    participant QR as Qdrant
    participant MO as MinIO

    Note over U1,GW: User A logs in
    U1->>GW: POST /auth/login
    GW->>GW: Validate credentials
    GW->>GW: Set JWT with tenant_id=tenant-1
    GW-->>U1: access_token (contains tenant-1)

    Note over U2,GW: User B logs in
    U2->>GW: POST /auth/login
    GW->>GW: Validate credentials
    GW->>GW: Set JWT with tenant_id=tenant-2
    GW-->>U2: access_token (contains tenant-2)

    Note over U1,DB: User A queries contacts
    U1->>GW: GET /api/v1/crm/contacts (JWT: tenant-1)
    GW->>SVC: Request with tenant_id=tenant-1
    SVC->>DB: SET app.current_tenant_id = 'tenant-1'
    SVC->>DB: SELECT * FROM contacts
    Note over DB: RLS adds: WHERE tenant_id = 'tenant-1'
    DB-->>SVC: Only Tenant 1 contacts
    SVC-->>U1: ✓

    Note over U2,DB: User B queries contacts (same endpoint)
    U2->>GW: GET /api/v1/crm/contacts (JWT: tenant-2)
    GW->>SVC: Request with tenant_id=tenant-2
    SVC->>DB: SET app.current_tenant_id = 'tenant-2'
    SVC->>DB: SELECT * FROM contacts
    Note over DB: RLS adds: WHERE tenant_id = 'tenant-2'
    DB-->>SVC: Only Tenant 2 contacts
    SVC-->>U2: ✓

    Note over U1,RD: Redis isolation
    U1->>GW: Create campaign
    SVC->>RD: SET cache:tenant-1:campaign_list [...]
    U2->>GW: Create campaign
    SVC->>RD: SET cache:tenant-2:campaign_list [...] (separate key)

    Note over U1,QR: Qdrant isolation
    U1->>GW: AI search knowledge
    SVC->>QR: Query collection knowledge_base_tenant-1
    QR-->>SVC: Only Tenant 1 documents

    Note over U1,MO: MinIO isolation
    U1->>GW: Upload media
    SVC->>MO: PUT /tenant-1/media/images/logo.png
    MO-->>SVC: ✓
    Note over MO: User B cannot access /tenant-1/...
    MO->>MO: IAM policy denies cross-tenant access
```

---

## 8. n8n Integration Architecture

### 8.1 Embedded Worker vs Dedicated n8n Cluster

AMC uses a **hybrid n8n deployment**:

| Component | Deployment Mode | Purpose |
|-----------|----------------|---------|
| **n8n Editor UI** | Embedded in AMC UI via iframe/embed | Users build workflows in a familiar n8n interface |
| **n8n Worker** | Standalone service (dedicated cluster) | Execute workflows — horizontally scalable |
| **n8n Webhook** | Standalone service | Receive webhook-triggered executions |
| **n8n Database** | Shared PostgreSQL (separate schema) | Workflow definitions, execution history, credentials |

```
┌────────────────────────────────────────────┐
│            AMC Application                   │
│  ┌────────────┐  ┌──────────────────────┐   │
│  │ Workflow   │  │ n8n Editor (embed)   │   │
│  │ Builder UI │──│ /n8n/editor          │   │
│  └────────────┘  └──────────┬───────────┘   │
│                              │               │
└──────────────────────────────┼───────────────┘
                               │
                    ┌──────────▼───────────┐
                    │  n8n API / Editor    │
                    │  (n8n-editor:5678)   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   n8n Workers (×N)   │
                    │  (n8n-worker:5679)   │
                    │  queue-based mode    │
                    └─────────────────────┘
```

### 8.2 Workflow Execution Model

```
User or AI Agent triggers workflow
         │
         ▼
automation-service receives trigger
         │
         ▼
POST /n8n/webhook/{workflow_id}  OR  n8n internal queue
         │
         ▼
n8n Worker picks up execution
         │
         ▼
┌─────────────────────────────────────────────┐
│         Workflow Execution                    │
│                                               │
│  Step 1: HTTP Request (fetch data from CRM)   │
│  Step 2: Function Node (transform data)       │
│  Step 3: Send Email (via notification-service)│
│  Step 4: Update CRM (write back)              │
│  Step 5: Log to Analytics                     │
└─────────────────────────────────────────────┘
         │
         ▼
Webhook callback to automation-service
         │
         ▼
automation-service records execution result
```

### 8.3 Cross-Module Action System

n8n workflows can trigger actions in any AMC module through a special **AMC Action Node** — a custom n8n node that wraps the REST API.

```typescript
// custom-nodes/AMCAction.node.ts
interface AMCActionNodeOptions {
  action: 'create_campaign' | 'send_email' | 'update_contact' | 'run_ai_agent' | 'generate_report';
  module: 'crm' | 'marketing' | 'ai' | 'analytics' | 'media';
  parameters: Record<string, any>;
}

class AMCActionNode implements INodeType {
  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[]> {
    const options = this.getNodeParameter('options') as AMCActionNodeOptions;
    const credentials = await this.getCredentials('amcApi');

    const response = await this.helpers.httpRequest({
      method: 'POST',
      url: `${credentials.baseUrl}/api/v1/${options.module}/${options.action}`,
      headers: {
        'Authorization': `Bearer ${credentials.apiKey}`,
        'X-Workspace-Id': credentials.workspaceId,
      },
      body: options.parameters,
    });

    return [{ json: response }];
  }
}
```

Available cross-module actions:

| Action | Module | Description |
|--------|--------|-------------|
| `create_contact` | CRM | Create a new contact |
| `update_contact` | CRM | Update contact properties |
| `add_to_segment` | CRM | Add contact to a segment |
| `create_campaign` | Marketing | Create a campaign draft |
| `send_email` | Marketing | Trigger an email send |
| `schedule_post` | Marketing | Schedule a social media post |
| `run_ai_agent` | AI | Invoke an AI agent with a task |
| `generate_report` | Analytics | Generate and export a report |
| `upload_media` | Media | Upload a file to media library |
| `search_knowledge` | Knowledge | Search knowledge base |
| `trigger_webhook` | Automation | Trigger another workflow |

### 8.4 Error Handling and Retry Architecture

```mermaid
flowchart TD
    A[Workflow Execution] --> B{Success?}
    B -->|Yes| C[Log success + Update stats]
    B -->|No| D{Retryable error?}

    D -->|Network timeout| E[Retry with backoff]
    D -->|API rate limit| E
    D -->|Validation error| F[Fail permanently]

    E --> G{Retries < 3?}
    G -->|Yes| H[Wait: 30s, 60s, 120s]
    H --> A
    G -->|No| I[Move to dead letter]

    F --> I
    I --> J[Notify admin]
    I --> K[Log to error analytics]
```

```python
class WorkflowExecutionManager:
    """Manages n8n workflow execution with retry and error handling."""

    RETRY_DELAYS = [30, 60, 120]  # seconds
    MAX_RETRIES = 3

    async def execute_with_retry(self, workflow_id: str, payload: dict) -> ExecutionResult:
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                result = await self._execute_workflow(workflow_id, payload)
                await self._log_success(workflow_id, result)
                return result
            except RetryableError as e:
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.warning(
                        "Workflow %s failed (attempt %d/%d), retrying in %ds: %s",
                        workflow_id, attempt + 1, self.MAX_RETRIES, delay, e,
                    )
                    await asyncio.sleep(delay)
                else:
                    await self._handle_failure(workflow_id, payload, e, attempt + 1)
                    raise
            except NonRetryableError as e:
                await self._handle_failure(workflow_id, payload, e, attempt + 1)
                raise
```

### 8.5 Workflow Versioning

n8n workflows are version-tracked through AMC's automation-service:

```python
class WorkflowVersion:
    """Represents a versioned n8n workflow."""

    def __init__(self):
        self.versions: dict[str, list[VersionRecord]] = {}

    async def save_version(self, workflow_id: str, workflow_data: dict) -> VersionRecord:
        """Save a new version of a workflow."""
        version = VersionRecord(
            version_id=uuid4(),
            workflow_id=workflow_id,
            version_number=await self._next_version(workflow_id),
            workflow_data=workflow_data,
            created_at=datetime.utcnow(),
            checksum=hashlib.sha256(json.dumps(workflow_data, sort_keys=True).encode()).hexdigest(),
        )
        await self._store_version(version)
        return version

    async def rollback(self, workflow_id: str, target_version: int):
        """Rollback a workflow to a previous version."""
        version = await self._get_version(workflow_id, target_version)
        await self._update_n8n_workflow(workflow_id, version.workflow_data)
        return version

    async def compare_versions(self, workflow_id: str, v1: int, v2: int) -> dict:
        """Diff two versions of a workflow."""
        v1_data = await self._get_version(workflow_id, v1)
        v2_data = await self._get_version(workflow_id, v2)
        return self._compute_diff(v1_data.workflow_data, v2_data.workflow_data)
```

---

## 9. Scalability & Performance

### 9.1 Horizontal Scaling Strategy Per Layer

| Layer | Scaling Unit | Autoscaling Trigger | Max Instances | Notes |
|-------|-------------|--------------------|---------------|-------|
| **CDN** | Edge locations | N/A (global) | N/A | CloudFront/Cloudflare handles global distribution |
| **API Gateway** | FastAPI process (container) | CPU > 70% or req/s > 1000/instance | 20 | Stateless — scale horizontally behind load balancer |
| **Modular Monolith** | Container instance | CPU > 70% or req/s > 500/instance | 10 | ElastiCache + PgBouncer handle connection scale |
| **auth-service** | Container instance | CPU > 60% | 5 | Stateless JWT validation, fast spin-up |
| **ai-service** | Container instance | Queue depth > 100 | 10 | GPU-backed for NIM, CPU-only for orchestration |
| **notification-service** | Container instance | Queue depth > 1000 | 8 | Multi-channel delivery — scale per channel |
| **analytics-service** | Container instance | Memory > 70% | 6 | Heavy aggregation queries |
| **media-service** | Container instance + worker pool | Queue depth > 50 | 4 + 10 workers | Processing workers can lag behind ingestion |
| **n8n workers** | Container instance | Queue depth > 200 | 20 | CPU-bound workflow execution |
| **PostgreSQL** | Read replicas | Read replica CPU > 70% | 3 read replicas | Primary handles writes only |
| **Redis** | Cluster shards | Memory > 75% per node | 6 shards + replicas | Auto-resharding |
| **Qdrant** | Cluster nodes | RAM > 80% | 6 nodes | Vectors held in RAM for fast search |
| **RabbitMQ** | Cluster nodes | Queue depth > 10K | 3 nodes | Disk-based queues for overflow |

### 9.2 Caching Strategy (Multi-Tier)

```
Browser/CDN Cache
     │
     ▼
Application Cache (In-memory — Python dict / LRU)
     │
     ▼
Redis Cache (Distributed — Cluster)
     │
     ▼
PostgreSQL (Database — Primary + Replicas)
```

#### Cache Layers Detail

| Tier | Location | Data | TTL | Invalidation |
|------|----------|------|-----|-------------|
| **L1: Browser** | Service Worker + HTTP Cache | Static assets, API responses | Varied | SW version bump, Cache-Control headers |
| **L2: CDN** | Edge (CloudFront) | Static assets, public API responses | 1h–7d | Cache invalidation API on deploy |
| **L3: Application** | Python in-memory (LRU) | Reference data (tenant config, feature flags) | 5min | TTL-based, manual invalidation via Redis pub/sub |
| **L4: Redis** | Distributed cache cluster | API responses, session data, rate limit counters | 1min–24h | TTL-based, event-driven invalidation |
| **L5: Database** | PostgreSQL shared buffers + replicas | All transactional data | N/A | Writes invalidate dependent caches |

#### Cache Invalidation Strategy

```python
class CacheInvalidator:
    """Event-driven cache invalidation."""

    async def on_domain_event(self, event: DomainEvent):
        """Listen for domain events and invalidate related caches."""
        invalidation_rules = {
            "contact.updated": [
                "crm:contact:{contact_id}",
                "crm:contacts:list:{workspace_id}:*",
                "crm:segment:{segment_id}:contacts",
            ],
            "campaign.launched": [
                "marketing:campaign:{campaign_id}",
                "marketing:campaigns:list:{workspace_id}:*",
            ],
            "tenant.settings_updated": [
                "tenant:settings:{tenant_id}",
                "tenant:config:*",
            ],
        }

        patterns = invalidation_rules.get(event.type, [])
        for pattern in patterns:
            # Pattern-based deletion (Redis SCAN + DEL)
            await self._delete_patterns(pattern.format(**event.payload))
```

### 9.3 Database Scaling

#### Read Replicas Architecture

```
                    ┌──────────────┐
                    │  PostgreSQL  │
                    │   Primary    │
                    │ (Read/Write) │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ Replica 1│  │ Replica 2│  │ Replica 3│
      │ (Read)   │  │ (Read)   │  │ (Read)   │
      │ EU West  │  │ US East  │  │ APAC     │
      └──────────┘  └──────────┘  └──────────┘
            │              │              │
            ▼              ▼              ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │PgBouncer │  │PgBouncer │  │PgBouncer │
      │ (pool)   │  │ (pool)   │  │ (pool)   │
      └──────────┘  └──────────┘  └──────────┘
```

**Read/write split in application:**

```python
class DatabaseRouter:
    """Route read queries to replicas, writes to primary."""

    def __init__(self):
        self.primary = "postgresql://user:pass@pg-primary:5432/amc"
        self.replicas = [
            "postgresql://user:pass@pg-replica-1:5432/amc",
            "postgresql://user:pass@pg-replica-2:5432/amc",
        ]

    def get_connection(self, read_only: bool = False):
        if read_only:
            return random.choice(self.replicas)  # Simple round-robin
        return self.primary
```

#### Sharding Considerations

AMC does **not** shard PostgreSQL at launch. Sharding adds significant complexity (cross-shard queries, distributed transactions, rebalancing). Instead:

- **Vertical scaling** first: larger instance types (up to 64 vCPU, 512GB RAM)
- **Read replicas** for read-heavy workloads
- **Partitioning** for time-series data (campaign_events, email_sends)
- **Materialized views** for analytics queries
- **Future sharding** if/when a single tenant exceeds 10TB or 100K TPS

**If sharding becomes necessary, the strategy would be:**

| Approach | Pros | Cons | Decision |
|----------|------|------|----------|
| **Citus** (PostgreSQL extension) | Transparent sharding, SQL compatible | Vendor dependency, operational complexity | Preferred if needed |
| **Application-level sharding** (by tenant_id) | Full control | Query routing complexity, cross-shard joins impossible | Fallback |
| **Separate database per tenant** | Maximum isolation | Connection management, no cross-tenant queries | Enterprise tier only |

#### Connection Pooling

| Pool | Purpose | Max Connections | Pool Mode |
|------|---------|----------------|-----------|
| **PgBouncer (transaction)** | API Gateway → Primary | 100 | Transaction |
| **PgBouncer (transaction)** | API Gateway → Replicas | 200 | Transaction |
| **PgBouncer (session)** | Admin tools, migrations | 10 | Session |
| **Application pool** | Internal workers | 20 | Transaction |

### 9.4 AI Inference Caching and Batching

#### Inference Cache

```python
class InferenceCache:
    """Cache AI inference results to reduce cost and latency."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def get_or_compute(
        self,
        cache_key: str,
        compute_fn: Callable,
        ttl: int = 300,
        semantic_threshold: float = 0.95,
    ) -> InferenceResult:
        """Check cache, return cached if high semantic similarity, else compute."""

        # 1. Exact match cache (Redis)
        cached = await self.redis.get(f"ai:inference:{cache_key}")
        if cached:
            return InferenceResult.parse_raw(cached)

        # 2. Semantic cache (Qdrant) — similar queries may share results
        similar = await self._search_semantic_cache(cache_key)
        if similar and similar.score >= semantic_threshold:
            await self.redis.setex(f"ai:inference:{cache_key}", ttl, similar.result.json())
            return similar.result

        # 3. Compute fresh
        result = await compute_fn()
        await self.redis.setex(f"ai:inference:{cache_key}", ttl, result.json())
        await self._store_semantic_cache(cache_key, result)
        return result
```

#### Request Batching

```python
class InferenceBatcher:
    """Batch multiple concurrent inference requests into a single call."""

    def __init__(self, max_batch_size: int = 32, max_wait_ms: int = 50):
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._pending: list[tuple[str, asyncio.Future]] = []

    async def submit(self, request: InferenceRequest) -> InferenceResult:
        """Submit a request for batched inference."""
        future = asyncio.get_event_loop().create_future()
        self._pending.append((request, future))

        if len(self._pending) >= self.max_batch_size:
            asyncio.ensure_future(self._flush())
        elif len(self._pending) == 1:
            # Schedule flush after max_wait_ms
            asyncio.ensure_future(self._delayed_flush())

        return await future

    async def _flush(self):
        """Execute batched inference."""
        batch = self._pending[:]
        self._pending.clear()
        try:
            results = await self._execute_batch([r for r, _ in batch])
            for (_, future), result in zip(batch, results):
                future.set_result(result)
        except Exception as e:
            for _, future in batch:
                if not future.done():
                    future.set_exception(e)
```

---

## 10. High Availability Design

### 10.1 Multi-AZ Deployment

AMC is designed to run across **3 Availability Zones** (AZs) within a cloud region, with full redundancy in each AZ.

```
                    ┌──────────────────────────────────────┐
                    │         Cloud Region (us-east-1)      │
                    │                                       │
                    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ │
                    │  │   AZ A   │ │   AZ B   │ │   AZ C   │ │
                    │  │          │ │          │ │          │ │
                    │  │  GW × 2  │ │  GW × 2  │ │  GW × 2  │ │
                    │  │  App × 2 │ │  App × 2 │ │  App × 2 │ │
                    │  │  Redis M │ │  Redis R │ │  Redis R │ │
                    │  │  Qdrant  │ │  Qdrant  │ │  Qdrant  │ │
                    │  │          │ │          │ │          │ │
                    │  └────┬─────┘ └────┬─────┘ └────┬─────┘ │
                    │       │            │            │        │
                    │       └────────────┼────────────┘        │
                    │                    │                      │
                    │           ┌────────▼────────┐            │
                    │           │  PostgreSQL     │            │
                    │           │  (Primary in A, │            │
                    │           │   Sync replica B,             │
                    │           │   Async replica C)│           │
                    │           └─────────────────┘            │
                    └──────────────────────────────────────────┘
```

### 10.2 Failover Strategy

| Component | Failure Mode | Detection | Failover Action | RTO | RPO |
|-----------|-------------|-----------|----------------|-----|-----|
| **API Gateway** | Instance crash | Load balancer health check | Route to remaining instances | < 1s | N/A |
| **Service (monolith)** | Instance crash | Load balancer health check | Route to remaining instances | < 1s | N/A |
| **PostgreSQL Primary** | Instance/disk failure | pg_auto_failover / Patroni | Promote sync replica to primary | < 30s | 0 (sync) |
| **PostgreSQL Replica** | Instance crash | Health check | Route reads to other replicas | < 5s | N/A |
| **Redis** | Node failure | Sentinel | Promote replica, update sentinel | < 10s | < 1s |
| **Qdrant** | Node failure | Raft consensus | Remaining nodes continue (Raft quorum) | < 5s | N/A (RF=2) |
| **RabbitMQ** | Node failure | Cluster health check | Queues mirrored to other nodes | < 10s | N/A |
| **MinIO** | Node failure | Erasure coding reconstruction | Read from remaining shards | < 1s | N/A |
| **n8n Worker** | Crash | Queue-based work stealing | Another worker picks up the task | < 5s | N/A |
| **Full AZ failure** | All resources in one AZ | Cloud provider event | Route to remaining AZs | < 5min | < 5min |

### 10.3 Disaster Recovery (RPO/RTO Targets)

| Scenario | RPO (Recovery Point Objective) | RTO (Recovery Time Objective) | Strategy |
|----------|-------------------------------|-------------------------------|----------|
| **Single instance failure** | 0 (no data loss) | < 1 min | Redundant instances, automatic failover |
| **AZ failure** | < 5 min | < 5 min | Multi-AZ deployment, traffic shifting |
| **Region failure** | < 15 min | < 60 min | Cross-region backup + restore (warm standby for Enterprise) |
| **Data corruption** | < 5 min (point-in-time recovery) | < 30 min | PITR from WAL archives (14-day window) |
| **Accidental deletion** | < 5 min | < 30 min | Soft delete + bucket versioning + trash bin |
| **Full region disaster** | < 1 hour | < 4 hours | Cross-region backup to MinIO secondary region |

### 10.4 Backup Architecture

```
┌────────────────────────────────────────────────────┐
│                   Backup Schedule                    │
├────────────┬─────────────┬──────────┬──────────────┤
│  Component │  Frequency   │ Retention│   Method      │
├────────────┼─────────────┼──────────┼──────────────┤
│ PostgreSQL │ Full: daily  │ 14 days  │ pg_dump →     │
│            │ WAL: 5min    │ 14 days  │ MinIO backup  │
│            │ PITR: yes    │          │ bucket        │
├────────────┼─────────────┼──────────┼──────────────┤
│ PostgreSQL │ Monthly     │ 12 months│ pg_dump →     │
│            │ archive     │          │ Glacier       │
├────────────┼─────────────┼──────────┼──────────────┤
│ Qdrant     │ Snapshot:   │ 7 days   │ qdrant snapshot│
│            │ daily       │          │ → MinIO       │
├────────────┼─────────────┼──────────┼──────────────┤
│ Redis      │ RDB: hourly │ 24 hours │ SAVE → MinIO  │
├────────────┼─────────────┼──────────┼──────────────┤
│ MinIO      │ Bucket      │ 30 days  │ MinIO bucket  │
│            │ replication │          │ replication   │
├────────────┼─────────────┼──────────┼──────────────┤
│ n8n        │ Workflow    │ Real-time│ Shared PG     │
│            │ definitions │          │ (covered by   │
│            │             │          │ PG backup)    │
├────────────┼─────────────┼──────────┼──────────────┤
│ Config     │ Terraform   │ Git      │ State in      │
│            │ state       │ history  │ S3 backend +  │
│            │             │          │ versioned     │
└────────────┴─────────────┴──────────┴──────────────┘
```

**Backup verification:**

```bash
#!/bin/bash
# scripts/verify-backup.sh
# Run daily to verify backups are restorable

set -euo pipefail

BACKUP_DATE=$(date +%Y-%m-%d)
RESTORE_TEST_DB="amc_backup_verify_${BACKUP_DATE}"

echo "=== Backup Verification: $BACKUP_DATE ==="

# 1. Download latest backup
echo "Downloading backup..."
mc cp minio/backups/postgresql/amc_${BACKUP_DATE}.sql.gz /tmp/

# 2. Restore to test database
echo "Restoring to test database..."
gunzip -c /tmp/amc_${BACKUP_DATE}.sql.gz | \
  psql -h pg-test -U amc -d $RESTORE_TEST_DB

# 3. Run integrity checks
echo "Running integrity checks..."
psql -h pg-test -U amc -d $RESTORE_TEST_DB -c "
  SELECT COUNT(*) as total_tenants FROM tenants;
  SELECT COUNT(*) as total_contacts FROM contacts;
  -- Check RLS policies exist
  SELECT tablename, policyname FROM pg_policies WHERE tablename = 'contacts';
" > /tmp/backup_verify_report_${BACKUP_DATE}.txt

# 4. Cleanup
echo "Cleaning up..."
psql -h pg-test -U amc -c "DROP DATABASE IF EXISTS $RESTORE_TEST_DB;"
rm /tmp/amc_${BACKUP_DATE}.sql.gz

echo "=== Verification Complete ==="
```

---

## 11. Deployment Architecture

### 11.1 Docker Compose (Development)

```yaml
# deployment/docker-compose.yml
version: "3.9"

services:
  # ── API Gateway ──
  api-gateway:
    build:
      context: .
      dockerfile: deployment/Dockerfile.api-gateway
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://amc:amc@pgbouncer:6432/amc
      - REDIS_URL=redis://redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:amc@rabbitmq:5672/
      - NIM_ENDPOINT=http://nim-dgx:8001/v1
    depends_on:
      pgbouncer:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    volumes:
      - ./backend:/app # Hot reload
    command: uvicorn api_gateway.main:app --reload --host 0.0.0.0 --port 8000

  # ── Modular Monolith ──
  monolith:
    build:
      context: .
      dockerfile: deployment/Dockerfile.monolith
    environment:
      - DATABASE_URL=postgresql://amc:amc@pgbouncer:6432/amc
      - REDIS_URL=redis://redis-cache:6379/0
      - RABBITMQ_URL=amqp://amc:amc@rabbitmq:5672/
    depends_on:
      pgbouncer:
        condition: service_healthy
      redis-cache:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    volumes:
      - ./backend:/app
    command: uvicorn monolith.main:app --reload --host 0.0.0.0 --port 8001

  # ── Frontend ──
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
      - NEXT_PUBLIC_GRAPHQL_URL=http://localhost:8000/api/v1/graphql
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  # ── PostgreSQL ──
  postgres-primary:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: amc
      POSTGRES_PASSWORD: amc
      POSTGRES_DB: amc
    ports:
      - "5432:5432"
    volumes:
      - pg-data:/var/lib/postgresql/data
      - ./deployment/postgres/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U amc"]
      interval: 5s

  postgres-replica:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: amc
      POSTGRES_PASSWORD: amc
      POSTGRES_DB: amc
    depends_on:
      postgres-primary:
        condition: service_healthy
    volumes:
      - pg-replica-data:/var/lib/postgresql/data
    command: >
      bash -c "until pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U amc -vP -W; do
        sleep 2; done;
        echo 'primary_conninfo = host=postgres-primary port=5432 user=amc password=amc' >> /var/lib/postgresql/data/postgresql.conf;
        pg_ctl -D /var/lib/postgresql/data start;"

  # ── PgBouncer ──
  pgbouncer:
    image: edoburu/pgbouncer:latest
    environment:
      DB_USER: amc
      DB_PASSWORD: amc
      DB_HOST: postgres-primary
      DB_PORT: "5432"
      DB_NAME: amc
      POOL_MODE: transaction
      MAX_CLIENT_CONN: "500"
      DEFAULT_POOL_SIZE: "50"
    ports:
      - "6432:6432"
    depends_on:
      postgres-primary:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "pgbouncer -q show databases"]

  # ── Redis ──
  redis-cache:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s

  # ── Qdrant ──
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant-data:/qdrant/storage
    environment:
      QDRANT__SERVICE__GRPC_PORT: "6334"

  # ── MinIO ──
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"

  # ── RabbitMQ ──
  rabbitmq:
    image: rabbitmq:3.13-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: amc
      RABBITMQ_DEFAULT_PASS: amc
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 10s

  # ── n8n ──
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    volumes:
      - n8n-data:/home/node/.n8n
    environment:
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      N8N_HOST: localhost
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: pgbouncer
      DB_POSTGRESDB_PORT: 6432
      DB_POSTGRESDB_DATABASE: amc_n8n
      DB_POSTGRESDB_USER: amc
      DB_POSTGRESDB_PASSWORD: amc
      N8N_METRICS: "true"
      N8N_METRICS_INCLUDE_DEFAULT_METRICS: "true"

  # ── Prometheus ──
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - prometheus-data:/prometheus
      - ./deployment/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  # ── Grafana ──
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./deployment/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./deployment/grafana/datasources:/etc/grafana/provisioning/datasources

  # ── Loki ──
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - loki-data:/loki
      - ./deployment/loki/loki-config.yaml:/etc/loki/local-config.yaml

  # ── Promtail ──
  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./deployment/loki/promtail-config.yaml:/etc/promtail/config.yaml

volumes:
  pg-data:
  pg-replica-data:
  redis-data:
  qdrant-data:
  minio-data:
  rabbitmq-data:
  n8n-data:
  prometheus-data:
  grafana-data:
  loki-data:
```

### 11.2 Docker Swarm / Kubernetes (Production)

**Production strategy:** Start with **Docker Swarm** for its simplicity (built into Docker Engine, no additional orchestration layer to manage). Plan for **Kubernetes migration** in Year 2–3 when the infrastructure team has matured and the scaling demands warrant it.

| Factor | Docker Swarm | Kubernetes | AMC Decision |
|--------|-------------|------------|--------------|
| **Setup complexity** | Low | High | Swarm for v1 (faster time-to-market) |
| **Built-in** | Yes (Docker Engine) | No (additional control plane) | Swarm wins for early stage |
| **Auto-scaling** | Manual | HPA (Horizontal Pod Autoscaler) | K8s needed at scale |
| **Service mesh** | Traefik/Nginx | Istio/Linkerd | K8s advantage |
| **Storage orchestration** | Basic | CSI drivers, StatefulSets | K8s advantage |
| **Learning curve** | Low | High | Swarm for current team |

#### Docker Swarm Stack (Production)

```yaml
# deployment/docker-stack.yml
version: "3.9"

x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:
  api-gateway:
    image: ${REGISTRY}/amc-api-gateway:${TAG}
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
        order: start-first
      resources:
        limits:
          cpus: "1"
          memory: 512M
      labels:
        - "traefik.enable=true"
        - "traefik.http.routers.api.rule=Host(`api.amc.io`) && PathPrefix(`/api`)"
        - "traefik.http.services.api.loadbalancer.server.port=8000"
    networks:
      - amc-net
    logging: *default-logging

  monolith:
    image: ${REGISTRY}/amc-monolith:${TAG}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: "2"
          memory: 1G
    networks:
      - amc-net
    logging: *default-logging

  # ... (similar for all services)

networks:
  amc-net:
    driver: overlay
    attachable: true
```

### 11.3 GitHub Actions CI/CD Pipeline Architecture

```mermaid
flowchart LR
    DEV[Developer Push] --> GH[GitHub]
    GH --> CI[CI Pipeline]

    subgraph CI["CI Pipeline (GitHub Actions)"]
        LINT["Lint & Format<br/>(ruff, prettier, eslint)"]
        TYPE["Type Check<br/>(mypy, TypeScript)"]
        UNIT["Unit Tests<br/>(pytest, jest)"]
        BUILD["Build<br/>(Docker image)"]
        SCAN["Security Scan<br/>(trivy, snyk)"]
    end

    LINT --> TYPE
    TYPE --> UNIT
    UNIT --> BUILD
    BUILD --> SCAN

    SCAN -->|Success| CD["CD Pipeline"]

    subgraph CD["CD Pipeline (per environment)"]
        STAGING["Deploy to Staging<br/>(Docker Swarm)"]
        SMOKE["Smoke Tests<br/>(integration + e2e)"]
        APPROVAL["Manual Approval<br/>(QA gate)"]
        PROD["Deploy to Production<br/>(Blue-Green)"]
        HEALTH["Health Check<br/>(5 min observation)"]
    end

    SCAN -->|Failure| FAIL["Notify Team ❌"]
    STAGING --> SMOKE
    SMOKE --> APPROVAL
    APPROVAL --> PROD
    PROD --> HEALTH
    HEALTH -->|Pass| DONE["Deploy Complete ✅"]
    HEALTH -->|Fail| ROLLBACK["Auto Rollback"]
```

#### GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop, 'release/*']
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io/aegis-marketing-cloud
  TAG: ${{ github.sha }}

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Python lint
        run: |
          pip install ruff
          ruff check backend/
      - name: TypeScript lint
        run: |
          cd frontend
          npm ci
          npm run lint

  test:
    needs: lint
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: amc
          POSTGRES_PASSWORD: amc
          POSTGRES_DB: amc_test
        ports:
          - 5432:5432
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    steps:
      - uses: actions/checkout@v4
      - name: Run backend tests
        run: |
          cd backend
          pip install -e ".[dev]"
          pytest tests/ --cov=. --cov-report=xml
      - name: Run frontend tests
        run: |
          cd frontend
          npm ci
          npm run test:ci

  build-and-scan:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker images
        run: |
          docker build -f deployment/Dockerfile.api-gateway \
            -t $REGISTRY/api-gateway:$TAG .
          docker build -f deployment/Dockerfile.monolith \
            -t $REGISTRY/monolith:$TAG .
      - name: Security scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/api-gateway:${{ env.TAG }}
          severity: CRITICAL,HIGH
      - name: Push images
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker push $REGISTRY/api-gateway:$TAG
          docker push $REGISTRY/monolith:$TAG

  deploy-staging:
    needs: build-and-scan
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to staging
        run: |
          docker stack deploy -c deployment/docker-stack.yml amc-staging
      - name: Run smoke tests
        run: |
          sleep 30  # Wait for services to become healthy
          ./scripts/smoke-test.sh https://staging.amc.io

  deploy-production:
    needs: deploy-staging
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Blue-green deploy
        run: |
          # Deploy to standby stack
          docker stack deploy -c deployment/docker-stack.yml amc-production-blue
          # Wait for health
          sleep 60
          # Swap load balancer
          ./scripts/swap-traffic.sh blue
          # Scale down old stack
          docker stack rm amc-production-green
```

### 11.4 Blue-Green Deployment Strategy

```
                    ┌──────────────┐
                    │  Load        │
                    │  Balancer    │
                    │  (Traefik)   │
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
      ┌──────────┐   ┌──────────┐   ┌──────────┐
      │  Active  │   │  Active  │   │  Active  │
      │  (Green) │   │  (Green) │   │  (Green) │
      │  v1.5.3  │   │  v1.5.3  │   │  v1.5.3  │
      └──────────┘   └──────────┘   └──────────┘
            ▲
            │  ┌─── Cutover ───┐
            │  │               │
            └──┼───────────────┘
               │
      ┌────────┴────────┐   ┌──────────┐   ┌──────────┐
      │   Standby        │   │  Standby │   │  Standby │
      │   (Blue)         │   │  (Blue)  │   │  (Blue)  │
      │   v1.6.0         │   │  v1.6.0  │   │  v1.6.0  │
      └─────────────────┘   └──────────┘   └──────────┘
```

**Deployment steps:**

1. **Deploy Blue** (standby) — New version is deployed alongside the current (Green) stack
2. **Verify Blue** — Automated smoke tests run against Blue stack's internal endpoint
3. **Swap traffic** — Load balancer gradually shifts traffic from Green to Blue (10% → 50% → 100%)
4. **Observe** — 5-minute health observation window
5. **Scale down Green** — Previous version is scaled down (but kept for 24h for instant rollback)

**Rollback:** If issues are detected, the load balancer swaps back to Green within seconds.

### 11.5 Feature Flags Infrastructure

AMC uses **Unleash** (self-hosted) as the feature flag platform, integrated into both backend and frontend.

```python
# lib/feature_flags.py
class FeatureFlags:
    """Feature flag client wrapper."""

    def __init__(self, unleash_client):
        self.client = unleash_client

    async def is_enabled(
        self,
        flag_name: str,
        context: FlagContext,
        default: bool = False,
    ) -> bool:
        """Check if a feature is enabled for the given context."""
        return await self.client.is_enabled(
            flag_name,
            {
                "userId": context.user_id,
                "tenantId": context.tenant_id,
                "tenantTier": context.tenant_tier,
                "environment": context.environment,
            },
            default,
        )

    async def get_variant(self, flag_name: str, context: FlagContext) -> str:
        """Get A/B test variant assignment."""
        variant = await self.client.get_variant(flag_name, {
            "userId": context.user_id,
            "tenantId": context.tenant_id,
        })
        return variant.name or "disabled"
```

**Flag categories:**

| Category | Example | Rollout Strategy |
|----------|---------|-----------------|
| **Release flags** | `new-campaign-builder` | Gradual % rollout → 100% |
| **Experiment flags** | `ai-writer-v2-prompt` | A/B test (50/50) → analyze → promote |
| **Operational flags** | `disable-email-delivery` | Instant kill switch (ops emergencies) |
| **Permission flags** | `ai-agent-autonomous-mode` | Enterprise tier only; beta users only |
| **Migration flags** | `use-new-contacts-index` | Gradual migration: 1% → 10% → 50% → 100% |

---

## 12. Observability Architecture

### 12.1 Structured Logging (JSON, Correlation IDs, Loki)

Every log line in AMC is a structured JSON object, making it queryable and parseable by Loki, Elasticsearch, or any log aggregator.

```python
# lib/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger("amc")

# Usage
await logger.info(
    "campaign_launched",
    campaign_id=campaign.id,
    workspace_id=workspace.id,
    channels=["email", "social"],
    contact_count=segment.contact_count,
    duration_ms=elapsed_ms,
    trace_id=current_trace_id(),
)
```

#### Log Output Example

```json
{
  "event": "campaign_launched",
  "level": "info",
  "timestamp": "2026-06-19T14:30:00.123456Z",
  "logger": "amc.marketing",
  "service": "monolith",
  "trace_id": "ab8c3d9e1f2a4b5c",
  "span_id": "9e8d7c6b5a4f3e2d",
  "campaign_id": "camp-abc-123",
  "workspace_id": "ws-def-456",
  "channels": ["email", "social"],
  "contact_count": 15000,
  "duration_ms": 3420,
  "environment": "production",
  "host": "monolith-7f9a8b"
}
```

### 12.2 Metrics (Prometheus Counters, Histograms, Gauges)

```python
# lib/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary

# ── API Metrics ──
http_requests_total = Counter(
    "amc_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status", "tenant_tier"],
)

http_request_duration_seconds = Histogram(
    "amc_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
    buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10],
)

# ── Database Metrics ──
db_query_duration_seconds = Histogram(
    "amc_db_query_duration_seconds",
    "Database query latency",
    ["query_type", "table"],
    buckets=[.001, .005, .01, .025, .05, .1, .25, .5, 1],
)

db_connections_active = Gauge(
    "amc_db_connections_active",
    "Active database connections",
    ["pool_name"],
)

# ── Cache Metrics ──
cache_hit_ratio = Gauge(
    "amc_cache_hit_ratio",
    "Cache hit ratio (0.0–1.0)",
    ["cache_layer", "cache_name"],
)

# ── AI Metrics ──
ai_inference_duration_seconds = Histogram(
    "amc_ai_inference_duration_seconds",
    "AI inference latency",
    ["model", "provider", "task_type"],
    buckets=[.1, .5, 1, 2.5, 5, 10, 30],
)

ai_inference_total = Counter(
    "amc_ai_inference_total",
    "Total AI inference calls",
    ["model", "provider", "tenant_tier"],
)

ai_inference_cost_total = Counter(
    "amc_ai_inference_cost_total_usd",
    "Total AI inference cost in USD",
    ["model", "provider", "tenant_tier"],
)

# ── Business Metrics ──
campaigns_dispatched = Counter(
    "amc_campaigns_dispatched_total",
    "Total campaigns dispatched",
    ["channel", "tenant_tier"],
)

contacts_processed = Counter(
    "amc_contacts_processed_total",
    "Total contacts processed",
    ["tenant_tier"],
)
```

### 12.3 Distributed Tracing (OpenTelemetry)

Every request that enters the API Gateway is traced with OpenTelemetry, propagating context across all services via W3C `traceparent` headers.

```python
# lib/tracing.py
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor

def setup_tracing(service_name: str):
    provider = TracerProvider(
        resource=Resource.create({
            "service.name": service_name,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })
    )
    processor = BatchSpanProcessor(
        OTLPSpanExporter(endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317"))
    )
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Auto-instrumentation
    FastAPIInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    AioPikaInstrumentor().instrument()
```

**Trace propagation across services:**

```
Browser                         API Gateway                    Monolith                     PostgreSQL
  │                                  │                              │                            │
  │  Request                         │                              │                            │
  │─────────────────────────────────►│                              │                            │
  │                                  │  traceparent: 00-abc...     │                            │
  │                                  │─────────────────────────────►│                            │
  │                                  │                              │  traceparent: 00-abc...   │
  │                                  │                              │───────────────────────────►│
  │                                  │                              │                            │
  │                                  │                              │◄───────────────────────────│
  │                                  │◄─────────────────────────────│                            │
  │◄─────────────────────────────────│                              │                            │

Trace:
  ┌──────────────────────────────────────────────────────────────────┐
  │  Span 1: GET /api/v1/crm/contacts (160ms)                       │
  │  ├── Span 1.1: auth.ValidateToken (12ms)                       │
  │  ├── Span 1.2: monolith.list_contacts (98ms)                   │
  │  │   ├── Span 1.2.1: db.SELECT contacts (45ms)                │
  │  │   └── Span 1.2.2: db.SELECT segments (32ms)                │
  │  └── Span 1.3: cache.check_campaign_ctx (8ms)                 │
  └──────────────────────────────────────────────────────────────────┘
```

### 12.4 Alerting (Grafana Alerting + Alertmanager)

```yaml
# deployment/grafana/alert-rules.yml
groups:
  - name: amc-service-health
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(amc_http_requests_total{status=~"5.."}[5m]))
          /
          sum(rate(amc_http_requests_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Error rate > 1% for 5 minutes"

      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, rate(amc_http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency > 2s"

      - alert: DatabaseConnectionExhausted
        expr: amc_db_connections_active{pool_name="primary"} > 80
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near exhaustion"

      - alert: AICostAnomaly
        expr: |
          rate(amc_ai_inference_cost_total_usd[1h]) > 50
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "AI inference cost > $50/hour"

      - alert: CampaignDispatchFailure
        expr: |
          rate(amc_campaigns_dispatched_total{status="failed"}[5m]) > 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Campaign dispatch failures detected"

      - alert: CacheHitRatioDrop
        expr: amc_cache_hit_ratio{cache_layer="redis"} < 0.7
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Redis cache hit ratio below 70%"

      - alert: QueueBacklog
        expr: amq_queue_messages_ready > 10000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "RabbitMQ queue backlog > 10,000 messages"
```

### 12.5 Dashboards (Service Health, Business Metrics, Cost)

#### Dashboard Architecture

| Dashboard | Audience | Purpose | Key Panels |
|-----------|----------|---------|------------|
| **Service Health** | Engineering | Monitor system uptime, latency, errors | API latency (P50/P95/P99), error rate by service, database connections, queue depths, cache hit ratio |
| **Business Metrics** | Product / Ops | Monitor platform usage and growth | Signups, active workspaces, campaigns dispatched, contacts processed, AI queries, NPS |
| **Cost Dashboard** | Engineering / Finance | Track infrastructure and AI costs | AI inference cost by model/provider, infrastructure cost by service, cost per tenant tier, cost per campaign |
| **AI Performance** | AI team | Monitor AI agent effectiveness | Agent response time, tool success rate, inference cache hit ratio, prompt version performance, agent error rate |
| **Security** | Security team | Detect anomalies | Failed auth attempts, rate limit hits, suspicious IPs, API key usage anomalies |

#### Grafana Dashboard JSON Model

```json
{
  "title": "AMC - Service Health",
  "panels": [
    {
      "title": "API Error Rate (5xx)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(rate(amc_http_requests_total{status=~\"5..\"}[5m])) / sum(rate(amc_http_requests_total[5m]))",
          "legendFormat": "Error Rate"
        }
      ],
      "alert": {
        "conditions": [{ "type": "threshold", "threshold": 0.01 }]
      }
    },
    {
      "title": "API Latency (P50 / P95 / P99)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.50, rate(amc_http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "P50"
        },
        {
          "expr": "histogram_quantile(0.95, rate(amc_http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "P95"
        },
        {
          "expr": "histogram_quantile(0.99, rate(amc_http_request_duration_seconds_bucket[5m]))",
          "legendFormat": "P99"
        }
      ]
    },
    {
      "title": "Active Database Connections",
      "type": "stat",
      "targets": [
        {
          "expr": "amc_db_connections_active{pool_name=\"primary\"}"
        }
      ]
    },
    {
      "title": "RabbitMQ Queue Depth",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(amq_queue_messages_ready) by (queue)",
          "legendFormat": "{{queue}}"
        }
      ]
    },
    {
      "title": "Cache Hit Ratio",
      "type": "timeseries",
      "targets": [
        {
          "expr": "amc_cache_hit_ratio{cache_layer=\"redis\"}",
          "legendFormat": "Redis"
        }
      ]
    },
    {
      "title": "AI Inference Cost (USD/hr)",
      "type": "timeseries",
      "targets": [
        {
          "expr": "rate(amc_ai_inference_cost_total_usd[1h])",
          "legendFormat": "Cost/hr"
        }
      ]
    }
  ]
}
```

---

## 13. Security Architecture

> **Note:** This section provides a high-level summary. See **Volume 10: Security Architecture and Compliance** for the complete security documentation.

### 13.1 Network Segmentation

```
                    ┌──────────────────────────────┐
                    │       Internet                │
                    │            │                  │
                    │      ┌─────▼─────┐            │
                    │      │   WAF     │            │
                    │      │ (Cloudflare)           │
                    │      └─────┬─────┘            │
                    └────────────┼──────────────────┘
                                 │
                    ┌────────────▼──────────────────┐
                    │        Public Subnet            │
                    │  ┌─────────────────────────┐   │
                    │  │   Load Balancer (443)    │   │
                    │  └────────────┬────────────┘   │
                    │               │                │
                    │               ▼                │
                    │  ┌─────────────────────────┐   │
                    │  │   API Gateway (8000)     │   │
                    │  │   Frontend (3000)        │   │
                    │  └─────────────────────────┘   │
                    └────────────────────────────────┘
                                 │
                    ┌────────────▼──────────────────┐
                    │       Private Subnet            │
                    │  ┌─────────────────────────┐   │
                    │  │   Service Layer          │   │
                    │  │   (Monolith, AI, etc)    │   │
                    │  └─────────────────────────┘   │
                    │               │                │
                    │               ▼                │
                    │  ┌─────────────────────────┐   │
                    │  │   Data Layer              │   │
                    │  │   (PostgreSQL, Redis,     │   │
                    │  │    Qdrant, MinIO, Rabbit) │   │
                    │  └─────────────────────────┘   │
                    └────────────────────────────────┘
```

**Network rules:**
- Public subnet: only ports 443 (HTTPS) and 80 (redirect to 443) are exposed
- Private subnet: no direct internet access; outbound via NAT gateway only
- Data layer: accepts connections only from private subnet services
- All inter-service communication is mTLS (mutual TLS) in production
- VPC flow logs enabled for network audit trail

### 13.2 API Security

| Measure | Implementation | Configuration |
|---------|---------------|---------------|
| **Rate Limiting** | Sliding window via Redis | 100 req/s per user (standard), 1000 req/s (Enterprise) |
| **Input Validation** | Pydantic (backend) + Zod (frontend) | Schema-based validation with reject-unknown |
| **CORS** | Allowlisted origins | `*.amc.io`, enterprise custom domains |
| **CSP** | Content Security Policy headers | `script-src 'self' 'strict-dynamic'` |
| **JWT** | RS256 signed access tokens | 15min TTL access, 7-day refresh with rotation |
| **API Keys** | Pre-generated keys for automation | Scoped to specific modules, IP-restrictable |
| **SQL Injection** | Parameterized queries + ORM | Never raw SQL in application code |
| **Content Type** | Strict content-type enforcement | Reject requests without valid `Content-Type` |

### 13.3 Data Encryption

| State | Encryption Method | Key Management |
|-------|------------------|---------------|
| **In-transit (external)** | TLS 1.3 | Let's Encrypt / AWS Certificate Manager |
| **In-transit (internal)** | mTLS | Internal CA + short-lived certificates (30-day rotation) |
| **At-rest (database)** | TDE (Transparent Data Encryption) or AES-256 | AWS KMS / HashiCorp Vault |
| **At-rest (object storage)** | Server-side encryption (SSE-S3) | MinIO KMS / Vault |
| **At-rest (backups)** | GPG + AES-256 | Vault-encrypted backup keys |
| **At-rest (secrets)** | Vault encrypted | Shamir seals (5-of-7 key shares) |
| **At-rest (AI models)** | NVIDIA NIM encrypted inference | Hardware TPM / GPU TEE |

### 13.4 Secrets Management

AMC uses **HashiCorp Vault** for secrets management in production, with environment variable fallback for development.

```python
# lib/secrets.py
class SecretsManager:
    """Abstract secrets access — Vault in prod, env vars in dev."""

    def __init__(self):
        if os.getenv("ENVIRONMENT") == "production":
            self._backend = VaultBackend(
                addr=os.getenv("VAULT_ADDR"),
                token=os.getenv("VAULT_TOKEN"),
            )
        else:
            self._backend = EnvBackend()

    async def get(self, path: str, key: str) -> str:
        return await self._backend.get(path, key)

    async def get_database_url(self) -> str:
        return await self.get("database", "primary_url")

    async def get_redis_url(self) -> str:
        return await self.get("redis", "cache_url")

    async def get_api_key(self, service: str) -> str:
        return await self.get("api-keys", service)
```

**Vault policy structure:**

```hcl
# policies/amc-app.hcl
path "secret/data/database/*" {
  capabilities = ["read"]
}
path "secret/data/api-keys/*" {
  capabilities = ["read"]
}
path "secret/data/redis/*" {
  capabilities = ["read"]
}
path "secret/metadata/*" {
  capabilities = ["list"]
}
```

---

## 14. Technology Rationale

### 14.1 Decision Framework

Every technology choice in AMC was evaluated against five criteria:

1. **Fit for purpose** — Does it solve the actual problem?
2. **Operational complexity** — Can a small team (3–5 engineers) operate it?
3. **Ecosystem maturity** — Is the community, documentation, and library support strong?
4. **Cost profile** — Is the licensing, infrastructure, and team cost justified?
5. **Future-proofing** — Does it scale to Year 5 goals or need replacement?

### 14.2 Technology Choices

#### Frontend Framework: Next.js 14 (App Router)

| Criteria | Next.js 14 | Remix | SPA (React + Vite) |
|----------|-----------|-------|-------------------|
| **Server rendering** | ✅ RSC (React Server Components) | ✅ Loader functions | ❌ Client-only |
| **SEO** | ✅ Excellent | ✅ Excellent | ❌ Requires SSR wrapper |
| **PWA support** | ✅ Native + Service Worker API | ✅ | ✅ (via additional tooling) |
| **Data fetching** | ✅ Server Components + RSC | ✅ Loaders + actions | ❌ Client-only fetching |
| **Learning curve** | Medium | Medium | Low |
| **Bundle size** | ✅ Small (only client JS sent) | ✅ Small | ❌ Large |
| **Streaming** | ✅ Built-in Suspense streaming | ⚠️ Deferred loading | ❌ |

**Why Next.js 14:** Server Components dramatically reduce client-side JavaScript, critical for a complex SPA-like marketing tool where pages have massive data tables and analytics charts. Streaming enables progressive rendering of campaign analytics without blocking the UI. The App Router's nested layouts map naturally to AMC's workspace/dashboard structure. Remix is a strong alternative but lacks the same level of RSC optimization and has a smaller plugin ecosystem.

#### Backend Framework: FastAPI

| Criteria | FastAPI | Django | NestJS |
|----------|---------|--------|--------|
| **Async-native** | ✅ Native (asyncio) | ⚠️ Django 4.0+ async support is partial | ✅ Native (Node.js) |
| **API documentation** | ✅ Automatic OpenAPI + Swagger UI + ReDoc | ⚠️ DRF + drf-yasg (adds complexity) | ⚠️ Requires decorators/plugins |
| **Performance** | ✅ Very high (Starlette/Uvicorn) | ⚠️ Lower (WSGI, async is newer) | ✅ High (Node.js) |
| **Type validation** | ✅ Pydantic (excellent) | ⚠️ DRF serializers (less type-safe) | ✅ class-validator |
| **GraphQL integration** | ✅ Strawberry (native integration) | ⚠️ Graphene (less maintainable) | ✅ Apollo / TypeGraphQL |
| **Python ecosystem** | ✅ AI/ML libraries, Redis, DB drivers | ✅ Largest ecosystem | ❌ Different language |
| **Team expertise** | ✅ Python specialists | ✅ Python specialists | ❌ Would require JS/TS team |

**Why FastAPI:** Python is non-negotiable for the AI layer (Hermes, NVIDIA NIM, LangChain ecosystem). FastAPI allows sharing types and schemas between the AI layer and the API gateway. Django's async support, while improving, is not battle-tested enough for a system where every single endpoint is async. FastAPI's Pydantic integration means API schemas, database models (SQLModel), and AI tool schemas can share the same type system.

#### Database: PostgreSQL

| Criteria | PostgreSQL | CockroachDB | MySQL 8 |
|----------|-----------|-------------|---------|
| **Multi-tenancy (RLS)** | ✅ Excellent RLS support | ⚠️ Limited RLS | ❌ No RLS |
| **JSON support** | ✅ Excellent (JSONB, indexes, operators) | ✅ Good | ⚠️ Basic |
| **Partitioning** | ✅ Declarative partitioning | ✅ Automatic (by design) | ✅ Range partitioning |
| **Connection pooling** | ✅ PgBouncer (mature) | ⚠️ Pgbouncer works but less documented | ✅ ProxySQL |
| **Replication** | ✅ Streaming replication | ✅ Built-in (CockroachDB is distributed) | ✅ Group replication |
| **Ecosystem** | ✅ Largest open-source DB ecosystem | ⚠️ Smaller community | ✅ Very large |
| **Operational maturity** | ✅ Very high (everyone knows how to run it) | ⚠️ Newer, specialized skills needed | ✅ Very high |

**Why PostgreSQL:** RLS is the cornerstone of AMC's tenant isolation. PostgreSQL's RLS is the most mature implementation in any open-source database. CockroachDB's automatic sharding is appealing but RLS support is limited, and the operational knowledge is less common. For Year 1–3 scale, a well-tuned PostgreSQL primary + replicas is sufficient and far more manageable than a distributed SQL database.

#### Vector Database: Qdrant

| Criteria | Qdrant | Pinecone | Weaviate |
|----------|--------|----------|----------|
| **Self-hostable** | ✅ Yes (Docker, K8s) | ❌ Managed only | ✅ Yes |
| **Open source** | ✅ Apache 2.0 | ❌ Proprietary | ✅ BSD-3-Clause |
| **Performance** | ✅ Very high (Rust) | ✅ High | ✅ Moderate |
| **Multi-tenancy** | ✅ Collection per tenant | ⚠️ Namespace per tenant (limits) | ✅ Class per tenant |
| **Filtering** | ✅ Rich filtering (nested, geo, etc.) | ✅ Good | ✅ Good |
| **GRPC support** | ✅ Yes | ❌ REST only | ✅ Yes |
| **Pricing** | ✅ Free (self-hosted) | ❌ $70+/mo minimum | ✅ Free (self-hosted) |
| **Payload size** | ✅ Large payload storage | ❌ Limited | ✅ Good |

**Why Qdrant:** Self-hosted vector search avoids per-vector API costs that would scale linearly with AMC's AI memory usage. At 100K+ tenants with thousands of memory entries each, Pinecone would cost more than the entire AI inference budget. Qdrant's Rust implementation provides excellent performance, and the collection-per-tenant model maps perfectly to AMC's isolation requirements.

#### Message Broker: RabbitMQ

| Criteria | RabbitMQ | Apache Kafka | Redis Streams |
|----------|----------|-------------|---------------|
| **Message routing** | ✅ Rich (topic, fanout, direct, headers) | ⚠️ Topic-only (less flexible) | ⚠️ Simple consumer groups |
| **Durability** | ✅ Persistent messages to disk | ✅ Very high (log-based) | ⚠️ Limited (memory-heavy) |
| **Throughput** | ✅ High (50K msg/s per node) | ✅ Very high (1M+ msg/s) | ✅ High (100K msg/s) |
| **Operational simplicity** | ✅ Simple cluster (3 nodes) | ❌ Complex (ZooKeeper/KRaft, rebalancing) | ✅ Very simple |
| **Dead letter** | ✅ Built-in DLX | ⚠️ Requires custom config | ❌ Manual implementation |
| **Retry** | ✅ TTL + DLX retry pattern | ⚠️ Requires custom retry topics | ❌ Manual |
| **Monitoring** | ✅ Excellent (management UI, Prometheus) | ✅ Good | ⚠️ Basic |
| **Message TTL** | ✅ Per-queue, per-message | ⚠️ Topic-level only | ✅ Per-key TTL |

**Why RabbitMQ:** Kafka's log-based architecture is overengineered for AMC's event-driven needs. Most events in AMC are domain events that need routing (topic exchange), dead-lettering, and retry — all first-class features in RabbitMQ. Redis Streams would work for simple use cases but lacks dead-letter queues, message TTL, and rich routing. RabbitMQ's management UI is invaluable for debugging workflow failures. If AMC reaches a scale where event throughput exceeds 50K msg/s, a Kafka migration can be evaluated, but that's a Year 3+ concern.

#### AI Inference: NVIDIA NIM

| Criteria | NVIDIA NIM | OpenAI API | Self-hosted (vLLM/TGI) |
|----------|-----------|------------|----------------------|
| **Latency** | ✅ Low (optimized Triton server) | ⚠️ Variable (shared infra) | ✅ Low (local) |
| **Data privacy** | ✅ Self-hosted, data never leaves | ❌ Data sent to OpenAI | ✅ Full control |
| **Cost at scale** | ✅ Lower at volume (GPU capex) | ❌ Higher at scale (per-token) | ✅ Lowest (own GPUs) |
| **Model choice** | ✅ Llama, Mistral, Nemotron | ❌ GPT-4 only | ✅ Any HuggingFace model |
| **Compliance** | ✅ Data residency controlled | ❌ US-bound unless Azure | ✅ Full control |
| **Setup complexity** | ⚠️ Medium (Docker containers) | ✅ Zero (API key only) | ⚠️ Higher (GPU cluster) |

**Why NVIDIA NIM:** AMC launches with NVIDIA DGX Cloud / NIM for inference. This provides the performance of self-hosted GPU inference with the privacy of on-premise deployment. The OpenAI-compatible API means fallback to OpenAI is trivial. NIM's model support (Llama 3, Mistral, Nemotron) gives flexibility to choose the right model for each task. As AMC scales, GPU capex becomes cheaper than per-token API costs.

#### Workflow Engine: n8n

| Criteria | n8n | Zapier/Make | Temporal |
|----------|-----|-------------|----------|
| **Self-hostable** | ✅ Yes | ❌ SaaS only | ✅ Yes |
| **Open source** | ✅ Fair-code (source available) | ❌ Proprietary | ✅ MIT |
| **Visual editor** | ✅ Excellent | ✅ Excellent | ❌ Code-based |
| **Custom nodes** | ✅ Node SDK | ⚠️ Limited (platform-dependent) | ❌ Custom workflow code |
| **AI integration** | ✅ HTTP nodes + custom AMC node | ✅ API-based | ✅ Via code |
| **Scalability** | ✅ Worker mode (scale horizontally) | ⚠️ SaaS limits | ✅ Very high |
| **Pricing** | ✅ Free (self-hosted) | ❌ $20+/mo, per-task pricing | ✅ Free (self-hosted) |

**Why n8n:** The combination of a visual workflow builder (accessible to non-developer marketers) + custom node SDK (for deep AMC integration) is unique to n8n. Zapier/Make are SaaS-only and cost-per-task would be prohibitive at AMC's scale. Temporal is excellent for engineering workflows but requires developers to write code — it cannot serve AMC's goal of empowering marketing users to build their own automations. n8n's queue-based worker mode allows horizontal scaling of workflow execution independently of the AMC application.

#### Container Orchestration: Docker Swarm (initial), Kubernetes (future)

| Criteria | Docker Swarm | Kubernetes | Nomad |
|----------|-------------|------------|-------|
| **Setup complexity** | ✅ Very low (built into Docker) | ❌ High (control plane, CNI, CSI) | ⚠️ Medium |
| **Learning curve** | ✅ Low | ❌ High | ⚠️ Medium |
| **Auto-scaling** | ❌ Manual | ✅ HPA/VPA, cluster autoscaler | ✅ Autoscaling |
| **Service discovery** | ✅ Built-in DNS | ✅ CoreDNS | ✅ Consul integration |
| **Stateful workloads** | ⚠️ Basic | ✅ StatefulSets, CSI | ✅ Nomad + Consul |
| **Ecosystem** | ⚠️ Declining | ✅ Dominant | ⚠️ Smaller |
| **Migration to K8s** | ✅ Easy (same compose format) | ✅ Target state | ⚠️ Different config format |

**Why Swarm first:** For a team of 3–5 engineers in Year 1, Docker Swarm's simplicity is a force multiplier. It uses the same `docker-compose.yml` format as development, has zero additional control plane overhead, and provides built-in load balancing and DNS resolution. Kubernetes is the long-term target (Year 2–3) when the team grows, auto-scaling becomes critical, and stateful workloads (Qdrant, PostgreSQL) need better orchestration.

### 14.3 Key Decision Summary

| Decision | Choice | Runner-up | Key Factor |
|----------|--------|-----------|------------|
| Frontend framework | **Next.js 14** | Remix | Server Components, streaming, PWA support |
| Backend framework | **FastAPI** | Django | Async-native, Pydantic integration, AI layer synergy |
| API style | **REST + GraphQL** | GraphQL-only | Universal compatibility (REST) + flexible queries (GraphQL) |
| Database | **PostgreSQL** | CockroachDB | RLS for multi-tenancy, operational maturity |
| Message broker | **RabbitMQ** | Redis Streams | Dead letter, retry, rich routing |
| Vector database | **Qdrant** | Pinecone | Self-hosted, cost at scale, collection-per-tenant |
| Object storage | **MinIO** | AWS S3 | Self-hosted, S3-compatible, no vendor lock-in |
| AI inference | **NVIDIA NIM** | OpenAI API | Data privacy, cost at scale, model flexibility |
| Workflow engine | **n8n** | Temporal | Visual editor for non-developers, custom nodes |
| Container orchestration | **Docker Swarm (v1)** | Kubernetes | Simplicity for small team, easy K8s migration path |
| Observability | **Grafana + Prometheus + Loki + Tempo** | Datadog | Self-hosted, cost-effective at scale, full control |
| Feature flags | **Unleash** | LaunchDarkly | Self-hosted, cost-effective, good API |
| Secrets management | **HashiCorp Vault** | AWS Secrets Manager | Multi-cloud, self-hosted, mature policies |

---

## Appendix A: Architecture Decision Records (ADRs)

### ADR-001: Hybrid Modular Monolith + Microservices

**Status:** Accepted  
**Context:** AMC needs to ship quickly with a small team while maintaining the ability to scale specific services independently.  
**Decision:** Start with a modular monolith for core business logic (CRM, Marketing, Projects, Knowledge) with clear bounded contexts. Extract services that have different scaling profiles (AI, Media, Auth, Billing, Notifications) as standalone microservices.  
**Consequences:** Monolith modules must be built with service interfaces (Python Protocols) so extraction is trivial. The team must maintain module boundaries rigorously to prevent the monolith from becoming a big ball of mud.

### ADR-002: RLS-First Multi-Tenancy

**Status:** Accepted  
**Context:** Tenant data isolation is the #1 security requirement. Application-level filtering is error-prone.  
**Decision:** Use PostgreSQL Row-Level Security as the primary isolation mechanism. Every tenant-scoped table has a `tenant_id` column with an RLS policy that automatically scopes queries. Application code never filters by `tenant_id` manually.  
**Consequences:** All database connections must set `app.current_tenant_id` before queries. Bulk operations and background jobs must be careful to set context correctly. Admin service bypasses RLS via a separate policy role.

### ADR-003: RabbitMQ over Kafka

**Status:** Accepted  
**Context:** AMC needs event-driven communication between services with reliable delivery, dead-lettering, and retry.  
**Decision:** Use RabbitMQ for the event bus. Kafka's log-based architecture is more complex than needed for AMC's throughput (est. < 10K events/s in Year 1, < 50K events/s in Year 3).  
**Consequences:** If event throughput exceeds RabbitMQ's capabilities, a migration to Kafka would be needed. RabbitMQ's clustering is straightforward (3-node HA), and the management UI is excellent for debugging.

### ADR-004: Self-Hosted AI Inference (NVIDIA NIM)

**Status:** Accepted  
**Context:** AI inference is the fastest-growing cost center. Sending all data to OpenAI raises privacy concerns and creates vendor lock-in.  
**Decision:** Use self-hosted NVIDIA NIM on DGX Cloud / dedicated GPU infrastructure. OpenAI API is maintained as a fallback provider.  
**Consequences:** Initial GPU capex is higher than pure OpenAI usage, but break-even is estimated at ~500K inference calls/month. AMC is projected to pass this threshold in Month 4 after GA. Multi-provider abstraction ensures OpenAI fallback is always available.

### ADR-005: Qdrant for Vector Storage

**Status:** Accepted  
**Context:** AI agents need long-term memory with semantic search. Vector storage costs could balloon with per-query pricing.  
**Decision:** Self-host Qdrant with collection-per-tenant isolation. Each workspace gets its own Qdrant collection for AI memory and knowledge base vectors.  
**Consequences:** Qdrant cluster sizing must account for vector RAM usage (est. 1GB per 1M vectors at 3072 dimensions). Collections are created/destroyed on tenant provisioning/deletion.

---

## Appendix B: System Requirements & Constraints

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API P50 latency | < 100ms | Request tracing |
| API P99 latency | < 500ms | Request tracing |
| AI inference P50 | < 2s | Provider metrics |
| Campaign dispatch (10K contacts) | < 30s | End-to-end timing |
| Search (10M contacts) | < 200ms | Database query timing |
| Vector search (1M vectors) | < 100ms | Qdrant timing |
| Page load (first paint) | < 1.5s | Lighthouse |
| Page load (interactive) | < 3s | Lighthouse |

### Scalability Targets

| Dimension | Year 1 Target | Year 3 Target | Year 5 Target |
|-----------|--------------|--------------|--------------|
| Tenants | 500 | 8,000 | 35,000 |
| Users | 1,500 | 40,000 | 200,000 |
| Contacts | 5M | 200M | 1B |
| Campaigns/month | 10K | 500K | 2.5M |
| AI inferences/day | 50K | 5M | 25M |
| Storage (objects) | 50TB | 500TB | 2PB |

### Availability Constraints

| Environment | Uptime Target | Maintenance Window | Support Response |
|-------------|---------------|-------------------|------------------|
| Production | 99.9% (8.76h downtime/yr) | Sunday 02:00–04:00 UTC | 15min critical, 1hr high |
| Staging | 99% (87.6h downtime/yr) | Any time | Best effort |
| Development | Best effort | Any time | None |

---

> **End of Volume 4: System Architecture**
>
> Next → **Volume 5: Database Design (ERD, Schemas, Migrations)**
>
> *This document is a living artifact. Architecture decisions should be updated as the system evolves. All significant changes require an Architecture Decision Record (ADR).*
