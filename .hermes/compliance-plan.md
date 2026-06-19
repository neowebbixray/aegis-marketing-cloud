# Documentation Compliance Audit & Execution Plan
# Identified gaps between docs/ and current codebase

## CRITICAL (blocks core functionality)
1. JWT: RS256 (asymmetric) required — current likely HS256
2. Response envelope: `{data, meta, links}` + RFC 7807 errors required — current flat
3. GraphQL (Strawberry) missing — architecture requires dual REST+GraphQL
4. PII column encryption (pgcrypto) not implemented

## MAJOR (architecture compliance)
5. Frontend Atomic Design structure (atoms/molecules/organisms/templates)
6. Missing modules: SEO, Social, Analytics, Knowledge Base, Notifications, Marketplace
7. PWA support missing (service worker, manifest, offline)
8. State management: React Query + Zustand hybrid required
9. PostgreSQL RLS policies not deployed
10. Audit history trigger tables not implemented

## MEDIUM
11. Test factories (factory_boy + Faker) not built
12. Webhook infrastructure missing
13. Settings UI only covers 3 modules, docs specify 16+

# Execution Order (highest impact first)
Phase 1: Auth/Api compliance (JWT RS256, response envelope, GraphQL)
Phase 2: Database compliance (RLS, PII encryption, audit tables)
Phase 3: Frontend compliance (Atomic Design, React Query, PWA)
Phase 4: Missing module stubs (SEO, Social, Analytics, KB, Notifications)
Phase 5: Testing infrastructure (factories, CI alignment)
