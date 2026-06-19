# Volume 7: Frontend UI/UX Design System

## Aegis Marketing Cloud (AMC)

> **Document Version:** 1.0  
> **Classification:** Internal — Engineering & Design  
> **Date:** June 2026  
> **Authors:** Design Systems Team & Frontend Engineering  
> **Status:** ✅ Complete  
> **Volume:** 7 of 15

---

## Table of Contents

1. [Design Philosophy & Principles](#1-design-philosophy--principles)
2. [Design Tokens](#2-design-tokens)
3. [Component Library](#3-component-library)
4. [Layout System](#4-layout-system)
5. [Page Patterns](#5-page-patterns)
6. [Navigation & Information Architecture](#6-navigation--information-architecture)
7. [Data Display & Visualization](#7-data-display--visualization)
8. [AI Agent UI Patterns](#8-ai-agent-ui-patterns)
9. [Form Patterns](#9-form-patterns)
10. [State & Data Loading](#10-state--data-loading)
11. [AI-Powered UX Patterns](#11-ai-powered-ux-patterns)
12. [Workspace & Multi-tenant UI](#12-workspace--multi-tenant-ui)
13. [PWA & Offline Features](#13-pwa--offline-features)
14. [Theming & White-label](#14-theming--white-label)
15. [Accessibility Checklist](#15-accessibility-checklist)
16. [Performance Guidelines](#16-performance-guidelines)
17. [Visual Mockups (Text-Based)](#17-visual-mockups-text-based)

---

## 1. Design Philosophy & Principles

### 1.1 Atomic Design Methodology

AMC's design system is built on **Atomic Design** (Brad Frost, 2016), providing a hierarchical, composable architecture that scales from the smallest UI atoms to complete page templates.

```
┌─────────────────────────────────────────────────────────────────┐
│                     ATOMIC DESIGN HIERARCHY                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ATOMS         MOLECULES       ORGANISMS      TEMPLATES       │
│   ┌─────┐      ┌─────────┐     ┌──────────┐    ┌───────────┐   │
│   │Button│      │ Search  │     │ DataTable│    │ Dashboard  │   │
│   │Input │──►  │  Bar    │──► │  + Filter │──►│  Template  │   │
│   │Label │      │ (Input +│     │  Bar     │    │           │   │
│   │Icon  │      │  Button)│     │          │    │           │   │
│   └─────┘      └─────────┘     └──────────┘    └───────────┘   │
│                                                                 │
│   Colors    Form Group      Card Grid         List/Detail Page  │
│   Typography  + Label    + Pagination           Template        │
│   Spacing     + Error    + Export Menu           Layout         │
│   Shadows                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation layers:**

| Layer | Definition | AMC Examples |
|-------|-----------|--------------|
| **Atoms** | Smallest indivisible UI elements | `Button`, `Input`, `Badge`, `Avatar`, `Icon` |
| **Molecules** | Groups of atoms working together | `SearchBar`, `FormField`, `CardHeader`, `Tabs` |
| **Organisms** | Complex UI sections composed of molecules/atoms | `DataTable`, `SidebarNav`, `CampaignCard`, `AgentChat` |
| **Templates** | Page-level layouts with content placeholders | `DashboardTemplate`, `ListPageTemplate`, `SettingsTemplate` |
| **Pages** | Specific instances of templates with real content | `/dashboard`, `/campaigns/123`, `/settings/team` |

**File structure:**

```
src/
  components/
    ui/                  # Atoms — shadcn/ui base components
      button.tsx
      input.tsx
      badge.tsx
      ...
    forms/               # Molecules — form-specific compositions
      form-field.tsx
      search-bar.tsx
      multi-step.tsx
    data-display/        # Molecules & Organisms
      data-table.tsx
      stat-card.tsx
      timeline.tsx
    layout/              # Organisms — layout components
      app-shell.tsx
      sidebar.tsx
      topbar.tsx
    pages/               # Templates — page-level compositions
      dashboard-page.tsx
      campaign-builder-page.tsx
      agent-chat-page.tsx
```

### 1.2 Accessibility (WCAG 2.1 AA Minimum)

All AMC interfaces **must** comply with WCAG 2.1 Level AA as a minimum standard. WCAG 2.2 AAA compliance is targeted for critical paths (authentication, checkout, form submissions).

**Core requirements:**

| Criteria | WCAG Ref | Target | Verification |
|----------|---------|--------|-------------|
| Color contrast (normal text) | 1.4.3 | 4.5:1 | axe DevTools, Contrast Ratio checker |
| Color contrast (large text) | 1.4.3 | 3:1 | Automated audit in CI |
| Non-text contrast (UI components) | 1.4.11 | 3:1 | Visual regression testing |
| Keyboard navigation | 2.1.1 | All interactive elements reachable via Tab | Manual audit per sprint |
| Focus indicators | 2.4.7 | 2px outline, 3:1 contrast vs background | Automated check |
| Screen reader labels | 4.1.2 | All controls have accessible name | axe-core in CI |
| Motion/animation | 2.3.3 | Respect `prefers-reduced-motion` | CSS media query check |

**Tooling integration:**

```typescript
// next.config.js — accessibility checking in CI
const withAccessibility = process.env.CI === 'true' ? {
  experimental: {
    a11y: {
      // axe-core runs during build for every page
      // fails build on critical violations
      axeCoreOptions: {
        runOnly: ['wcag2a', 'wcag2aa', 'wcag21aa'],
      },
    },
  },
} : {};

module.exports = {
  ...withAccessibility,
};
```

### 1.3 Responsive Design (Mobile-First)

AMC uses a **mobile-first** responsive approach. All layouts start at the smallest viewport and progressively enhance upward.

**Breakpoint strategy:**

```typescript
// tailwind.config.ts
export const breakpoints = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Tablet landscape / small desktop
  xl: '1280px',  // Desktop
  '2xl': '1536px', // Large desktop
};

// Usage in components:
// <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
```

**Responsive behaviors by component type:**

| Component | Mobile (<640px) | Tablet (640-1024px) | Desktop (1024px+) |
|-----------|----------------|--------------------|--------------------|
| Sidebar | Hidden (hamburger overlay) | Collapsed icons-only | Full expanded |
| Topbar | Compact (icons only) | Icons + labels | Full with search |
| DataTable | Card list view | Table (horizontal scroll) | Full table |
| Forms | Single column | Single column | Multi-column |
| Modals | Full screen bottom sheet | Centered modal | Centered modal |
| Cards | Full width | 2 columns | 3-4 columns |

### 1.4 Performance (Core Web Vitals Targets)

AMC targets **P95 performance** across all Core Web Vitals (CWV) for the **aggregate user base**:

| Metric | Target | Measurement Tool |
|--------|--------|-----------------|
| **LCP** (Largest Contentful Paint) | < 2.5s | Lighthouse, CrUX, Web Vitals library |
| **FID** (First Input Delay) | < 100ms | CrUX, web-vitals JS |
| **INP** (Interaction to Next Paint) | < 200ms | CrUX, web-vitals JS |
| **CLS** (Cumulative Layout Shift) | < 0.1 | Lighthouse, CrUX |
| **TTFB** (Time to First Byte) | < 800ms | Performance API, Lighthouse |
| **First Contentful Paint** | < 1.8s | Web Vitals library |

**Performance budgets per route:**

| Route | JS Bundle | CSS | Images | Lighthouse Score |
|-------|-----------|-----|--------|-----------------|
| Login/Register | < 80KB | < 20KB | < 50KB | ≥ 95 |
| Dashboard | < 150KB | < 30KB | < 200KB | ≥ 90 |
| Campaign Builder | < 200KB | < 40KB | < 300KB | ≥ 85 |
| AI Chat | < 120KB | < 20KB | < 100KB | ≥ 90 |
| Analytics | < 250KB | < 50KB | < 500KB | ≥ 80 |
| Settings | < 100KB | < 30KB | < 50KB | ≥ 95 |
| Marketplace | < 180KB | < 30KB | < 400KB | ≥ 85 |
| CRM List | < 160KB | < 20KB | < 100KB | ≥ 90 |

### 1.5 Consistency (Single Source of Truth)

All visual properties are governed by **Design Tokens** — platform-agnostic variables that feed every output (CSS, Figma, Storybook, code generation).

```
┌─────────────────────────────────────────────────────────────┐
│                 DESIGN TOKEN PIPELINE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Figma ──► Token Studio ──► JSON ──► Style Dictionary ──►  │
│                                     │    CSS Variables       │
│                                     │    Tailwind Config     │
│                                     │    JS/TS Constants     │
│                                     │    SCSS Variables      │
│                                                             │
│  Every change in Figma → auto-generated tokens → all        │
│  implementations update simultaneously via CI/CD.           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Token types:**

| Category | Token Prefix | Example |
|----------|-------------|---------|
| Color | `color-` | `color-primary-500` |
| Typography | `font-` / `text-` | `font-size-xl`, `text-weight-semibold` |
| Spacing | `spacing-` | `spacing-4` (16px) |
| Border radius | `radius-` | `radius-lg` |
| Shadow | `shadow-` | `shadow-lg` |
| Z-index | `z-` | `z-modal` |
| Animation | `ease-` / `duration-` | `ease-out`, `duration-300` |
| Breakpoint | `breakpoint-` | `breakpoint-lg` |

---

## 2. Design Tokens

### 2.1 Color Palette

AMC uses a **functional color system** with named roles rather than raw hex values. All colors exist in 11-step scales (50–950) for maximum flexibility.

#### 2.1.1 Brand Colors

```css
/* Primary — AMC Brand Blue */
--color-primary-50: #EFF6FF;
--color-primary-100: #DBEAFE;
--color-primary-200: #BFDBFE;
--color-primary-300: #93C5FD;
--color-primary-400: #60A5FA;
--color-primary-500: #3B82F6;  /* Main brand color */
--color-primary-600: #2563EB;
--color-primary-700: #1D4ED8;
--color-primary-800: #1E40AF;
--color-primary-900: #1E3A8A;
--color-primary-950: #172554;

/* Secondary — Teal/Emphasis */
--color-secondary-50: #F0FDFA;
--color-secondary-100: #CCFBF1;
--color-secondary-200: #99F6E4;
--color-secondary-300: #5EEAD4;
--color-secondary-400: #2DD4BF;
--color-secondary-500: #14B8A6;
--color-secondary-600: #0D9488;
--color-secondary-700: #0F766E;
--color-secondary-800: #115E59;
--color-secondary-900: #134E4A;
--color-secondary-950: #042F2E;

/* Accent — Purple/Highlight */
--color-accent-50: #FAF5FF;
--color-accent-100: #F3E8FF;
--color-accent-200: #E9D5FF;
--color-accent-300: #D8B4FE;
--color-accent-400: #C084FC;
--color-accent-500: #A855F7;
--color-accent-600: #9333EA;
--color-accent-700: #7E22CE;
--color-accent-800: #6B21A8;
--color-accent-900: #581C87;
--color-accent-950: #3B0764;
```

#### 2.1.2 Neutral / Gray Scale

```css
--color-neutral-50:  #FAFAFA;
--color-neutral-100: #F5F5F5;
--color-neutral-200: #E5E5E5;
--color-neutral-300: #D4D4D4;
--color-neutral-400: #A3A3A3;
--color-neutral-500: #737373;
--color-neutral-600: #525252;
--color-neutral-700: #404040;
--color-neutral-800: #262626;
--color-neutral-900: #171717;
--color-neutral-950: #0A0A0A;
```

#### 2.1.3 Semantic Colors

```css
/* Success — Green */
--color-success-50:  #F0FDF4;
--color-success-100: #DCFCE7;
--color-success-200: #BBF7D0;
--color-success-300: #86EFAC;
--color-success-400: #4ADE80;
--color-success-500: #22C55E;
--color-success-600: #16A34A;
--color-success-700: #15803D;
--color-success-800: #166534;
--color-success-900: #14532D;
--color-success-950: #052E16;

/* Warning — Amber */
--color-warning-50:  #FFFBEB;
--color-warning-100: #FEF3C7;
--color-warning-200: #FDE68A;
--color-warning-300: #FCD34D;
--color-warning-400: #FBBF24;
--color-warning-500: #F59E0B;
--color-warning-600: #D97706;
--color-warning-700: #B45309;
--color-warning-800: #92400E;
--color-warning-900: #78350F;
--color-warning-950: #451A03;

/* Error — Red */
--color-error-50:  #FEF2F2;
--color-error-100: #FEE2E2;
--color-error-200: #FECACA;
--color-error-300: #FCA5A5;
--color-error-400: #F87171;
--color-error-500: #EF4444;
--color-error-600: #DC2626;
--color-error-700: #B91C1C;
--color-error-800: #991B1B;
--color-error-900: #7F1D1D;
--color-error-950: #450A0A;

/* Info — Sky Blue */
--color-info-50:  #F0F9FF;
--color-info-100: #E0F2FE;
--color-info-200: #BAE6FD;
--color-info-300: #7DD3FC;
--color-info-400: #38BDF8;
--color-info-500: #0EA5E9;
--color-info-600: #0284C7;
--color-info-700: #0369A1;
--color-info-800: #075985;
--color-info-900: #0C4A6E;
--color-info-950: #082F49;
```

#### 2.1.4 Semantic Role Mapping

| CSS Variable | Token Name | Default (Light) | Dark Mode |
|-------------|-----------|----------------|-----------|
| `--color-bg-primary` | Background Primary | `neutral-50` | `neutral-950` |
| `--color-bg-secondary` | Background Secondary | `neutral-100` | `neutral-900` |
| `--color-bg-tertiary` | Background Tertiary | `neutral-200` | `neutral-800` |
| `--color-text-primary` | Text Primary | `neutral-900` | `neutral-50` |
| `--color-text-secondary` | Text Secondary | `neutral-500` | `neutral-400` |
| `--color-text-tertiary` | Text Tertiary | `neutral-400` | `neutral-500` |
| `--color-text-inverse` | Text Inverse | `white` | `neutral-900` |
| `--color-border` | Border Default | `neutral-200` | `neutral-700` |
| `--color-border-hover` | Border Hover | `neutral-300` | `neutral-600` |

### 2.2 Typography

#### 2.2.1 Font Family

```css
/* Primary font (UI) */
--font-family-sans: 'Inter', -apple-system, BlinkMacSystemFont,
  'Segoe UI', Roboto, sans-serif;

/* Mono font (code, data) */
--font-family-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code',
  'SF Mono', Consolas, monospace;

/* Display font (headings, marketing) */
--font-family-display: 'Inter Display', 'Inter', sans-serif;
```

#### 2.2.2 Type Scale

```css
/* Font Sizes */
--text-xs:     0.75rem;    /* 12px */
--text-sm:     0.875rem;   /* 14px */
--text-base:   1rem;       /* 16px — body text */
--text-lg:     1.125rem;   /* 18px */
--text-xl:     1.25rem;    /* 20px */
--text-2xl:    1.5rem;     /* 24px */
--text-3xl:    1.875rem;   /* 30px */
--text-4xl:    2.25rem;    /* 36px */
--text-5xl:    3rem;       /* 48px */
--text-6xl:    3.75rem;    /* 60px */
--text-7xl:    4.5rem;     /* 72px */
--text-8xl:    6rem;       /* 96px */
--text-9xl:    8rem;       /* 128px */
```

#### 2.2.3 Font Weight

```css
--font-weight-thin:       100;
--font-weight-extralight: 200;
--font-weight-light:      300;
--font-weight-normal:     400;
--font-weight-medium:     500;
--font-weight-semibold:   600;
--font-weight-bold:       700;
--font-weight-extrabold:  800;
--font-weight-black:      900;
```

#### 2.2.4 Line Height

```css
--leading-none:    1;
--leading-tight:   1.25;
--leading-snug:    1.375;
--leading-normal:  1.5;
--leading-relaxed: 1.625;
--leading-loose:   2;
```

#### 2.2.5 Typography Scale Table

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `display-2xl` | 4.5rem / 72px | Bold (700) | 1.1 | Marketing hero headlines |
| `display-xl` | 3.75rem / 60px | Bold (700) | 1.1 | Page headings, landing pages |
| `display-lg` | 3rem / 48px | Semibold (600) | 1.2 | Section headers |
| `display-md` | 2.25rem / 36px | Semibold (600) | 1.2 | Major page titles |
| `display-sm` | 1.875rem / 30px | Semibold (600) | 1.3 | Page titles |
| `display-xs` | 1.5rem / 24px | Semibold (600) | 1.3 | Card titles, modal headers |
| `text-xl` | 1.25rem / 20px | Medium (500) | 1.4 | Subheadings |
| `text-lg` | 1.125rem / 18px | Normal (400) | 1.5 | Lead paragraphs |
| `text-base` | 1rem / 16px | Normal (400) | 1.5 | Body text, inputs |
| `text-sm` | 0.875rem / 14px | Normal (400) | 1.5 | Secondary text, captions |
| `text-xs` | 0.75rem / 12px | Normal (400) | 1.5 | Labels, timestamps |
| `label-sm` | 0.875rem / 14px | Medium (500) | 1.5 | Form labels |
| `label-xs` | 0.75rem / 12px | Medium (500) | 1.5 | Small labels, badge text |
| `code-sm` | 0.875rem / 14px | Normal (400) | 1.7 | Inline code |
| `mono-xs` | 0.75rem / 12px | Normal (400) | 1.5 | Data values |

### 2.3 Spacing (4px Base Grid)

AMC uses a **4px base grid** for all spacing decisions.

```css
--spacing-0:   0px;
--spacing-px:  1px;
--spacing-0.5: 0.125rem;  /* 2px */
--spacing-1:   0.25rem;   /* 4px  */
--spacing-2:   0.5rem;    /* 8px  */
--spacing-3:   0.75rem;   /* 12px */
--spacing-4:   1rem;      /* 16px */
--spacing-5:   1.25rem;   /* 20px */
--spacing-6:   1.5rem;    /* 24px */
--spacing-7:   1.75rem;   /* 28px */
--spacing-8:   2rem;      /* 32px */
--spacing-9:   2.25rem;   /* 36px */
--spacing-10:  2.5rem;    /* 40px */
--spacing-11:  2.75rem;   /* 44px */
--spacing-12:  3rem;      /* 48px */
--spacing-14:  3.5rem;    /* 56px */
--spacing-16:  4rem;      /* 64px */
--spacing-20:  5rem;      /* 80px */
--spacing-24:  6rem;      /* 96px */
--spacing-28:  7rem;      /* 112px */
--spacing-32:  8rem;      /* 128px */
--spacing-36:  9rem;      /* 144px */
--spacing-40:  10rem;     /* 160px */
--spacing-44:  11rem;     /* 176px */
--spacing-48:  12rem;     /* 192px */
--spacing-52:  13rem;     /* 208px */
--spacing-56:  14rem;     /* 224px */
--spacing-60:  15rem;     /* 240px */
--spacing-64:  16rem;     /* 256px */
--spacing-72:  18rem;     /* 288px */
--spacing-80:  20rem;     /* 320px */
--spacing-96:  24rem;     /* 384px */
```

**Semantic spacing tokens:**

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | 4px (spacing-1) | Compact elements, icon gaps |
| `--space-sm` | 8px (spacing-2) | Tight element spacing |
| `--space-md` | 16px (spacing-4) | Default between elements |
| `--space-lg` | 24px (spacing-6) | Section spacing |
| `--space-xl` | 32px (spacing-8) | Major section spacing |
| `--space-2xl` | 48px (spacing-12) | Page-level spacing |
| `--space-3xl` | 64px (spacing-16) | Spacious layouts |

### 2.4 Border Radius

```css
--radius-none: 0px;
--radius-sm:   0.125rem;   /* 2px */
--radius-md:   0.375rem;   /* 6px */
--radius-lg:   0.5rem;     /* 8px  */
--radius-xl:   0.75rem;    /* 12px */
--radius-2xl:  1rem;       /* 16px */
--radius-3xl:  1.5rem;     /* 24px */
--radius-full: 9999px;     /* Circular/pill */
```

**Semantic radius mapping:**

| Token | Value | Components |
|-------|-------|-----------|
| `--radius-input` | `radius-md` (6px) | Input, Select, Textarea |
| `--radius-button` | `radius-lg` (8px) | Button, Badge |
| `--radius-card` | `radius-xl` (12px) | Card, Dialog, Sheet |
| `--radius-modal` | `radius-2xl` (16px) | Modals, Drawers |
| `--radius-pill` | `radius-full` | Tabs, Toggle, Switch, Avatar |

### 2.5 Shadows

```css
--shadow-sm:   0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md:   0 4px 6px -1px rgb(0 0 0 / 0.1),
               0 2px 4px -2px rgb(0 0 0 / 0.1);
--shadow-lg:   0 10px 15px -3px rgb(0 0 0 / 0.1),
               0 4px 6px -4px rgb(0 0 0 / 0.1);
--shadow-xl:   0 20px 25px -5px rgb(0 0 0 / 0.1),
               0 8px 10px -6px rgb(0 0 0 / 0.1);
--shadow-2xl:  0 25px 50px -12px rgb(0 0 0 / 0.25);
--shadow-inner: inset 0 2px 4px 0 rgb(0 0 0 / 0.05);

/* Dark mode shadows are elevated + tinted */
@media (prefers-color-scheme: dark) {
  --shadow-sm:  0 1px 2px 0 rgb(0 0 0 / 0.3);
  --shadow-md:  0 4px 6px -1px rgb(0 0 0 / 0.4);
  --shadow-lg:  0 10px 15px -3px rgb(0 0 0 / 0.4);
  --shadow-xl:  0 20px 25px -5px rgb(0 0 0 / 0.5);
  --shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.6);
}
```

**Semantic shadow usage:**

| Token | Elevation | Components |
|-------|-----------|-----------|
| `--shadow-button` | sm | Default buttons |
| `--shadow-card` | md | Cards, stat cards |
| `--shadow-dropdown` | lg | Dropdowns, popovers, tooltips |
| `--shadow-modal` | xl | Dialogs, sheets, drawers |
| `--shadow-toast` | 2xl | Toast notifications |
| `--shadow-focus-ring` | inner | Focus visible ring |

### 2.6 Z-Index Scale

```css
--z-base:      0;
--z-dropdown:  50;
--z-sticky:    100;
--z-fixed:     200;
--z-overlay:   300;
--z-modal:     400;
--z-popover:   500;
--z-tooltip:   600;
--z-toast:     700;
--z-banner:    800;
--z-loading:   900;
--z-max:       9999;
```

**Layer mapping guide:**

| Layer | Z-index | Elements |
|-------|---------|----------|
| Page content | `base` (0) | All regular layout |
| Sticky headers | `sticky` (100) | Table headers, sidebar sections |
| Fixed elements | `fixed` (200) | Sidebar, topbar |
| Dropdown menus | `dropdown` (50) | Select dropdowns, command menu |
| Popovers | `popover` (500) | Date picker, combobox |
| Modals | `modal` (400) | Dialogs, sheets |
| Tooltips | `tooltip` (600) | Tooltips |
| Toasts | `toast` (700) | Toast notifications |
| Loading overlays | `loading` (900) | Full-page spinners |
| Banners | `banner` (800) | Offline banner, maintenance |

### 2.7 Breakpoints

```typescript
// tailwind.config.ts
export const breakpoints = {
  sm:  '640px',   // @media (min-width: 640px)
  md:  '768px',   // @media (min-width: 768px)
  lg:  '1024px',  // @media (min-width: 1024px)
  xl:  '1280px',  // @media (min-width: 1280px)
  '2xl': '1536px', // @media (min-width: 1536px)
};
```

**CSS media query utilities:**

```css
/* Mobile-first pattern — always start with base styles */
.component {
  /* Mobile styles (< 640px) */
}
@media (min-width: 640px) { /* sm+ */ }
@media (min-width: 768px) { /* md+ */ }
@media (min-width: 1024px) { /* lg+ */ }
@media (min-width: 1280px) { /* xl+ */ }
@media (min-width: 1536px) { /* 2xl+ */ }
```

### 2.8 Animation Tokens

#### 2.8.1 Duration

```css
--duration-0:    0ms;
--duration-75:   75ms;
--duration-100:  100ms;
--duration-150:  150ms;
--duration-200:  200ms;
--duration-300:  300ms;
--duration-500:  500ms;
--duration-700:  700ms;
--duration-1000: 1000ms;
```

**Semantic durations:**

| Token | Value | Usage |
|-------|-------|-------|
| `--duration-instant` | 75ms | Hover states, micro-interactions |
| `--duration-fast` | 150ms | Button press, toggle switch |
| `--duration-normal` | 200ms | Default transitions |
| `--duration-slow` | 300ms | Modal open/close, sheet |
| `--duration-page` | 500ms | Page transitions, route changes |
| `--duration-enter` | 150ms | Element enter animation |
| `--duration-exit` | 100ms | Element exit animation (faster) |

#### 2.8.2 Easing

```css
--ease-linear: linear;
--ease-in:     cubic-bezier(0.4, 0, 1, 1);
--ease-out:    cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

/* Custom easings for specific effects */
--ease-enter:  cubic-bezier(0.05, 0.7, 0.1, 1);   /* Spring-like enter */
--ease-exit:   cubic-bezier(0.3, 0, 0.8, 0.15);    /* Quick exit */
--ease-bounce: cubic-bezier(0.68, -0.55, 0.27, 1.55); /* Bounce effect */
```

#### 2.8.3 Motion Preferences

```css
/* Respect user's motion preferences */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Respect user's transparency preferences */
@media (prefers-reduced-transparency: reduce) {
  *, *::before, *::after {
    opacity: 1 !important;
    background: transparent !important;
    backdrop-filter: none !important;
  }
}

/* Respect user's contrast preferences */
@media (prefers-contrast: more) {
  :root {
    --color-text-primary: #000000;
    --color-bg-primary: #FFFFFF;
    --color-border: #000000;
  }
}
```

---

## 3. Component Library

### 3.1 Architecture & Conventions

AMC's component library is built on **shadcn/ui** — copy-paste components that are owned by the application, not imported as an opaque dependency. Every component is a Tailwind CSS + Radix UI primitive composition.

**Component anatomy:**

```typescript
// components/ui/button.tsx
import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  // Base styles — applied to all variants
  'inline-flex items-center justify-center whitespace-nowrap rounded-lg ' +
  'text-sm font-medium ring-offset-background transition-colors ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ' +
  'focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-primary/90',
        destructive: 'bg-destructive text-destructive-foreground hover:bg-destructive/90',
        outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
        secondary: 'bg-secondary text-secondary-foreground hover:bg-secondary/80',
        ghost: 'hover:bg-accent hover:text-accent-foreground',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3',
        lg: 'h-11 rounded-lg px-8',
        icon: 'h-10 w-10',
        'icon-sm': 'h-8 w-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <>
            <Spinner className="mr-2 h-4 w-4 animate-spin" />
            {children}
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

### 3.2 Component Inventory

All 40+ components are documented with usage guidelines, variants, states, code examples, and accessibility notes. Below is the complete inventory.

#### 3.2.1 Button

**Usage guidelines:**
- Use for primary actions: form submissions, CTAs, dialog triggers
- Avoid using buttons for navigation — use `Link` component instead
- Use `loading` state for async actions
- Maximum one primary button per section
- Icon buttons must have accessible labels

**Variants:**

| Variant | Visual | When to use |
|---------|--------|-------------|
| `default` | Solid primary fill | Primary call-to-action |
| `secondary` | Solid neutral fill | Secondary actions, Cancel |
| `outline` | Bordered, transparent fill | Tertiary actions, "Add" buttons |
| `ghost` | No background, hover only | Toolbar actions, table row actions |
| `destructive` | Red solid fill | Delete, remove, irreversible actions |
| `link` | Text only, underlined on hover | Inline actions, "View all" links |

**Sizes:**

| Size | Height | Padding | Icon Support |
|------|--------|---------|-------------|
| `sm` | 32px (h-8) | 12px horizontal | Yes, 14px icon |
| `default` | 40px (h-10) | 16px horizontal | Yes, 16px icon |
| `lg` | 44px (h-11) | 32px horizontal | Yes, 18px icon |
| `icon` | 40px (h-10) | Square | Always |
| `icon-sm` | 32px (h-8) | Square | Always |

**States:**

| State | Visual Change |
|-------|--------------|
| Default | Normal appearance per variant |
| Hover | Background darken by 10%, cursor pointer |
| Focus (keyboard) | 2px ring offset 2px (focus-visible) |
| Active (press) | Scale 0.98, background darken 20% |
| Disabled | Opacity 50%, no pointer events |
| Loading | Spinner replaces/prefixes icon, disabled interaction |
| Error | Red border flash for 500ms on failed submission |

**Code example:**

```tsx
import { Button } from '@/components/ui/button';
import { Plus, Loader2 } from 'lucide-react';

// Default usage
<Button onClick={handleCreate}>Create Campaign</Button>

// With icon
<Button>
  <Plus className="mr-2 h-4 w-4" /> New Contact
</Button>

// Loading state
<Button loading disabled={isPending}>
  {isPending ? 'Saving...' : 'Save Changes'}
</Button>

// Destructive
<Button variant="destructive" onClick={handleDelete}>
  Delete Workspace
</Button>

// Icon button with accessible label
<Button variant="ghost" size="icon" aria-label="Edit contact">
  <Pencil className="h-4 w-4" />
</Button>

// As child component (for Link wrapping)
<Button asChild variant="link">
  <Link href="/campaigns">View all campaigns</Link>
</Button>
```

**Accessibility:**
- All buttons must have accessible name (visible text, `aria-label`, or `aria-labelledby`)
- Loading state: `aria-busy="true"` on button
- Disabled: `aria-disabled="true"` (use `disabled` prop)
- Icon-only buttons: MUST have `aria-label`

#### 3.2.2 Input

**Usage guidelines:**
- Single-line text input for short-form data
- Always pair with a visible `<Label>`
- Show helper text below for format requirements
- Error state requires both border change and error message text

**Variants:**

| Variant | Usage |
|---------|-------|
| `default` | Standard text, email, password, URL |
| `file` | File upload with custom styling |
| `search` | Search input with magnifying glass icon |

**States:**

```tsx
// Default
<Input placeholder="Enter email address" />

// Hover — CSS :hover changes border color to neutral-400

// Focus — ring-2 with primary color, offset-2

// Disabled
<Input disabled placeholder="Read only" />

// Error
<Input aria-invalid="true" />
{/* Renders with error border color + error message below */}

// With icon (left)
<div className="relative">
  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
  <Input className="pl-10" placeholder="Search..." />
</div>

// Password visibility toggle
<div className="relative">
  <Input type={showPassword ? 'text' : 'password'} />
  <Button
    variant="ghost"
    size="icon"
    className="absolute right-2 top-1/2 -translate-y-1/2"
    onClick={() => setShowPassword(!showPassword)}
    aria-label={showPassword ? 'Hide password' : 'Show password'}
  >
    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
  </Button>
</div>
```

**Accessibility:**
- Always paired with `<Label htmlFor="input-id">`
- Error message linked via `aria-describedby`
- `aria-invalid="true"` when in error state
- `aria-required="true"` when required

#### 3.2.3 Select

**Usage guidelines:**
- For selecting from 5-25 options
- For < 5 options, use Radio Group
- For > 25 options, use Command combobox with search

**Anatomy:**

```tsx
<Select onValueChange={handleChange} defaultValue="option1">
  <SelectTrigger className="w-[280px]">
    <SelectValue placeholder="Select a template..." />
  </SelectTrigger>
  <SelectContent>
    <SelectGroup>
      <SelectLabel>Email Templates</SelectLabel>
      <SelectItem value="welcome">Welcome Email</SelectItem>
      <SelectItem value="abandoned-cart">Abandoned Cart</SelectItem>
      <SelectItem value="newsletter">Newsletter</SelectItem>
    </SelectGroup>
    <SelectSeparator />
    <SelectGroup>
      <SelectLabel>Social Templates</SelectLabel>
      <SelectItem value="promo">Promotion Post</SelectItem>
      <SelectItem value="announcement">Announcement</SelectItem>
    </SelectGroup>
  </SelectContent>
</Select>
```

**States:**

| State | Visual |
|-------|--------|
| Default | Input-style border, placeholder text |
| Hover | Border darken, cursor pointer |
| Open | Trigger gets focus ring, content drops down |
| Selected | Value replaces placeholder |
| Disabled | Opacity 50%, no interaction |
| Error | Red border + error message |

**Accessibility:**
- Uses Radix's `Select` with full keyboard navigation
- Arrow keys to navigate, Enter/Space to select
- `aria-expanded` on trigger
- Screen reader announces selected value

#### 3.2.4 Checkbox

**Usage guidelines:**
- For boolean selections or multiple selections from a list
- Use standalone for "agree to terms"
- Use in groups for multi-select lists
- Indeterminate state for "select all" partial selections

```tsx
// Standalone
<div className="flex items-center space-x-2">
  <Checkbox id="terms" />
  <Label htmlFor="terms">I agree to the terms and conditions</Label>
</div>

// With form
<FormField
  control={form.control}
  name="channels"
  render={() => (
    <FormItem>
      <FormLabel>Marketing Channels</FormLabel>
      {channels.map((channel) => (
        <FormField
          key={channel.id}
          control={form.control}
          name="channels"
          render={({ field }) => (
            <FormItem className="flex items-center space-x-2">
              <FormControl>
                <Checkbox
                  checked={field.value?.includes(channel.id)}
                  onCheckedChange={(checked) => {
                    return checked
                      ? field.onChange([...field.value, channel.id])
                      : field.onChange(field.value?.filter((v) => v !== channel.id));
                  }}
                />
              </FormControl>
              <FormLabel className="font-normal">{channel.label}</FormLabel>
            </FormItem>
          )}
        />
      ))}
    </FormItem>
  )}
/>

// Indeterminate (select all)
<Checkbox
  checked={checkedItems.length === items.length}
  onCheckedChange={handleSelectAll}
  aria-checked={isIndeterminate ? 'mixed' : checkedItems.length === items.length}
/>
```

**Accessibility:**
- Uses native `role="checkbox"` via Radix
- `aria-checked` supports `true`, `false`, `mixed` (indeterminate)
- Keyboard: Space to toggle
- Requires `<Label>` for accessible name

#### 3.2.5 Radio Group

**Usage guidelines:**
- For mutually exclusive selections from 2-5 options
- For > 5 options, use Select dropdown
- Use when all options should be visible for comparison

```tsx
<RadioGroup defaultValue="email" onValueChange={handleChange}>
  <div className="space-y-2">
    <div className="flex items-center space-x-2">
      <RadioGroupItem value="email" id="email" />
      <Label htmlFor="email">Email Campaign</Label>
    </div>
    <div className="flex items-center space-x-2">
      <RadioGroupItem value="social" id="social" />
      <Label htmlFor="social">Social Media</Label>
    </div>
    <div className="flex items-center space-x-2">
      <RadioGroupItem value="both" id="both" />
      <Label htmlFor="both">Both Channels</Label>
    </div>
  </div>
</RadioGroup>
```

**Accessibility:**
- `role="radiogroup"` on container
- Arrow key navigation between options
- Screen reader announces selected option

#### 3.2.6 Switch

**Usage guidelines:**
- For binary settings toggles (on/off)
- Prefer over checkbox for "immediate effect" settings
- Use with descriptive label on left or right

```tsx
<div className="flex items-center justify-between rounded-lg border p-4">
  <div>
    <Label htmlFor="airplane-mode">AI Auto-suggestions</Label>
    <p className="text-sm text-muted-foreground">
      Allow AI to suggest campaign improvements
    </p>
  </div>
  <Switch
    id="airplane-mode"
    checked={autoSuggestions}
    onCheckedChange={setAutoSuggestions}
    aria-label="Toggle AI auto-suggestions"
  />
</div>
```

#### 3.2.7 Textarea

**Usage guidelines:**
- For multi-line text input (notes, descriptions, email body)
- Provide character count for limited fields
- Resize vertical only by default

```tsx
<div className="space-y-2">
  <Label htmlFor="description">Campaign Description</Label>
  <Textarea
    id="description"
    placeholder="Describe your campaign goals..."
    className="min-h-[120px]"
    maxLength={500}
  />
  <p className="text-xs text-muted-foreground text-right">
    {description.length}/500 characters
  </p>
</div>
```

**Accessibility:**
- Same as Input — requires Label, supports aria-invalid, aria-describedby

#### 3.2.8 Badge

**Usage guidelines:**
- For status indicators, labels, counts, tags
- Use semantic variants for different meanings
- Dismissible badges for filter chips

**Variants:**

| Variant | Example | Usage |
|---------|---------|-------|
| `default` | Default tag | Neutral metadata |
| `secondary` | Secondary tag | Subtle badge |
| `destructive` | Error | Error/blocked status |
| `outline` | Filter chip | Interactive filters |
| `success` | Active | Positive status |
| `warning` | Pending | In-progress/warning |
| `info` | Draft | Informational |

```tsx
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending Review</Badge>
<Badge variant="destructive">Paused</Badge>

// Dismissible badge (filter chip)
<Badge variant="outline" className="gap-1">
  Email Campaigns
  <X className="h-3 w-3 cursor-pointer" onClick={() => removeFilter('channel')} />
</Badge>

// Count badge (on notification bell)
<Badge variant="destructive" className="absolute -top-1 -right-1 h-4 w-4 p-0 text-[10px]">
  3
</Badge>
```

#### 3.2.9 Avatar

**Usage guidelines:**
- For user/contact/agent profile images
- Fallback to initials on missing image
- Status dot for presence indication

```tsx
// With image
<Avatar>
  <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
  <AvatarFallback>CN</AvatarFallback>
</Avatar>

// With status indicator
<div className="relative">
  <Avatar>
    <AvatarImage src="/avatars/user-1.jpg" alt="Jane Smith" />
    <AvatarFallback>JS</AvatarFallback>
  </Avatar>
  <span className="absolute bottom-0 right-0 h-3 w-3 rounded-full bg-green-500 border-2 border-white" />
</div>

// Sizes
<Avatar className="h-6 w-6" />  {/* sm */}
<Avatar className="h-10 w-10" /> {/* md (default) */}
<Avatar className="h-14 w-14" /> {/* lg */}
<Avatar className="h-20 w-20" /> {/* xl */}

// Group (stacked)
<AvatarGroup limit={3}>
  <Avatar src="/user1.jpg" />
  <Avatar src="/user2.jpg" />
  <Avatar src="/user3.jpg" />
  <Avatar src="/user4.jpg" />
  <AvatarFallback>+2</AvatarFallback>
</AvatarGroup>
```

**Accessibility:**
- AvatarImage: `alt` describes the person (not "avatar")
- AvatarFallback: initials only, no decorative role needed
- Group: `aria-label="Team members"` on container

#### 3.2.10 Card

**Usage guidelines:**
- For grouped content: metrics, summaries, data panels
- Clickable cards for navigation
- Avoid nesting cards inside cards

```tsx
<Card className="w-[380px]">
  <CardHeader>
    <CardTitle>Campaign Performance</CardTitle>
    <CardDescription>Last 30 days activity</CardDescription>
  </CardHeader>
  <CardContent>
    <div className="space-y-4">
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">Impressions</span>
        <span className="font-semibold">124,592</span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">Clicks</span>
        <span className="font-semibold">3,847</span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">CTR</span>
        <span className="font-semibold text-green-600">3.09%</span>
      </div>
    </div>
  </CardContent>
  <CardFooter>
    <Button className="w-full" variant="outline">View Full Report</Button>
  </CardFooter>
</Card>

// Clickable card
<Card
  className="cursor-pointer hover:shadow-md transition-shadow"
  onClick={() => router.push(`/campaigns/${campaign.id}`)}
  role="button"
  tabIndex={0}
  onKeyDown={(e) => e.key === 'Enter' && router.push(`/campaigns/${campaign.id}`)}
>
  {/* ... */}
</Card>
```

#### 3.2.11 Dialog

**Usage guidelines:**
- For confirmations, forms, and focused tasks that require user attention
- Use `Sheet` for side panels (non-blocking)
- Always provide a `title` for screen readers
- Close on Escape; trap focus within dialog

```tsx
<Dialog open={open} onOpenChange={setOpen}>
  <DialogTrigger asChild>
    <Button variant="outline">New Campaign</Button>
  </DialogTrigger>
  <DialogContent className="sm:max-w-[425px]">
    <DialogHeader>
      <DialogTitle>Create New Campaign</DialogTitle>
      <DialogDescription>
        Fill in the details for your new marketing campaign.
      </DialogDescription>
    </DialogHeader>
    <CampaignForm onSubmit={handleSubmit} />
    <DialogFooter>
      <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
      <Button type="submit">Create Campaign</Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

**Accessibility:**
- Focus trapped within dialog while open
- Escape closes dialog
- `aria-modal="true"`
- `aria-labelledby` points to DialogTitle
- `aria-describedby` points to DialogDescription
- Closing restores focus to trigger element

#### 3.2.12 Dropdown Menu

**Usage guidelines:**
- For contextual actions (row menus, "more" menus)
- Use `Popover` for richer content (forms, previews)
- Use `Command` menu for searchable lists

```tsx
<DropdownMenu>
  <DropdownMenuTrigger asChild>
    <Button variant="ghost" size="icon">
      <MoreHorizontal className="h-4 w-4" />
      <span className="sr-only">More options</span>
    </Button>
  </DropdownMenuTrigger>
  <DropdownMenuContent align="end" className="w-[180px]">
    <DropdownMenuLabel>Actions</DropdownMenuLabel>
    <DropdownMenuSeparator />
    <DropdownMenuItem onClick={handleEdit}>
      <Pencil className="mr-2 h-4 w-4" /> Edit
    </DropdownMenuItem>
    <DropdownMenuItem onClick={handleDuplicate}>
      <Copy className="mr-2 h-4 w-4" /> Duplicate
    </DropdownMenuItem>
    <DropdownMenuSeparator />
    <DropdownMenuItem onClick={handleDelete} className="text-destructive">
      <Trash2 className="mr-2 h-4 w-4" /> Delete
      <DropdownMenuShortcut>⌘⌫</DropdownMenuShortcut>
    </DropdownMenuItem>
  </DropdownMenuContent>
</DropdownMenu>
```

**Accessibility:**
- Full keyboard navigation (arrow keys, Enter, Escape)
- `aria-haspopup="menu"` on trigger
- Screen reader announces "submenu" on open
- Items with icons must have descriptive text

#### 3.2.13 Popover

**Usage guidelines:**
- For non-modal, lightweight content: date pickers, command menus, help text
- Use instead of tooltip when interactive content is needed
- Closes on click outside and Escape

```tsx
<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline">Open popover</Button>
  </PopoverTrigger>
  <PopoverContent className="w-80">
    <div className="grid gap-4">
      <div className="space-y-2">
        <h4 className="font-medium leading-none">Dimensions</h4>
        <p className="text-sm text-muted-foreground">
          Set the dimensions for your campaign preview.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="width">Width</Label>
          <Input id="width" defaultValue="600" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="height">Height</Label>
          <Input id="height" defaultValue="400" />
        </div>
      </div>
    </div>
  </PopoverContent>
</Popover>
```

#### 3.2.14 Tooltip

**Usage guidelines:**
- For supplementary information (not critical)
- Show on hover or focus (keyboard)
- Short text only (1-3 words)
- Use `Popover` for interactive or rich content

```tsx
<TooltipProvider>
  <Tooltip>
    <TooltipTrigger asChild>
      <Button variant="ghost" size="icon" aria-label="Campaign performance">
        <BarChart3 className="h-4 w-4" />
      </Button>
    </TooltipTrigger>
    <TooltipContent side="bottom">
      <p>View Analytics</p>
    </TooltipContent>
  </Tooltip>
</TooltipProvider>
```

**Accessibility:**
- Tooltip appears on focus AND hover
- `role="tooltip"`
- `aria-describedby` connects trigger to tooltip content
- Dismiss on Escape

#### 3.2.15 Toast (Sonner)

**Usage guidelines:**
- For transient notifications: success, error, info
- Stack multiple toasts
- Use for actions that don't require immediate response
- For blocking actions, use Dialog instead

```tsx
import { toast } from 'sonner';

// Success
toast.success('Campaign created', {
  description: 'Your campaign has been launched successfully.',
  action: {
    label: 'View',
    onClick: () => router.push('/campaigns/123'),
  },
});

// Error
toast.error('Failed to save', {
  description: 'Please check your connection and try again.',
  duration: 5000,
});

// Promise toast (loading → success/error)
toast.promise(saveCampaign(data), {
  loading: 'Saving campaign...',
  success: 'Campaign saved!',
  error: 'Failed to save campaign',
});

// Custom action toast
toast('Campaign published', {
  description: 'Your campaign is now live',
  action: {
    label: 'Undo',
    onClick: () => unpublishCampaign(id),
  },
  duration: 8000, // Longer for undoable actions
});
```

**Accessibility:**
- `role="status"` for non-critical, `role="alert"` for critical
- Screen reader announcements via `aria-live`
- Focus remains on current task (not stolen by toast)
- Action buttons accessible via keyboard

#### 3.2.16 Tabs

**Usage guidelines:**
- For switching between related content sections
- Avoid using tabs for navigation between pages (use sidebar/links)
- Use `TabsList` with `TabsTrigger` inside `Tabs`
- Content above/below tabs pattern

```tsx
<Tabs defaultValue="overview" value={activeTab} onValueChange={setActiveTab}>
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="analytics">Analytics</TabsTrigger>
    <TabsTrigger value="settings">Settings</TabsTrigger>
    <TabsTrigger value="activity" disabled>Activity (Coming Soon)</TabsTrigger>
  </TabsList>
  <TabsContent value="overview" className="space-y-4">
    <OverviewPanel campaignId={id} />
  </TabsContent>
  <TabsContent value="analytics">
    <AnalyticsPanel campaignId={id} />
  </TabsContent>
  <TabsContent value="settings">
    <SettingsPanel campaignId={id} />
  </TabsContent>
</Tabs>
```

**Accessibility:**
- `role="tablist"` on container
- `role="tab"` on each trigger
- `role="tabpanel"` on content
- `aria-controls` connects tab to panel
- Arrow key navigation between tabs
- `aria-selected` on active tab

#### 3.2.17 Table

**Usage guidelines:**
- For structured data display
- Use `DataTable` (not basic Table) when sorting/filtering/actions needed
- Responsive: show as cards on mobile

```tsx
<Table>
  <TableCaption>A list of your recent campaigns.</TableCaption>
  <TableHeader>
    <TableRow>
      <TableHead className="w-[100px]">Name</TableHead>
      <TableHead>Status</TableHead>
      <TableHead>Channel</TableHead>
      <TableHead className="text-right">Impressions</TableHead>
      <TableHead className="text-right">Actions</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {campaigns.map((campaign) => (
      <TableRow key={campaign.id}>
        <TableCell className="font-medium">{campaign.name}</TableCell>
        <TableCell>
          <Badge variant={getStatusVariant(campaign.status)}>
            {campaign.status}
          </Badge>
        </TableCell>
        <TableCell>{campaign.channel}</TableCell>
        <TableCell className="text-right">{campaign.impressions.toLocaleString()}</TableCell>
        <TableCell className="text-right">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem>Edit</DropdownMenuItem>
              <DropdownMenuItem>Duplicate</DropdownMenuItem>
              <DropdownMenuItem className="text-destructive">Delete</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
  <TableFooter>
    <TableRow>
      <TableCell colSpan={3}>Total</TableCell>
      <TableCell className="text-right">{totalImpressions.toLocaleString()}</TableCell>
      <TableCell />
    </TableRow>
  </TableFooter>
</Table>
```

#### 3.2.18 Form (react-hook-form + zod)

**Usage guidelines:**
- Every form uses `react-hook-form` for performant validation
- Schema validation with `zod`
- Wizard/multi-step forms use `@stepperize/react`
- AI-assisted forms use `@ai-sdk/react`

```tsx
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

const campaignSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  description: z.string().optional(),
  channel: z.enum(['email', 'social', 'both']),
  budget: z.number().min(0, 'Budget must be positive'),
  startDate: z.date(),
  endDate: z.date().optional(),
});

type CampaignFormValues = z.infer<typeof campaignSchema>;

function CampaignForm() {
  const form = useForm<CampaignFormValues>({
    resolver: zodResolver(campaignSchema),
    defaultValues: {
      name: '',
      channel: 'email',
      budget: 0,
    },
  });

  const onSubmit = (data: CampaignFormValues) => {
    // Submit handler
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Campaign Name</FormLabel>
              <FormControl>
                <Input placeholder="Summer Sale 2026" {...field} />
              </FormControl>
              <FormDescription>
                A descriptive name for your campaign
              </FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        {/* Additional fields... */}
        <Button type="submit">Create Campaign</Button>
      </form>
    </Form>
  );
}
```

#### 3.2.19 Accordion

**Usage guidelines:**
- For collapsing/expanding content sections
- Use for FAQs, settings groups, navigation menus
- Single or multiple item expansion

```tsx
<Accordion type="single" collapsible className="w-full">
  <AccordionItem value="item-1">
    <AccordionTrigger>Campaign Settings</AccordionTrigger>
    <AccordionContent>
      <div className="space-y-4 p-4">
        <div className="flex items-center justify-between">
          <Label>Auto-optimize AI bids</Label>
          <Switch />
        </div>
        <div className="flex items-center justify-between">
          <Label>Send performance reports</Label>
          <Switch defaultChecked />
        </div>
      </div>
    </AccordionContent>
  </AccordionItem>
  <AccordionItem value="item-2">
    <AccordionTrigger>Audience Targeting</AccordionTrigger>
    <AccordionContent>
      {/* Audience configuration */}
    </AccordionContent>
  </AccordionItem>
</Accordion>
```

#### 3.2.20 Alert

**Usage guidelines:**
- For messages requiring user attention
- Use variants matching severity
- Dismissible for non-critical alerts
- Appears inline in page content

```tsx
// Info
<Alert>
  <Info className="h-4 w-4" />
  <AlertTitle>Heads up!</AlertTitle>
  <AlertDescription>
    Your campaign budget is 80% used. Consider increasing it.
  </AlertDescription>
</Alert>

// Destructive
<Alert variant="destructive">
  <AlertCircle className="h-4 w-4" />
  <AlertTitle>Error</AlertTitle>
  <AlertDescription>
    Failed to connect to your social media account. Please reconnect.
  </AlertDescription>
</Alert>

// Success
<Alert variant="success">
  <CheckCircle2 className="h-4 w-4" />
  <AlertTitle>Campaign Launched</AlertTitle>
  <AlertDescription>
    Your campaign is now live across all channels.
  </AlertDescription>
</Alert>

// Warning
<Alert variant="warning">
  <TriangleAlert className="h-4 w-4" />
  <AlertTitle>Budget Warning</AlertTitle>
  <AlertDescription>
    You're approaching your monthly budget limit.
  </AlertDescription>
</Alert>
```

#### 3.2.21 Breadcrumb

**Usage guidelines:**
- Show current page location in hierarchy
- Use `>` separator (not `/`)
- Last item is current page (not a link)
- Truncate long paths with ellipsis

```tsx
<Breadcrumb>
  <BreadcrumbList>
    <BreadcrumbItem>
      <BreadcrumbLink href="/">Dashboard</BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbLink href="/campaigns">Campaigns</BreadcrumbLink>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <DropdownMenu>
        <DropdownMenuTrigger className="flex items-center gap-1">
          <Ellipsis className="h-4 w-4" />
          <span className="sr-only">More</span>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuItem>Q2 Newsletter</DropdownMenuItem>
          <DropdownMenuItem>Summer Sale</DropdownMenuItem>
          <DropdownMenuItem>Product Launch</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem>
      <BreadcrumbPage>Summer Sale 2026</BreadcrumbPage>
    </BreadcrumbItem>
  </BreadcrumbList>
</Breadcrumb>
```

#### 3.2.22 Calendar & Date Picker

**Usage guidelines:**
- Calendar for date selection in forms
- Date Picker as a composed Input + Calendar popover
- Range selection available for date ranges

```tsx
// Single date picker
<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline" className="w-[280px] justify-start text-left font-normal">
      <CalendarIcon className="mr-2 h-4 w-4" />
      {date ? format(date, 'PPP') : <span>Pick a date</span>}
    </Button>
  </PopoverTrigger>
  <PopoverContent className="w-auto p-0">
    <Calendar
      mode="single"
      selected={date}
      onSelect={setDate}
      initialFocus
    />
  </PopoverContent>
</Popover>

// Date range picker
<Popover>
  <PopoverTrigger asChild>
    <Button variant="outline" className="w-[300px] justify-start text-left font-normal">
      <CalendarIcon className="mr-2 h-4 w-4" />
      {date?.from ? (
        date.to ? (
          <>
            {format(date.from, 'LLL dd, y')} - {format(date.to, 'LLL dd, y')}
          </>
        ) : (
          format(date.from, 'LLL dd, y')
        )
      ) : (
        <span>Pick a date range</span>
      )}
    </Button>
  </PopoverTrigger>
  <PopoverContent className="w-auto p-0" align="start">
    <Calendar
      initialFocus
      mode="range"
      defaultMonth={date?.from}
      selected={date}
      onSelect={setDate}
      numberOfMonths={2}
    />
  </PopoverContent>
</Popover>
```

#### 3.2.23 Command (⌘K Palette)

**Usage guidelines:**
- Global search/command palette opened via `Cmd+K` / `Ctrl+K`
- Search across all modules, contacts, campaigns, settings
- Recent searches shown before typing
- Keyboard shortcut labels beside commands

```tsx
<CommandDialog open={open} onOpenChange={setOpen}>
  <CommandInput placeholder="Search campaigns, contacts, settings..." />
  <CommandList>
    <CommandEmpty>No results found.</CommandEmpty>
    <CommandGroup heading="Suggestions">
      <CommandItem onSelect={() => router.push('/campaigns/new')}>
        <Plus className="mr-2 h-4 w-4" />
        <span>Create new campaign</span>
      </CommandItem>
      <CommandItem onSelect={() => router.push('/analytics')}>
        <BarChart3 className="mr-2 h-4 w-4" />
        <span>View analytics dashboard</span>
      </CommandItem>
    </CommandGroup>
    <CommandSeparator />
    <CommandGroup heading="Recent Campaigns">
      <CommandItem onSelect={() => router.push('/campaigns/123')}>
        <FileText className="mr-2 h-4 w-4" />
        <span>Summer Sale 2026</span>
        <CommandShortcut>⌘1</CommandShortcut>
      </CommandItem>
      <CommandItem onSelect={() => router.push('/campaigns/456')}>
        <FileText className="mr-2 h-4 w-4" />
        <span>Product Launch Q3</span>
        <CommandShortcut>⌘2</CommandShortcut>
      </CommandItem>
    </CommandGroup>
    <CommandSeparator />
    <CommandGroup heading="Settings">
      <CommandItem onSelect={() => router.push('/settings/workspace')}>
        <Settings className="mr-2 h-4 w-4" />
        <span>Workspace settings</span>
      </CommandItem>
      <CommandItem onSelect={() => router.push('/settings/team')}>
        <Users className="mr-2 h-4 w-4" />
        <span>Team management</span>
      </CommandItem>
    </CommandGroup>
  </CommandList>
</CommandDialog>
```

#### 3.2.24 Data Table

**Usage guidelines:**
- For complex tabular data with sorting, filtering, pagination
- Built on `@tanstack/react-table`
- Responsive: card view on mobile
- Row selection for batch actions

```tsx
'use client';

import { DataTable } from '@/components/ui/data-table';
import { columns } from './columns';
import { useQuery } from '@tanstack/react-query';

export function CampaignTable() {
  const { data, isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => fetchCampaigns(),
  });

  return (
    <DataTable
      columns={columns}
      data={data?.items ?? []}
      isLoading={isLoading}
      // Feature flags
      enableSorting
      enableFiltering
      enableColumnVisibility
      enableRowSelection
      enablePagination
      enableExport
      // Config
      pageSize={25}
      searchPlaceholder="Search campaigns..."
      emptyMessage="No campaigns found. Create your first campaign to get started."
    />
  );
}
```

#### 3.2.25 File Upload

**Usage guidelines:**
- Drag-and-drop zone + click to browse
- Preview for images, documents
- Progress bar during upload
- Multiple file support

```tsx
<FileUpload
  accept={{
    'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
    'application/pdf': ['.pdf'],
    'text/csv': ['.csv'],
  }}
  maxFiles={5}
  maxSize={10 * 1024 * 1024} // 10MB
  onUpload={handleUpload}
>
  <div className="flex flex-col items-center gap-2 p-12 border-2 border-dashed rounded-lg">
    <Upload className="h-8 w-8 text-muted-foreground" />
    <p className="text-sm text-muted-foreground">
      <span className="font-semibold text-primary">Click to upload</span> or drag and drop
    </p>
    <p className="text-xs text-muted-foreground">
      PNG, JPG, WebP, PDF, CSV (max 10MB each)
    </p>
  </div>
</FileUpload>
```

#### 3.2.26 Skeleton

**Usage guidelines:**
- Show loading UI that matches eventual content shape
- Use `Skeleton` for every data-fetching component
- Never show raw spinners for content loading

```tsx
// Card skeleton
<div className="space-y-3">
  <Skeleton className="h-[125px] w-full rounded-xl" />
  <div className="space-y-2">
    <Skeleton className="h-4 w-[250px]" />
    <Skeleton className="h-4 w-[200px]" />
  </div>
</div>

// Table skeleton
<div className="space-y-3">
  <Skeleton className="h-8 w-full" />
  {Array.from({ length: 5 }).map((_, i) => (
    <Skeleton key={i} className="h-12 w-full" />
  ))}
</div>

// Form skeleton
<div className="space-y-6">
  {Array.from({ length: 4 }).map((_, i) => (
    <div key={i} className="space-y-2">
      <Skeleton className="h-4 w-[100px]" />
      <Skeleton className="h-10 w-full" />
    </div>
  ))}
</div>
```

#### 3.2.27 Additional Components

**Progress bar:**
```tsx
<Progress value={65} className="w-[60%]" />
// With label: "65% complete"
```

**Separator:**
```tsx
<Separator className="my-4" />
// Vertical: <Separator orientation="vertical" className="mx-2 h-8" />
```

**Sheet (slide-over panel):**
```tsx
<Sheet>
  <SheetTrigger>Open Panel</SheetTrigger>
  <SheetContent side="right" className="w-[400px] sm:w-[540px]">
    <SheetHeader>
      <SheetTitle>Campaign Details</SheetTitle>
      <SheetDescription>View and edit campaign properties</SheetDescription>
    </SheetHeader>
    {/* Panel content */}
    <SheetFooter>
      <Button type="submit">Save changes</Button>
    </SheetFooter>
  </SheetContent>
</Sheet>
```

**Slider:**
```tsx
<Slider
  defaultValue={[50]}
  max={100}
  step={1}
  onValueChange={(value) => setBudget(value[0])}
/>
```

**Toggle:**
```tsx
<Toggle variant="outline" aria-label="Toggle bold">
  <Bold className="h-4 w-4" />
</Toggle>
```

**Stepper (multi-step wizard):**
```tsx
<Stepper>
  <Step label="Campaign Details" description="Name, channel, budget" />
  <Step label="Audience" description="Target demographics" />
  <Step label="Content" description="Email, social assets" />
  <Step label="Review" description="Preview and launch" />
</Stepper>
```

**Sonner (toast provider):**
```tsx
// In layout or provider
<Toaster
  position="bottom-right"
  toastOptions={{
    duration: 4000,
    style: { background: 'var(--color-bg-primary)', border: '1px solid var(--color-border)' },
  }}
/>
```

---

## 4. Layout System

### 4.1 App Shell

The App Shell is the persistent wrapper around all authenticated pages in AMC. It consists of three zones:

```
┌─────────────────────────────────────────────────────────────┐
│  TOPBAR                                                      │
│  ┌──────┬──────┬──────┬──────┬──────────────┬──────┬──────┐ │
│  │  ☰   │ 🏠   │      │Search...           │ 🔔   │ 👤   │ │
│  └──────┴──────┴──────┴──────┴──────────────┴──────┴──────┘ │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                   │
│ SIDEBAR  │              MAIN CONTENT AREA                    │
│          │                                                   │
│ 📊 CRM   │   ┌────────────────────────────────────────┐     │
│ 📧 Email │   │                                        │     │
│ 🤖 AI    │   │         Page content renders here       │     │
│ 📈 Anal. │   │                                        │     │
│ ⚙️ Set.  │   │                                        │     │
│          │   └────────────────────────────────────────┘     │
│          │                                                   │
└──────────┴──────────────────────────────────────────────────┘
```

**Layout implementation:**

```tsx
// app/(dashboard)/layout.tsx
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </AppShell>
  );
}
```

### 4.2 Sidebar

The sidebar provides persistent navigation across all AMC modules.

**States:**
- **Expanded** (desktop default): Full labels + icons, 256px width
- **Collapsed** (tablet / user preference): Icons only, 64px width
- **Hidden** (mobile): Overlay panel triggered by hamburger menu
- **Resizable**: User can drag edge to resize between 200px and 320px

```tsx
'use client';

import { useSidebar } from '@/store/use-sidebar';
import { cn } from '@/lib/utils';

const navItems = [
  { label: 'Dashboard', icon: LayoutDashboard, href: '/dashboard' },
  { label: 'CRM', icon: Contact2, href: '/crm' },
  { label: 'Campaigns', icon: Megaphone, href: '/campaigns' },
  { label: 'AI Agents', icon: Bot, href: '/agents' },
  { label: 'Analytics', icon: BarChart3, href: '/analytics' },
  { label: 'SEO', icon: Search, href: '/seo' },
  { label: 'Social', icon: Share2, href: '/social' },
  { label: 'Automation', icon: Workflow, href: '/automation' },
  { label: 'Knowledge Base', icon: BookOpen, href: '/knowledge' },
  { label: 'Marketplace', icon: Store, href: '/marketplace' },
  { label: 'Settings', icon: Settings, href: '/settings' },
];

export function Sidebar() {
  const { collapsed, setCollapsed } = useSidebar();
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-300',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo area */}
      <div className="flex h-14 items-center border-b px-4">
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2 font-semibold">
            <Shield className="h-6 w-6 text-primary" />
            <span>Aegis MC</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="ml-auto"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-2 space-y-1">
        {navItems.map((item) => (
          <Tooltip key={item.href}>
            <TooltipTrigger asChild>
              <Link
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  pathname.startsWith(item.href)
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            </TooltipTrigger>
            {collapsed && <TooltipContent side="right">{item.label}</TooltipContent>}
          </Tooltip>
        ))}
      </nav>

      {/* Bottom section */}
      <div className="border-t p-2">
        {!collapsed ? (
          <div className="flex items-center gap-3 rounded-lg px-3 py-2">
            <Avatar className="h-8 w-8">
              <AvatarImage src="/avatars/user.jpg" />
              <AvatarFallback>JD</AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">John Doe</p>
              <p className="text-xs text-muted-foreground truncate">Acme Corp</p>
            </div>
          </div>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <Avatar className="h-8 w-8 mx-auto">
                <AvatarImage src="/avatars/user.jpg" />
                <AvatarFallback>JD</AvatarFallback>
              </Avatar>
            </TooltipTrigger>
            <TooltipContent side="right">John Doe — Acme Corp</TooltipContent>
          </Tooltip>
        )}
      </div>
    </aside>
  );
}
```

### 4.3 Topbar

The topbar contains global actions accessible from any page.

```
┌──────────────────────────────────────────────────────────────┐
│  ☰    🏠 Dashboard  ›  Campaigns  ›  Summer Sale  [Status]  │
│                                     🔍 ⌘K   🔔 🔄   👤  ▼  │
└──────────────────────────────────────────────────────────────┘
```

**Elements:**

| Region | Components | Behavior |
|--------|-----------|----------|
| Left | Hamburger (mobile), Breadcrumbs | Toggle sidebar mobile, show page hierarchy |
| Center | (Empty or page context) | Occasional page-specific actions |
| Right | Search (⌘K), Notifications, Help, Workspace Switcher, User Menu | Always visible |

### 4.4 Page Layouts

#### 4.4.1 List/Detail Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Filters  │  Search...  │  [+ New Campaign]  │  Export ▼    │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Campaign Name      Status    Channel    Impressions   │  │
│  │  ├────────────────────────────────────────────────────┤  │
│  │  │ Summer Sale 2026  ● Active  Email      124,592     │  │
│  │  │ Product Launch    ● Draft   Social     0           │  │
│  │  │ Newsletter Q3     ● Active  Both       89,234      │  │
│  │  │ ...                                              │  │
│  │  └────────────────────────────────────────────────────┘  │
│  │  Showing 1-25 of 142              < 1  2  3 ... 6 >     │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### 4.4.2 Split Pane Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Breadcrumbs                                        [Edit]  │
├───────────────────┬──────────────────────────────────────────┤
│                   │                                          │
│  CAMPAIGN LIST    │      CAMPAIGN DETAIL                     │
│  (Draggable pane) │                                          │
│                   │  ┌──────────────────────────────────┐    │
│  ┌─────────────┐  │  │  Overview │ Analytics │ Settings │    │
│  │ Summer Sale │  │  ├──────────────────────────────────┤    │
│  │ Product     │  │  │                                  │    │
│  │ Newsletter  │  │  │  Campaign details content...     │    │
│  │ Launch      │  │  │                                  │    │
│  └─────────────┘  │  └──────────────────────────────────┘    │
│                   │                                          │
└───────────────────┴──────────────────────────────────────────┘
```

#### 4.4.3 Full-Width Layout

```
┌──────────────────────────────────────────────────────────────┐
│                    [Dashboard / Analytics]                    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   KPI Cards Row (full width grid)                            │
│                                                              │
│   ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                       │
│   │Revenue│ │Leads │ │Conv. │ │ROAS  │                       │
│   │$124K  │ │1,892 │ │3.09% │ │4.2x  │                       │
│   │↑12%   │ │↑8%   │ │↑2%   │ │↓1%   │                       │
│   └──────┘ └──────┘ └──────┘ └──────┘                       │
│                                                              │
│   Main Chart (full width)                                    │
│   ┌──────────────────────────────────────────────────────┐   │
│   │  Line chart: Revenue over time                       │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                              │
│   Two-column section                                         │
│   ┌────────────────────┐ ┌────────────────────┐              │
│   │  Recent Activity   │ │  AI Suggestions    │              │
│   └────────────────────┘ └────────────────────┘              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

#### 4.4.4 Modal-Over Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Dimmed/disabled background content                         │
│                                                              │
│                    ┌──────────────────────────┐               │
│                    │  DIALOG TITLE            │               │
│                    │                          │               │
│                    │  Form content...         │               │
│                    │                          │               │
│                    │  [Cancel]  [Confirm]     │               │
│                    └──────────────────────────┘               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.5 Responsive Breakpoint Behaviors

| Component | sm (0-639) | md (640-1023) | lg (1024-1279) | xl (1280+) |
|-----------|-----------|--------------|----------------|------------|
| Sidebar | Hidden overlay | Collapsed (icons) | Expanded or collapsed | Expanded (256px) |
| Topbar | Breadcrumb truncation | Full breadcrumbs | Full breadcrumbs | Full breadcrumbs |
| DataTable | Card list | Card list | Table (scroll) | Full table |
| Split pane | Single stacked | Single stacked | Side by side | Side by side |
| KPI cards | 1 col | 2 col | 3 col | 4 col |
| Form columns | Single | Single | 2 col | 2-3 col |
| Dialog | Bottom sheet (full) | Centered modal | Centered modal | Centered modal |
| Charts | Single column | Single column | Two charts side-by-side | Multi-chart grid |

---

## 5. Page Patterns

### 5.1 Dashboard Page

The dashboard serves as the landing page after login — a high-level overview of marketing performance.

**Content zones (top to bottom):**

1. **Welcome banner** — personalized greeting with AI insight of the day
2. **KPI row** — 4 stat cards (Revenue, Leads, Conversion Rate, ROAS)
3. **Main chart** — revenue/performance over time with period selector
4. **Two-column section**:
   - Left: Recent activity feed (timeline)
   - Right: AI suggestions (contextual recommendations)
5. **Bottom row**: Campaign performance table (top 5 recent)

```tsx
// app/(dashboard)/dashboard/page.tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <WelcomeBanner userName={user.name} insight={aiInsight} />
      <KPIRow metrics={metrics} />
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Revenue Over Time">
          <RevenueChart data={revenueData} period={period} />
        </ChartCard>
        <ChartCard title="Channel Performance">
          <ChannelBreakdown data={channelData} />
        </ChartCard>
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RecentActivity activities={recentActivity} />
        </div>
        <AISuggestionsCard suggestions={suggestions} />
      </div>
      <RecentCampaignsTable campaigns={recentCampaigns} />
    </div>
  );
}
```

### 5.2 List Page (DataTable)

**Pattern**: Filter bar → DataTable → Pagination

```tsx
export function CampaignListPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        title="Campaigns"
        description="Manage all your marketing campaigns"
        actions={<Button>+ New Campaign</Button>}
      />
      <DataTableToolbar
        filters={[
          { key: 'status', label: 'Status', options: statusOptions },
          { key: 'channel', label: 'Channel', options: channelOptions },
          { key: 'dateRange', label: 'Date Range', type: 'date' },
        ]}
        searchPlaceholder="Search campaigns..."
        onSearch={setSearch}
      >
        <DataTableViewOptions columns={columns} />
        <DataTableExport onExport={handleExport} />
      </DataTableToolbar>
      <DataTable
        columns={columns}
        data={campaigns}
        isLoading={isLoading}
        pageSize={25}
        onRowClick={(row) => router.push(`/campaigns/${row.id}`)}
      />
      <DataTablePagination
        currentPage={page}
        totalPages={totalPages}
        onPageChange={setPage}
      />
    </div>
  );
}
```

### 5.3 Detail Page

**Layout**: Back button + title → Tabs → Side panel for metadata

```tsx
export function CampaignDetailPage({ id }: { id: string }) {
  return (
    <div className="flex gap-6">
      <div className="flex-1 space-y-6">
        <PageHeader
          backHref="/campaigns"
          title={campaign.name}
          subtitle={`Created ${format(campaign.createdAt, 'PPP')}`}
          actions={
            <>
              <Badge variant={statusVariant}>{campaign.status}</Badge>
              <Button variant="outline" onClick={handleDuplicate}>Duplicate</Button>
              <Button onClick={handleEdit}>Edit Campaign</Button>
            </>
          }
        />
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
            <TabsTrigger value="content">Content</TabsTrigger>
            <TabsTrigger value="activity">Activity Feed</TabsTrigger>
          </TabsList>
          <TabsContent value="overview">{/* ... */}</TabsContent>
          <TabsContent value="analytics">{/* ... */}</TabsContent>
          <TabsContent value="content">{/* ... */}</TabsContent>
          <TabsContent value="activity">
            <ActivityFeed activities={activities} />
          </TabsContent>
        </Tabs>
      </div>
      <aside className="w-80 space-y-4">
        <DetailPanel>
          <DetailPanel.Section title="Campaign Info">
            <DetailRow label="Status" value={campaign.status} />
            <DetailRow label="Channel" value={campaign.channel} />
            <DetailRow label="Budget" value={formatCurrency(campaign.budget)} />
            <DetailRow label="Start Date" value={format(campaign.startDate, 'PPP')} />
            <DetailRow label="End Date" value={format(campaign.endDate, 'PPP')} />
          </DetailPanel.Section>
          <DetailPanel.Section title="Performance">
            <DetailRow label="Impressions" value={campaign.impressions.toLocaleString()} />
            <DetailRow label="Clicks" value={campaign.clicks.toLocaleString()} />
            <DetailRow label="CTR" value={`${campaign.ctr}%`} />
          </DetailPanel.Section>
        </DetailPanel>
      </aside>
    </div>
  );
}
```

### 5.4 Form Page (Campaign Wizard)

**Multi-step wizard with stepper progress indicator:**

```tsx
'use client';

import { useStepper } from '@/components/ui/stepper';

const steps = [
  { id: 'basics', label: 'Basics', description: 'Campaign name & channel' },
  { id: 'audience', label: 'Audience', description: 'Target demographics' },
  { id: 'content', label: 'Content', description: 'Creative assets' },
  { id: 'budget', label: 'Budget', description: 'Budget & schedule' },
  { id: 'review', label: 'Review', description: 'Preview & launch' },
];

export function CampaignWizard() {
  const { currentStep, goToNextStep, goToPrevStep, isFirstStep, isLastStep } = useStepper();

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <PageHeader
        title="Create Campaign"
        description="Set up your multi-channel marketing campaign"
      />
      <Stepper steps={steps} currentStep={currentStep} />

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {currentStep === 'basics' && <CampaignBasicsStep />}
          {currentStep === 'audience' && <AudienceStep />}
          {currentStep === 'content' && <ContentStep />}
          {currentStep === 'budget' && <BudgetStep />}
          {currentStep === 'review' && <ReviewStep data={form.getValues()} />}

          <div className="flex justify-between">
            <Button
              variant="outline"
              onClick={goToPrevStep}
              disabled={isFirstStep}
            >
              Previous
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={handleSaveDraft}>
                Save Draft
              </Button>
              {isLastStep ? (
                <Button type="submit">Launch Campaign</Button>
              ) : (
                <Button onClick={handleNext}>
                  Next Step
                </Button>
              )}
            </div>
          </div>
        </form>
      </Form>
    </div>
  );
}
```

### 5.5 Settings Page

**Layout**: Left navigation → Right content panel

```
┌──────────────────────────────────────────────────────────────┐
│  Settings                                                    │
├───────────────┬──────────────────────────────────────────────┤
│               │                                              │
│  General      │  GENERAL                                     │
│  Workspace    │  ┌────────────────────────────────────────┐  │
│  Team         │  │  Workspace Name    [Acme Corp    ]     │  │
│  Billing      │  │  Industry          [Marketing    ]  ▼  │  │
│  API Keys     │  │  Timezone          [(UTC-5) EST]  ▼   │  │
│  Notifications│  └────────────────────────────────────────┘  │
│  Appearance   │                                              │
│  Integrations │  APPEARANCE                                  │
│               │  ┌────────────────────────────────────────┐  │
│               │  │  Theme          ● Light  ○ Dark  ○ System│  │
│               │  │  Density        ○ Comfortable ● Compact │  │
│               │  └────────────────────────────────────────┘  │
│               │                                              │
│               │  [Save Changes]                              │
└───────────────┴──────────────────────────────────────────────┘
```

### 5.6 AI Chat Page

```
┌──────────────────────────────────────────────────────────────┐
│  AI Agents  │  Marketing Strategist  │  🤖  ▼               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  🤖 Marketing Strategist                              │  │
│  │  Hello! I can help you create and optimize your       │  │
│  │  marketing campaigns. What would you like to do?      │  │
│  │  10:32 AM                                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Me: Create a summer sale campaign for our email list  │  │
│  │  10:33 AM                                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  🤖 I'll help you set that up. Here's what I'll do:   │  │
│  │                                                       │  │
│  │  🔍 Searching for past summer campaigns... Done       │  │
│  │  📊 Analyzing audience segments... Done               │  │
│  │  ✏️ Drafting email copy... In progress               │  │
│  │  🎨 Selecting creative assets... Pending              │  │
│  │                                                       │  │
│  │  Here's the draft campaign summary:                   │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │  Campaign: Summer Sale 2026                    │  │  │
│  │  │  Channel: Email + Social                       │  │  │
│  │  │  Budget: $5,000                                │  │  │
│  │  │  Audience: Warm leads + past customers         │  │  │
│  │  │  Schedule: Jul 1 - Jul 15                      │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  Would you like me to:                                │  │
│  │  [Create Campaign] [Refine] [Modify Audience]         │  │
│  │  10:33 AM                                             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Type a message...         [📎] [🎤] [Send →]       │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 5.7 Calendar Page

```
┌──────────────────────────────────────────────────────────────┐
│  Calendar                     ◀ June 2026 ▶  [Today]        │
│  [Month] [Week] [Day]                                       │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────┤
│  Sun     │  Mon     │  Tue     │  Wed     │  Thu     │ Fri  │
│  1       │  2       │  3       │  4       │  5       │  6   │
│          │          │          │          │          │      │
│          │          │          │          │          │      │
│  ┌──────┐│          │          │ ┌──────┐ │          │      │
│  │CRM   ││          │          │ │Email │ │          │      │
│  │Webin.││          │          │ │Launch│ │          │      │
│  └──────┘│          │          │ └──────┘ │          │      │
├──────────┼──────────┼──────────┼──────────┼──────────┼──────┤
│  7       │  8       │  9       │  10      │  11      │  12  │
│          │          │          │          │          │      │
│          │ ┌──────┐ │          │          │ ┌──────┐ │      │
│          │ │Social│ │          │          │ │Report│ │      │
│          │ │Post  │ │          │          │ │Due   │ │      │
│          │ └──────┘ │          │          │ └──────┘ │      │
└──────────┴──────────┴──────────┴──────────┴──────────┴──────┘
```

### 5.8 Kanban Page

```
┌──────────────────────────────────────────────────────────────┐
│  Campaign Pipeline                          [+ Add Card]    │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  TO DO       │  IN PROGRESS │  REVIEW      │  DONE          │
│              │              │              │                │
│  ┌────────┐  │  ┌────────┐  │  ┌────────┐  │  ┌────────┐   │
│  │ Summer │  │  │ Product│  │  │ News-  │  │  │ Q2 Re- │   │
│  │ Sale   │  │  │ Launch │  │  │ letter │  │  │ port   │   │
│  │ Idea   │  │  │ Draft  │  │  │ Review │  │  │ Done   │   │
│  │        │  │  │        │  │  │        │  │  │        │   │
│  │ Jan 15 │  │  │ Feb 1  │  │  │ Jan 28 │  │  │ Jan 20 │   │
│  └────────┘  │  └────────┘  │  └────────┘  │  └────────┘   │
│              │              │              │                │
│  ┌────────┐  │  ┌────────┐  │              │  ┌────────┐   │
│  │ Webinar│  │  │ A/B    │  │              │  │ Market │   │
│  │ Plan   │  │  │ Test   │  │              │  │ Report │   │
│  │        │  │  │        │  │              │  │        │   │
│  │ Feb 10 │  │  │ Jan 25 │  │              │  │ Jan 18 │   │
│  └────────┘  │  └────────┘  │              │  └────────┘   │
│              │              │              │                │
│  2 cards     │  2 cards     │  1 card      │  2 cards       │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

---

## 6. Navigation & Information Architecture

### 6.1 Main Navigation Structure

The primary navigation is organized into logical groups within the sidebar.

| Group | Module | Icon | Description |
|-------|--------|------|-------------|
| **Overview** | Dashboard | `LayoutDashboard` | KPI summary, recent activity |
| **Marketing** | CRM | `Contact2` | Contact management, pipelines |
| | Campaigns | `Megaphone` | Multi-channel campaign builder |
| | SEO | `Search` | SEO analysis, keyword tracking |
| | Social | `Share2` | Social media scheduling |
| **AI** | AI Agents | `Bot` | Agent management & chat |
| | Automation | `Workflow` | n8n workflow builder |
| **Insights** | Analytics | `BarChart3` | Reports & dashboards |
| | Knowledge Base | `BookOpen` | Brand guidelines, strategies |
| **Ecosystem** | Marketplace | `Store` | Extensions & integrations |
| **System** | Settings | `Settings` | Workspace configuration |

### 6.2 Workspace Switcher

A dropdown in the topbar for multi-tenant workspace switching.

```tsx
<Popover>
  <PopoverTrigger asChild>
    <Button variant="ghost" className="gap-2 px-2">
      <Building2 className="h-4 w-4" />
      <span className="font-medium">Acme Corp</span>
      <ChevronDown className="h-3 w-3 text-muted-foreground" />
    </Button>
  </PopoverTrigger>
  <PopoverContent className="w-72 p-2" align="start">
    <Command>
      <CommandInput placeholder="Search workspaces..." />
      <CommandList>
        <CommandGroup heading="Recent">
          <CommandItem onSelect={() => switchWorkspace('acme')}>
            <Building2 className="mr-2 h-4 w-4" />
            <span>Acme Corp</span>
            <Badge variant="secondary" className="ml-auto">Current</Badge>
          </CommandItem>
          <CommandItem onSelect={() => switchWorkspace('client-a')}>
            <Building2 className="mr-2 h-4 w-4" />
            <span>Client A Agency</span>
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="All Workspaces">
          <CommandItem onSelect={() => switchWorkspace('personal')}>
            <User className="mr-2 h-4 w-4" />
            <span>Personal</span>
          </CommandItem>
          <CommandItem onSelect={() => switchWorkspace('startup')}>
            <Building2 className="mr-2 h-4 w-4" />
            <span>Startup Inc.</span>
          </CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandItem onSelect={() => router.push('/workspaces/new')}>
          <Plus className="mr-2 h-4 w-4" />
          <span>Create Workspace</span>
        </CommandItem>
      </CommandList>
    </Command>
  </PopoverContent>
</Popover>
```

### 6.3 Quick-Search (⌘K)

The global command palette provides instant access to any feature, record, or action.

**Activation**: `Cmd+K` (Mac) / `Ctrl+K` (Windows/Linux)

**Search scope ordering:**
1. **Commands** — Create campaign, New contact, View analytics
2. **Recent items** — Recently viewed campaigns, contacts
3. **Navigation** — All pages matching search query
4. **Records** — Campaigns, contacts, agents by name
5. **Settings** — Settings pages matching search

### 6.4 Breadcrumb Strategy

**Rules:**
- Every page except Dashboard gets breadcrumbs
- Maximum 4 levels deep (Dashboard > Section > Subsection > Item)
- Current page is always plain text (not linked)
- Use ellipsis dropdown for truncated middle sections
- Breadcrumbs appear in the topbar

**Pattern by page type:**

| Page Type | Breadcrumb Example |
|-----------|-------------------|
| List page | `Dashboard > Campaigns` |
| Detail page | `Dashboard > Campaigns > Summer Sale 2026` |
| Settings | `Dashboard > Settings > Workspace` |
| Wizard | `Dashboard > Campaigns > New Campaign` |
| AI Chat | `Dashboard > AI Agents > Marketing Strategist` |

### 6.5 Deep-Linking / Shareable URLs

All application states must be shareable via URL.

```typescript
// URL patterns
/campaigns                                    // List view (with query params for filters)
/campaigns?status=active&channel=email        // Pre-filtered view
/campaigns/123                                // Detail view
/campaigns/123?tab=analytics                  // Detail view with active tab
/campaigns/new                                // Create wizard
/campaigns/123/edit                           // Edit mode

// Search and filter state in URL
/crm/contacts?query=jane&tags=lead,vip&page=2&sort=name:asc

// Calendar state
/calendar?view=week&date=2026-06-15

// Chat conversation
/agents/chat/456
```

---

## 7. Data Display & Visualization

### 7.1 Chart Components (Recharts-Based)

All charts use Recharts v2 with consistent theming and responsive containers.

**Shared chart configuration:**

```tsx
// lib/chart-config.ts
export const chartDefaults = {
  // Consistent color palette for chart series
  colors: [
    'var(--color-primary-500)',
    'var(--color-secondary-500)',
    'var(--color-accent-500)',
    'var(--color-info-500)',
    'var(--color-warning-500)',
    'var(--color-error-500)',
  ],
  // Grid
  grid: {
    strokeDasharray: '3 3',
    stroke: 'var(--color-border)',
  },
  // Tooltip
  tooltip: {
    contentStyle: {
      background: 'var(--color-bg-primary)',
      border: '1px solid var(--color-border)',
      borderRadius: '8px',
      boxShadow: 'var(--shadow-lg)',
    },
  },
  // Responsive container
  responsive: true,
};
```

#### 7.1.1 Line Chart

```tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export function RevenueChart({ data }: { data: { date: string; revenue: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" fontSize={12} />
        <YAxis fontSize={12} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
        <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, 'Revenue']} />
        <Line
          type="monotone"
          dataKey="revenue"
          stroke="var(--color-primary-500)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

#### 7.1.2 Bar Chart

```tsx
<BarChart data={channelData}>
  <CartesianGrid strokeDasharray="3 3" />
  <XAxis dataKey="channel" />
  <YAxis />
  <Tooltip />
  <Legend />
  <Bar dataKey="impressions" fill="var(--color-primary-500)" radius={[4, 4, 0, 0]} />
  <Bar dataKey="clicks" fill="var(--color-secondary-500)" radius={[4, 4, 0, 0]} />
</BarChart>
```

#### 7.1.3 Area Chart

```tsx
<AreaChart data={data}>
  <CartesianGrid strokeDasharray="3 3" />
  <XAxis dataKey="month" />
  <YAxis />
  <Tooltip />
  <Area
    type="monotone"
    dataKey="leads"
    stroke="var(--color-accent-500)"
    fill="var(--color-accent-200)"
    fillOpacity={0.3}
  />
</AreaChart>
```

#### 7.1.4 Pie Chart

```tsx
<PieChart width={400} height={400}>
  <Pie
    data={channelMix}
    cx="50%"
    cy="50%"
    innerRadius={60}
    outerRadius={120}
    paddingAngle={2}
    dataKey="value"
  >
    {channelMix.map((entry, index) => (
      <Cell key={`cell-${index}`} fill={chartDefaults.colors[index % chartDefaults.colors.length]} />
    ))}
  </Pie>
  <Tooltip />
  <Legend />
</PieChart>
```

#### 7.1.5 Radar Chart

```tsx
<RadarChart cx="50%" cy="50%" outerRadius="80%" data={data}>
  <PolarGrid />
  <PolarAngleAxis dataKey="metric" />
  <PolarRadiusAxis angle={30} domain={[0, 100]} />
  <Radar
    name="Current"
    dataKey="current"
    stroke="var(--color-primary-500)"
    fill="var(--color-primary-500)"
    fillOpacity={0.3}
  />
  <Radar
    name="Target"
    dataKey="target"
    stroke="var(--color-secondary-500)"
    fill="var(--color-secondary-500)"
    fillOpacity={0.3}
  />
  <Legend />
</RadarChart>
```

#### 7.1.6 Funnel Chart

```tsx
// Custom funnel using stacked bar (Recharts doesn't have native funnel)
export function FunnelChart({ stages }: { stages: { name: string; count: number }[] }) {
  const total = stages[0].count;
  return (
    <div className="space-y-2">
      {stages.map((stage, i) => {
        const width = (stage.count / total) * 100;
        return (
          <div key={stage.name} className="space-y-1">
            <div className="flex justify-between text-sm">
              <span>{stage.name}</span>
              <span className="font-medium">{stage.count.toLocaleString()}</span>
            </div>
            <div className="h-8 rounded-md bg-primary/10 overflow-hidden"
                 style={{ width: `${width}%` }}>
              <div className="h-full bg-primary" style={{ width: '100%' }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
```

### 7.2 Data Table (Advanced)

The full-featured DataTable component built on TanStack Table:

**Features:**
- Column sorting (multi-column support)
- Column filtering (text, select, date range)
- Column visibility toggle
- Row selection (checkbox + shift-click range select)
- Row actions (dropdown per row)
- Pagination (server-side or client-side)
- Export (CSV, Excel, PDF)
- Infinite scroll mode
- Column reordering (drag)
- Column resizing
- Sticky headers
- Row pinning

```tsx
'use client';

import { useQuery } from '@tanstack/react-query';
import { DataTable } from '@/components/ui/data-table';
import { columns } from './columns';
import { useColumnFilters, useSorting, usePagination } from '@/hooks/use-data-table';

export function ContactsTable() {
  const { sorting, onSortingChange } = useSorting();
  const { columnFilters, onColumnFiltersChange } = useColumnFilters();
  const { pagination, onPaginationChange } = usePagination({ pageSize: 25 });

  const { data, isLoading } = useQuery({
    queryKey: ['contacts', sorting, columnFilters, pagination],
    queryFn: () => fetchContacts({ sorting, columnFilters, pagination }),
  });

  return (
    <DataTable
      columns={columns}
      data={data?.items ?? []}
      isLoading={isLoading}
      pageCount={data?.pageCount ?? 0}
      // State
      sorting={sorting}
      onSortingChange={onSortingChange}
      columnFilters={columnFilters}
      onColumnFiltersChange={onColumnFiltersChange}
      pagination={pagination}
      onPaginationChange={onPaginationChange}
      // Features
      enableRowSelection
      enableColumnVisibility
      enableExport
      enableInfiniteScroll={false}
    />
  );
}
```

### 7.3 Stat Cards

```tsx
export function StatCard({
  title,
  value,
  trend,
  trendLabel,
  icon: Icon,
  variant = 'default',
}: StatCardProps) {
  const trendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;
  const trendColor = trend > 0 ? 'text-green-600' : trend < 0 ? 'text-red-600' : 'text-muted-foreground';

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-1 mt-1">
          <trendIcon className={`h-4 w-4 ${trendColor}`} />
          <span className={`text-sm ${trendColor}`}>
            {Math.abs(trend)}%
          </span>
          <span className="text-xs text-muted-foreground">{trendLabel}</span>
        </div>
        {/* Optional sparkline */}
        {sparklineData && <Sparkline data={sparklineData} />}
      </CardContent>
    </Card>
  );
}
```

### 7.4 Timeline Component

```tsx
export function ActivityFeed({ activities }: { activities: Activity[] }) {
  return (
    <div className="space-y-4">
      <h3 className="font-semibold">Recent Activity</h3>
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
        <div className="space-y-6">
          {activities.map((activity) => (
            <div key={activity.id} className="relative flex gap-4 pl-10">
              {/* Dot */}
              <div className={cn(
                'absolute left-2.5 h-3 w-3 rounded-full border-2 border-background',
                activity.type === 'created' && 'bg-green-500',
                activity.type === 'updated' && 'bg-blue-500',
                activity.type === 'deleted' && 'bg-red-500',
                activity.type === 'note' && 'bg-yellow-500',
              )} />
              {/* Content */}
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2">
                  <Avatar className="h-6 w-6">
                    <AvatarImage src={activity.user.avatar} />
                    <AvatarFallback>{activity.user.initials}</AvatarFallback>
                  </Avatar>
                  <p className="text-sm font-medium">{activity.user.name}</p>
                  <span className="text-xs text-muted-foreground">
                    {formatDistanceToNow(activity.timestamp, { addSuffix: true })}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">{activity.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

### 7.5 JSON Viewer Component

```tsx
'use client';

import { useState } from 'react';

export function JSONViewer({ data, defaultCollapsed = false }: { data: unknown; defaultCollapsed?: boolean }) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-lg border bg-card">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Response</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon-sm" onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
          <Button variant="ghost" size="icon-sm" onClick={handleCopy}>
            {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      </div>
      {!collapsed && (
        <pre className="overflow-auto p-4 text-sm font-mono">
          <code>{JSON.stringify(data, null, 2)}</code>
        </pre>
      )}
    </div>
  );
}
```

---

## 8. AI Agent UI Patterns

### 8.1 Agent Card

```
┌──────────────────────────────────────────────────────┐
│  ┌──────┐    Marketing Strategist                     │
│  │  🤖  │    📊 Expert in multi-channel campaigns    │
│  └──────┘    ● Online     ▲ 89% accuracy             │
│                                                     │
│  Capabilities:                                       │
│  🏷️ Campaign Strategy  🏷️ Copywriting              │
│  🏷️ Audience Analysis  🏷️ A/B Testing             │
│                                                     │
│  [Chat Now]  [Configure]  [View Analytics]          │
└──────────────────────────────────────────────────────┘
```

```tsx
export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Card className="w-[320px]">
      <CardHeader>
        <div className="flex items-start gap-4">
          <Avatar className="h-12 w-12">
            <AvatarImage src={agent.avatar} />
            <AvatarFallback>{agent.name[0]}</AvatarFallback>
          </Avatar>
          <div className="flex-1 space-y-1">
            <CardTitle className="text-base">{agent.name}</CardTitle>
            <CardDescription className="text-sm">{agent.description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Status + Metrics */}
        <div className="flex items-center gap-4 text-sm">
          <span className={cn(
            'flex items-center gap-1',
            agent.status === 'online' && 'text-green-600',
            agent.status === 'busy' && 'text-yellow-600',
            agent.status === 'offline' && 'text-muted-foreground',
          )}>
            <span className="h-2 w-2 rounded-full bg-current" />
            {agent.status}
          </span>
          <span className="text-muted-foreground">▲ {agent.accuracy}% accuracy</span>
        </div>
        {/* Capability tags */}
        <div className="flex flex-wrap gap-1">
          {agent.capabilities.map((cap) => (
            <Badge key={cap} variant="secondary" className="text-xs">
              {cap}
            </Badge>
          ))}
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button className="flex-1" onClick={() => startChat(agent.id)}>
          Chat Now
        </Button>
        <Button variant="outline" size="icon" onClick={() => configure(agent.id)}>
          <Settings className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="icon" onClick={() => viewAnalytics(agent.id)}>
          <BarChart3 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
```

### 8.2 Agent Chat Interface

**Message types:**

| Type | Visual | Description |
|------|--------|-------------|
| User | Right-aligned, primary bg | User's messages |
| Agent | Left-aligned, card bg | AI responses |
| Tool call | Collapsible card | Agent using a tool |
| System | Centered, muted | Status updates |
| Error | Red alert | Error messages |
| Loading | Pulsing dots | Thinking state |

```tsx
export function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user';

  return (
    <div className={cn('flex gap-3', isUser && 'flex-row-reverse')}>
      <Avatar className="h-8 w-8 shrink-0">
        {isUser ? (
          <AvatarFallback>U</AvatarFallback>
        ) : (
          <AvatarImage src={agent.avatar} />
        )}
      </Avatar>
      <div className={cn(
        'flex flex-col gap-1 max-w-[80%]',
        isUser ? 'items-end' : 'items-start'
      )}>
        {/* Message bubble */}
        <div className={cn(
          'rounded-lg px-4 py-2 text-sm',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}>
          <MarkdownRenderer content={message.content} />
        </div>

        {/* Tool calls */}
        {message.toolCalls?.map((call) => (
          <Collapsible key={call.id} className="w-full">
            <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground">
              <Wrench className="h-3 w-3" />
              Used {call.tool}
              <ChevronDown className="h-3 w-3" />
            </CollapsibleTrigger>
            <CollapsibleContent>
              <JSONViewer data={call.result} />
            </CollapsibleContent>
          </Collapsible>
        ))}

        {/* Timestamp */}
        <span className="text-xs text-muted-foreground px-1">
          {format(message.timestamp, 'h:mm a')}
        </span>
      </div>
    </div>
  );
}
```

### 8.3 Agent Configuration Form

```tsx
export function AgentConfigForm({ agent }: { agent: Agent }) {
  const form = useForm({
    resolver: zodResolver(agentConfigSchema),
    defaultValues: agent,
  });

  return (
    <Form {...form}>
      <form className="space-y-8">
        {/* Profile Section */}
        <section>
          <h3 className="text-lg font-semibold mb-4">Profile</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <FormField name="name" label="Agent Name" />
            <FormField name="role" label="Role / Specialty" />
            <FormField name="description" label="Description" className="md:col-span-2" />
          </div>
        </section>

        {/* Knowledge Section */}
        <section>
          <h3 className="text-lg font-semibold mb-4">Knowledge Sources</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Brand Guidelines</Label>
                <p className="text-xs text-muted-foreground">documents/brand-guide.pdf</p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <Label>Campaign History</Label>
                <p className="text-xs text-muted-foreground">All past campaigns</p>
              </div>
              <Switch defaultChecked />
            </div>
            <Button variant="outline" size="sm">
              <Plus className="mr-2 h-4 w-4" /> Add Knowledge Source
            </Button>
          </div>
        </section>

        {/* Tools Section */}
        <section>
          <h3 className="text-lg font-semibold mb-4">Available Tools</h3>
          <div className="grid gap-2">
            {tools.map((tool) => (
              <div key={tool.id} className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <Checkbox id={tool.id} checked={selectedTools.includes(tool.id)} />
                  <Label htmlFor={tool.id}>
                    <div className="font-medium">{tool.name}</div>
                    <p className="text-xs text-muted-foreground">{tool.description}</p>
                  </Label>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Permissions */}
        <section>
          <h3 className="text-lg font-semibold mb-4">Permissions</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Require approval for campaign creation</Label>
                <p className="text-xs text-muted-foreground">Human-in-the-loop approval needed</p>
              </div>
              <Switch />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label>Can access billing data</Label>
              </div>
              <Switch />
            </div>
          </div>
        </section>

        <Button type="submit">Save Configuration</Button>
      </form>
    </Form>
  );
}
```

### 8.4 Agent Memory Browser

```
┌──────────────────────────────────────────────────────────────┐
│  Agent Memory  │  Marketing Strategist                       │
├──────────┬───────────────────────────────────────────────────┤
│          │                                                    │
│  Filters │  Timeline                                          │
│          │                                                    │
│  □ All   │  Today                                             │
│  □ Chat  │   ┌────────────────────────────────────────────┐  │
│  □ Tools │   │ 💬 Chatted with John about campaign budget │  │
│  □ Tasks │   │    Used tools: getBudget(), updateBudget() │  │
│  □ Knowledge│   2:30 PM                                    │  │
│          │   └────────────────────────────────────────────┘  │
│  Search  │   ┌────────────────────────────────────────────┐  │
│  ┌──────┐│   │ 🔍 Searched knowledge base: "summer sale  │  │
│  │      ││   │    2025 performance"                       │  │
│  └──────┘│   │    Results: 3 documents found              │  │
│          │   │   2:15 PM                                   │  │
│          │   └────────────────────────────────────────────┘  │
│          │                                                    │
│          │   Yesterday                                        │
│          │   ┌────────────────────────────────────────────┐  │
│          │   │ 📝 Created campaign draft: "Summer Sale    │  │
│          │   │    2026"                                    │  │
│          │   │   Audience: Warm Leads (1,247 contacts)    │  │
│          │   │   Budget: $5,000                            │  │
│          │   │   11:20 AM                                  │  │
│          │   └────────────────────────────────────────────┘  │
│          │                                                    │
│          │   [Load More...]                                   │
└──────────┴───────────────────────────────────────────────────┘
```

### 8.5 Human-in-the-Loop Approval UI

```tsx
export function ApprovalCard({ request }: { request: ApprovalRequest }) {
  return (
    <Card className="border-l-4 border-l-yellow-500">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            <CardTitle className="text-sm font-medium">
              {request.agentName} requests approval
            </CardTitle>
          </div>
          <Badge variant="warning">Pending Review</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-lg bg-muted p-3 text-sm">
          <p className="font-medium mb-1">{request.action}</p>
          <p className="text-muted-foreground">{request.details}</p>
        </div>
        {/* Changes summary */}
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Campaign Name</span>
            <span className="font-medium">{request.changes.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Budget</span>
            <span className="font-medium">{formatCurrency(request.changes.budget)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Audience</span>
            <span className="font-medium">{request.changes.audience}</span>
          </div>
        </div>
      </CardContent>
      <CardFooter className="gap-2">
        <Button variant="outline" onClick={() => modify(request.id)}>
          <Pencil className="mr-2 h-4 w-4" /> Modify
        </Button>
        <Button variant="destructive" onClick={() => reject(request.id)}>
          <X className="mr-2 h-4 w-4" /> Reject
        </Button>
        <Button onClick={() => approve(request.id)}>
          <Check className="mr-2 h-4 w-4" /> Approve
        </Button>
      </CardFooter>
    </Card>
  );
}
```

---

## 9. Form Patterns

### 9.1 Standard Form (react-hook-form + zod)

**Pattern:**
1. Schema definition with zod
2. Form state with react-hook-form
3. Field components with error display
4. Submit handler with loading state
5. Success/error feedback

```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const contactSchema = z.object({
  firstName: z.string().min(2, 'First name required'),
  lastName: z.string().min(2, 'Last name required'),
  email: z.string().email('Invalid email address'),
  phone: z.string().optional(),
  company: z.string().optional(),
  tags: z.array(z.string()).min(1, 'At least one tag required'),
  notes: z.string().max(500).optional(),
});

type ContactFormValues = z.infer<typeof contactSchema>;

export function ContactForm() {
  const form = useForm<ContactFormValues>({
    resolver: zodResolver(contactSchema),
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      tags: [],
    },
  });

  const { mutate, isPending } = useMutation({
    mutationFn: createContact,
    onSuccess: () => {
      toast.success('Contact created');
      form.reset();
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((data) => mutate(data))} className="space-y-6">
        <div className="grid gap-4 md:grid-cols-2">
          <FormField control={form.control} name="firstName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>First Name</FormLabel>
                <FormControl><Input {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <FormField control={form.control} name="lastName"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Last Name</FormLabel>
                <FormControl><Input {...field} /></FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
        <FormField control={form.control} name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl><Input type="email" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        {/* ... more fields */}
        <Button type="submit" loading={isPending}>
          {isPending ? 'Saving...' : 'Save Contact'}
        </Button>
      </form>
    </Form>
  );
}
```

### 9.2 Multi-Step Wizard

**Pattern:** Stepper + per-step validation + draft saving

```tsx
'use client';

import { useStepper } from '@/components/ui/stepper';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { campaignBasicsSchema, campaignAudienceSchema, campaignBudgetSchema } from './schemas';
import { useAutoSave } from '@/hooks/use-auto-save';

const steps = [
  { id: 'basics', title: 'Campaign Basics', schema: campaignBasicsSchema },
  { id: 'audience', title: 'Target Audience', schema: campaignAudienceSchema },
  { id: 'budget', title: 'Budget & Schedule', schema: campaignBudgetSchema },
  { id: 'review', title: 'Review & Launch', schema: null },
];

export function CampaignWizard() {
  const { currentStep, goTo, goToNext, goToPrev } = useStepper();
  const form = useForm({
    resolver: zodResolver(steps[currentStep].schema),
    mode: 'onChange',
  });

  // Auto-save draft on changes
  useAutoSave(form.watch(), '/api/campaigns/draft');

  const validateAndNext = async () => {
    const valid = await form.trigger();
    if (valid) goToNext();
  };

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <Stepper steps={steps} currentStep={currentStep} onStepClick={(i) => goTo(i)} />
      <Form {...form}>
        <form className="space-y-6">
          {currentStep === 0 && <BasicsStep />}
          {currentStep === 1 && <AudienceStep />}
          {currentStep === 2 && <BudgetStep />}
          {currentStep === 3 && <ReviewStep data={form.getValues()} />}

          <div className="flex justify-between">
            <Button variant="outline" onClick={goToPrev} disabled={currentStep === 0}>
              Previous
            </Button>
            <div className="flex gap-2">
              <Button variant="ghost" onClick={handleSaveDraft}>Save Draft</Button>
              {currentStep < steps.length - 1 ? (
                <Button onClick={validateAndNext}>Next Step</Button>
              ) : (
                <Button type="submit">Launch Campaign</Button>
              )}
            </div>
          </div>
        </form>
      </Form>
    </div>
  );
}
```

### 9.3 Inline Edit

**Pattern:** Click text → Show input → Auto-save on blur/Enter

```tsx
export function InlineEdit({ value, onSave, field, className }: InlineEditProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(value);

  const handleSave = async () => {
    if (editValue !== value) {
      await onSave(editValue);
    }
    setEditing(false);
  };

  if (editing) {
    return (
      <Input
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={handleSave}
        onKeyDown={(e) => {
          if (e.key === 'Enter') handleSave();
          if (e.key === 'Escape') { setEditValue(value); setEditing(false); }
        }}
        autoFocus
        className={className}
      />
    );
  }

  return (
    <div
      className={cn(
        'group flex items-center gap-2 cursor-pointer rounded px-1 -mx-1 hover:bg-accent/50',
        className
      )}
      onClick={() => setEditing(true)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && setEditing(true)}
      aria-label={`Edit ${field}`}
    >
      <span>{value}</span>
      <Pencil className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );
}
```

### 9.4 Dynamic Form (Add/Remove Sections)

```tsx
import { useFieldArray } from 'react-hook-form';

export function DynamicForm() {
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'teamMembers',
  });

  return (
    <div className="space-y-4">
      {fields.map((field, index) => (
        <div key={field.id} className="flex gap-2 items-start">
          <div className="flex-1 grid grid-cols-3 gap-2">
            <Input {...form.register(`teamMembers.${index}.name`)} placeholder="Name" />
            <Input {...form.register(`teamMembers.${index}.email`)} placeholder="Email" />
            <Select {...form.register(`teamMembers.${index}.role`)}>
              <SelectTrigger><SelectValue placeholder="Role" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin</SelectItem>
                <SelectItem value="member">Member</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button variant="ghost" size="icon" onClick={() => remove(index)} aria-label="Remove member">
            <X className="h-4 w-4" />
          </Button>
        </div>
      ))}
      <Button variant="outline" onClick={() => append({ name: '', email: '', role: 'member' })}>
        <Plus className="mr-2 h-4 w-4" /> Add Team Member
      </Button>
    </div>
  );
}
```

### 9.5 AI-Assisted Form

```tsx
export function AIAssistedField({ name, label, control }: FieldProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const handleAIFill = async () => {
    const context = form.getValues();
    const result = await generateFieldSuggestion(name, context);
    form.setValue(name, result.value);
  };

  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <div className="flex items-center justify-between">
            <FormLabel>{label}</FormLabel>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleAIFill}
              className="text-xs text-primary"
            >
              <Sparkles className="mr-1 h-3 w-3" /> AI Fill
            </Button>
          </div>
          <FormControl>
            <Textarea {...field} />
          </FormControl>
          {/* AI suggestions below field */}
          {suggestions.length > 0 && (
            <div className="space-y-1 mt-1">
              {suggestions.map((suggestion, i) => (
                <button
                  key={i}
                  className="flex items-center gap-2 text-xs text-muted-foreground hover:text-primary transition-colors"
                  onClick={() => field.onChange(suggestion)}
                >
                  <Sparkles className="h-3 w-3 shrink-0" />
                  {suggestion}
                </button>
              ))}
            </div>
          )}
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
```

---

## 10. State & Data Loading

### 10.1 Loading Skeletons

Every component must have a skeleton variant for loading states.

```tsx
// Skeleton pattern for any component
export function CardSkeleton() {
  return (
    <Card>
      <CardHeader className="space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </CardHeader>
      <CardContent className="space-y-3">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-3/4" />
        <Skeleton className="h-4 w-full" />
      </CardContent>
    </Card>
  );
}

// Page-level skeletons for each page type
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Welcome banner skeleton */}
      <Skeleton className="h-24 w-full rounded-xl" />
      {/* KPI row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <CardSkeleton key={i} />
        ))}
      </div>
      {/* Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-[300px] w-full rounded-xl" />
        <Skeleton className="h-[300px] w-full rounded-xl" />
      </div>
    </div>
  );
}

export function DataTableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-full" />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}
```

### 10.2 Empty States

Empty states follow a consistent pattern: illustration → message → action.

```tsx
export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-muted p-4 mb-4">
        <Icon className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-6">
        {description}
      </p>
      {action}
    </div>
  );
}

// Usage examples:
<EmptyState
  icon={Users}
  title="No contacts yet"
  description="Add your first contact to start building your CRM."
  action={<Button>+ Add Contact</Button>}
/>

<EmptyState
  icon={BarChart3}
  title="No campaign data"
  description="Campaign performance metrics will appear here once you launch your first campaign."
  action={<Button variant="outline">Create Campaign</Button>}
/>

<EmptyState
  icon={Search}
  title="No results found"
  description="Try adjusting your search or filters."
  action={<Button variant="ghost" onClick={clearFilters}>Clear Filters</Button>}
/>
```

### 10.3 Error States

```tsx
export function ErrorState({
  title = 'Something went wrong',
  description = 'An unexpected error occurred. Please try again.',
  error,
  retry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-destructive/10 p-4 mb-4">
        <AlertCircle className="h-8 w-8 text-destructive" />
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground max-w-sm mb-4">
        {description}
      </p>
      {error && process.env.NODE_ENV === 'development' && (
        <details className="mb-4 max-w-md text-left">
          <summary className="text-xs text-muted-foreground cursor-pointer">Error details</summary>
          <pre className="mt-2 text-xs bg-muted p-2 rounded overflow-auto">
            {error.message}
          </pre>
        </details>
      )}
      {retry && (
        <Button onClick={retry} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" /> Try Again
        </Button>
      )}
    </div>
  );
}

// Per-component error boundaries
export function DataTableErrorBoundary({ retry }: { retry: () => void }) {
  return (
    <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-8 text-center">
      <p className="text-sm text-destructive mb-4">Failed to load data</p>
      <Button variant="outline" size="sm" onClick={retry}>Retry</Button>
    </div>
  );
}
```

### 10.4 Optimistic Updates

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query';

export function useDeleteContact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteContact(id),
    // Optimistic update
    onMutate: async (id) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['contacts'] });
      // Snapshot previous value
      const previous = queryClient.getQueryData(['contacts']);
      // Optimistically remove from cache
      queryClient.setQueryData(['contacts'], (old: Contact[]) =>
        old.filter((c) => c.id !== id)
      );
      return { previous };
    },
    // On error, roll back
    onError: (err, id, context) => {
      queryClient.setQueryData(['contacts'], context?.previous);
      toast.error('Failed to delete contact');
    },
    // Always refetch after mutation
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['contacts'] });
    },
  });
}
```

### 10.5 Offline State

```tsx
'use client';

import { useOnlineStatus } from '@/hooks/use-online-status';

export function OfflineBanner() {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-banner bg-warning text-warning-foreground px-4 py-2 text-center text-sm">
      <WifiOff className="inline-block mr-2 h-4 w-4" />
      You are offline. Changes will be saved locally and synced when you reconnect.
    </div>
  );
}

// PWA detection hook
export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
}
```

---

## 11. AI-Powered UX Patterns

### 11.1 Smart Compose

Inline AI writing assistance for text fields.

```tsx
export function SmartComposeTextarea({ field }: { field: FieldValues }) {
  const [suggestion, setSuggestion] = useState('');

  const handleKeyDown = async (e: React.KeyboardEvent) => {
    if (e.key === 'Tab' && suggestion) {
      e.preventDefault();
      field.onChange(field.value + suggestion);
      setSuggestion('');
    }
  };

  return (
    <div className="relative">
      <Textarea
        {...field}
        onKeyDown={handleKeyDown}
        className="min-h-[120px]"
        placeholder="Start typing or press ⌘+Space for AI assistance..."
      />
      {suggestion && (
        <div className="absolute bottom-3 left-3 text-sm text-muted-foreground/50 pointer-events-none">
          {suggestion}
          <span className="text-xs ml-2">Tab to accept</span>
        </div>
      )}
    </div>
  );
}
```

### 11.2 AI Suggestions Chip

Non-intrusive suggestion cards below content.

```
┌──────────────────────────────────────────────────────┐
│  ...existing content...                               │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ✨ AI Suggestion                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Consider adding a "limited time" element to   │  │
│  │  your subject line for 30% higher open rates.  │  │
│  │  [Apply] [Dismiss]  ✕                          │  │
│  └────────────────────────────────────────────────┘  │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### 11.3 Predictive Search

Typeahead with AI-completed search queries.

```tsx
export function PredictiveSearch({ onSearch }: { onSearch: (query: string) => void }) {
  const [query, setQuery] = useState('');
  const [predictions, setPredictions] = useState<string[]>([]);

  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    if (debouncedQuery.length > 2) {
      getSearchPredictions(debouncedQuery).then(setPredictions);
    }
  }, [debouncedQuery]);

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="pl-10"
        placeholder="Search campaigns, contacts, or anything..."
      />
      {predictions.length > 0 && (
        <Card className="absolute top-full mt-1 w-full z-50">
          {predictions.map((prediction, i) => (
            <button
              key={i}
              className="w-full text-left px-3 py-2 text-sm hover:bg-accent flex items-center gap-2"
              onClick={() => { setQuery(prediction); onSearch(prediction); }}
            >
              <Search className="h-3 w-3 text-muted-foreground" />
              {prediction}
            </button>
          ))}
        </Card>
      )}
    </div>
  );
}
```

### 11.4 One-Click Automation Suggestions

```
┌──────────────────────────────────────────────────────────────┐
│  Repeat Task Detected                                         │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  🔄 You've sent 5 weekly reports manually this month.   ││
│  │  Would you like me to automate this?                     ││
│  │                                                          ││
│  │  [Automate It →]  [Not Now]  [Don't Show Again]         ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 11.5 Auto-Generated Summaries

```tsx
export function AISummary({ content, type }: { content: string; type: 'campaign' | 'customer' | 'analytics' }) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    generateSummary(content, type)
      .then(setSummary)
      .finally(() => setLoading(false));
  }, [content, type]);

  if (loading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-4 w-1/2" />
      </div>
    );
  }

  return (
    <div className="rounded-lg bg-primary/5 border border-primary/20 p-4">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-4 w-4 text-primary" />
        <span className="text-xs font-medium text-primary">AI Summary</span>
      </div>
      <p className="text-sm text-muted-foreground">{summary}</p>
    </div>
  );
}
```

---

## 12. Workspace & Multi-tenant UI

### 12.1 Workspace Creation Flow

```tsx
// Multi-step wizard for workspace creation
export function CreateWorkspaceWizard() {
  return (
    <div className="mx-auto max-w-lg space-y-8 py-12">
      <div className="text-center">
        <Building2 className="h-12 w-12 mx-auto text-primary mb-4" />
        <h1 className="text-2xl font-bold">Create Your Workspace</h1>
        <p className="text-muted-foreground mt-2">
          A workspace is where you and your team manage marketing campaigns.
        </p>
      </div>
      <Card>
        <CardContent className="pt-6 space-y-4">
          <FormField label="Workspace Name" placeholder="Acme Marketing">
            <Input />
          </FormField>
          <FormField label="Industry" type="select">
            <Select>
              <SelectTrigger><SelectValue placeholder="Select industry" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="tech">Technology</SelectItem>
                <SelectItem value="ecommerce">E-commerce</SelectItem>
                <SelectItem value="agency">Agency</SelectItem>
                <SelectItem value="finance">Finance</SelectItem>
                <SelectItem value="healthcare">Healthcare</SelectItem>
              </SelectContent>
            </Select>
          </FormField>
          <FormField label="Team Size">
            <RadioGroup defaultValue="1-5">
              <div className="flex gap-2">
                <RadioOption value="1-5" label="1-5" />
                <RadioOption value="5-20" label="5-20" />
                <RadioOption value="20-50" label="20-50" />
                <RadioOption value="50+" label="50+" />
              </div>
            </RadioGroup>
          </FormField>
          <div className="flex items-center space-x-2">
            <Checkbox id="white-label" />
            <Label htmlFor="white-label">Enable white-label mode (hide AMC branding)</Label>
          </div>
        </CardContent>
      </Card>
      <div className="flex justify-between">
        <Button variant="ghost" onClick={() => router.back()}>Back</Button>
        <Button onClick={handleCreate}>Create Workspace</Button>
      </div>
    </div>
  );
}
```

### 12.2 Workspace Switcher

See [Section 6.2](#62-workspace-switcher) for implementation.

### 12.3 Workspace Settings

```
┌──────────────────────────────────────────────────────────────┐
│  Settings  >  Workspace                                      │
├───────────────┬──────────────────────────────────────────────┤
│  General      │  Workspace Settings                          │
│  Workspace    │  ┌────────────────────────────────────────┐  │
│  Team         │  │  Workspace Name: [Acme Corp      ]     │  │
│  Billing      │  │  Slug: acme-corp                        │  │
│  API Keys     │  │  Industry: [Marketing ▼]               │  │
│  Appearance   │  │  Timezone: [(UTC-5) Eastern ▼]         │  │
│               │  └────────────────────────────────────────┘  │
│               │                                              │
│               │  Danger Zone                                 │
│               │  ┌────────────────────────────────────────┐  │
│               │  │  Delete Workspace                      │  │
│               │  │  This action is irreversible.          │  │
│               │  │  [Delete Workspace]                    │  │
│               │  └────────────────────────────────────────┘  │
│               │                                              │
│               │  [Save Changes]                               │
└───────────────┴──────────────────────────────────────────────┘
```

### 12.4 User Invitation Flow

```tsx
export function InviteUsersDialog() {
  const [emails, setEmails] = useState<string[]>(['']);
  const [role, setRole] = useState('member');

  return (
    <Dialog>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Invite Team Members</DialogTitle>
          <DialogDescription>
            Send invitations to join your workspace
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Email Addresses</Label>
            {emails.map((email, index) => (
              <div key={index} className="flex gap-2">
                <Input
                  value={email}
                  onChange={(e) => {
                    const next = [...emails];
                    next[index] = e.target.value;
                    setEmails(next);
                  }}
                  placeholder="colleague@company.com"
                  type="email"
                />
                {emails.length > 1 && (
                  <Button variant="ghost" size="icon" onClick={() => setEmails(emails.filter((_, i) => i !== index))}>
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <Button variant="link" size="sm" onClick={() => setEmails([...emails, ''])}>
              + Add another email
            </Button>
          </div>
          <div className="space-y-2">
            <Label>Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">Admin — Full access</SelectItem>
                <SelectItem value="member">Member — Standard access</SelectItem>
                <SelectItem value="viewer">Viewer — Read only</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline">Cancel</Button>
          <Button onClick={handleInvite}>
            <Send className="mr-2 h-4 w-4" /> Send Invitations
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### 12.5 Team Management UI

```
┌──────────────────────────────────────────────────────────────┐
│  Team Management                          [+ Invite Member]  │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────┐  │
│  │  👤  John Doe            john@acme.com     Admin       │  │
│  │      Joined Jan 2026                       [▼ Actions] │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  👤  Jane Smith          jane@acme.com     Member      │  │
│  │      Joined Mar 2026                       [▼ Actions] │  │
│  ├────────────────────────────────────────────────────────┤  │
│  │  👤  Bob Wilson          bob@client.net    Viewer      │  │
│  │      Pending Invitation                    [▼ Actions] │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Role descriptions:                                          │
│  ● Admin — Full workspace access, billing, team management   │
│  ● Member — Create and edit campaigns, contacts, reports     │
│  ● Viewer — Read-only access to all workspace data           │
└──────────────────────────────────────────────────────────────┘
```

### 12.6 Billing & Plan UI

```
┌──────────────────────────────────────────────────────────────┐
│  Billing & Plan                                              │
├──────────────────────────────────────────────────────────────┤
│  Current Plan: Professional                                  │
│  $49/month · Billed monthly · Next billing: July 1, 2026    │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Starter  │ │  Pro     │ │ Business │ │  Enterp. │       │
│  │ $19/mo   │ │  $49/mo  │ │ $149/mo  │ │  Custom  │       │
│  │          │ │          │ │          │ │          │       │
│  │ 1 user   │ │ 5 users  │ │ 25 users │ │ Unlimited│       │
│  │ 10K cont │ │ 50K cont │ │ 500K cont│ │ Unlimited│       │
│  │ Basic AI │ │ Adv AI   │ │ AI Agents│ │ White-label│     │
│  │          │ │          │ │          │ │          │       │
│  │ [Current]│ │ [Active] │ │ [Upgrade]│ │ [Contact]│       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  Usage This Month                                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Contacts: 12,847 / 50,000    ████████░░░░  25%      │  │
│  │  AI Calls: 847 / 5,000        ████░░░░░░░░  17%      │  │
│  │  Storage: 2.3 GB / 25 GB      █░░░░░░░░░░░  9%       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  [Change Plan]  [View Invoice History]  [Update Payment]     │
└──────────────────────────────────────────────────────────────┘
```

---

## 13. PWA & Offline Features

### 13.1 Service Worker Registration

```typescript
// app/sw.ts — Next.js App Router service worker
/// <reference lib="webworker" />

const CACHE_NAME = 'amc-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
];

// Install — cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activate — clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch — stale-while-revalidate strategy
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // API requests — network first, fallback to cache
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Static assets — cache first
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
```

### 13.2 Offline Fallback Page

```tsx
// app/offline/page.tsx
export default function OfflinePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8 text-center">
      <WifiOff className="h-16 w-16 text-muted-foreground mb-6" />
      <h1 className="text-2xl font-bold mb-2">You're Offline</h1>
      <p className="text-muted-foreground max-w-md mb-8">
        Aegis Marketing Cloud is cached for offline use. You can still view
        your dashboard and previously loaded data.
      </p>
      <div className="space-y-2">
        <Button onClick={() => window.location.reload()}>
          <RefreshCw className="mr-2 h-4 w-4" /> Try Again
        </Button>
        <p className="text-xs text-muted-foreground">
          Changes will sync automatically when you reconnect
        </p>
      </div>
    </div>
  );
}
```

### 13.3 Background Sync

```typescript
// Register background sync for offline mutations
export function useBackgroundSync() {
  const queue = useRef<OfflineMutation[]>([]);

  const addToQueue = useCallback(async (mutation: OfflineMutation) => {
    queue.current.push(mutation);
    // Store in IndexedDB for persistence
    await idb.set('mutation-queue', queue.current);

    // Register background sync if available
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      const registration = await navigator.serviceWorker.ready;
      await registration.sync.register('sync-mutations');
    }
  }, []);

  return { addToQueue };
}
```

### 13.4 Push Notification Permission Flow

```tsx
export function PushNotificationPrompt() {
  const [dismissed, setDismissed] = useState(() => localStorage.getItem('push-dismissed'));

  const handleEnable = async () => {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      // Register push subscription
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: VAPID_PUBLIC_KEY,
      });
      await fetch('/api/notifications/subscribe', {
        method: 'POST',
        body: JSON.stringify(subscription),
      });
    }
    setDismissed('true');
    localStorage.setItem('push-dismissed', 'true');
  };

  if (dismissed || Notification.permission === 'granted') return null;

  return (
    <Card className="fixed bottom-4 right-4 w-80 z-toast shadow-2xl">
      <CardContent className="pt-6 space-y-3">
        <div className="flex items-center gap-2">
          <Bell className="h-5 w-5 text-primary" />
          <h4 className="font-semibold">Stay Updated</h4>
        </div>
        <p className="text-sm text-muted-foreground">
          Get notified when campaigns launch, reports are ready, or AI needs your input.
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => { setDismissed('true'); localStorage.setItem('push-dismissed', 'true'); }}>
            Not Now
          </Button>
          <Button size="sm" onClick={handleEnable}>
            Enable Notifications
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 13.5 Install Prompt

```tsx
export function InstallPWA() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', handler);
    window.addEventListener('appinstalled', () => setInstalled(true));
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  if (!deferredPrompt || installed) return null;

  return (
    <Card className="fixed bottom-4 left-4 w-72 z-toast shadow-2xl">
      <CardContent className="pt-6 space-y-3">
        <div className="flex items-center gap-2">
          <Download className="h-5 w-5 text-primary" />
          <h4 className="font-semibold">Install AMC</h4>
        </div>
        <p className="text-sm text-muted-foreground">
          Install Aegis Marketing Cloud for the best experience.
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setDeferredPrompt(null)}>
            Dismiss
          </Button>
          <Button size="sm" onClick={async () => {
            deferredPrompt.prompt();
            const result = await deferredPrompt.userChoice;
            if (result.outcome === 'accepted') setInstalled(true);
            setDeferredPrompt(null);
          }}>
            Install
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

### 13.6 Manifest Configuration

```json
{
  "name": "Aegis Marketing Cloud",
  "short_name": "AMC",
  "description": "AI-Native Digital Marketing Operating System",
  "start_url": "/dashboard",
  "display": "standalone",
  "background_color": "#FFFFFF",
  "theme_color": "#3B82F6",
  "orientation": "any",
  "categories": ["business", "productivity", "marketing"],
  "icons": [
    { "src": "/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-192x192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/icons/icon-512x512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "screenshots": [
    {
      "src": "/screenshots/dashboard.png",
      "sizes": "1280x800",
      "type": "image/png",
      "form_factor": "wide"
    },
    {
      "src": "/screenshots/mobile-dashboard.png",
      "sizes": "390x844",
      "type": "image/png",
      "form_factor": "narrow"
    }
  ],
  "shortcuts": [
    {
      "name": "New Campaign",
      "short_name": "New Campaign",
      "description": "Create a new marketing campaign",
      "url": "/campaigns/new",
      "icons": [{ "src": "/icons/shortcut-campaign.png", "sizes": "96x96" }]
    },
    {
      "name": "AI Agents",
      "short_name": "AI Agents",
      "description": "Chat with AI agents",
      "url": "/agents",
      "icons": [{ "src": "/icons/shortcut-ai.png", "sizes": "96x96" }]
    }
  ]
}
```

---

## 14. Theming & White-label

### 14.1 Dark/Light Mode

System preference + manual toggle with persistence.

```tsx
'use client';

import { useTheme } from 'next-themes';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Toggle theme">
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>
          <Sun className="mr-2 h-4 w-4" /> Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          <Moon className="mr-2 h-4 w-4" /> Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>
          <Monitor className="mr-2 h-4 w-4" /> System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

### 14.2 Custom Branding (Per-Workspace)

```typescript
// lib/workspace-branding.ts
export interface WorkspaceBranding {
  logo: string;            // URL to custom logo
  favicon: string;         // URL to custom favicon
  primaryColor: string;    // Hex color override
  secondaryColor: string;  // Hex color override
  hideAegisBranding: boolean; // White-label mode
  customDomain?: string;   // Custom domain for white-label
}

// app/layout.tsx — dynamic CSS variable injection
export function BrandingProvider({ children }: { children: React.ReactNode }) {
  const { workspace } = useWorkspace();
  const branding = workspace?.branding;

  useEffect(() => {
    if (branding) {
      document.documentElement.style.setProperty('--color-primary-500', branding.primaryColor);
      document.documentElement.style.setProperty('--color-secondary-500', branding.secondaryColor);
      if (branding.favicon) {
        const link = document.querySelector("link[rel*='icon']") as HTMLLinkElement;
        link.href = branding.favicon;
      }
    }
  }, [branding]);

  // White-label: hide AMC references
  const context = useMemo(() => ({
    hideBranding: branding?.hideAegisBranding ?? false,
  }), [branding]);

  return (
    <BrandingContext.Provider value={context}>
      {children}
    </BrandingContext.Provider>
  );
}
```

### 14.3 CSS Variable-Based Theming

```css
/* styles/themes.css */
:root {
  /* Light theme (default) */
  --color-bg-primary: #FAFAFA;
  --color-bg-secondary: #F5F5F5;
  --color-bg-tertiary: #E5E5E5;
  --color-text-primary: #171717;
  --color-text-secondary: #737373;
  --color-border: #E5E5E5;
  /* ... */
}

.dark {
  --color-bg-primary: #0A0A0A;
  --color-bg-secondary: #171717;
  --color-bg-tertiary: #262626;
  --color-text-primary: #FAFAFA;
  --color-text-secondary: #A3A3A3;
  --color-border: #404040;
  /* ... */
}

/* Workspace-specific branding injected via inline styles */
[data-branding] {
  --color-primary-500: var(--branding-primary);
  --color-secondary-500: var(--branding-secondary);
}
```

### 14.4 White-Label Mode

When white-label is enabled:

- AMC logo → workspace's custom logo
- "Powered by Aegis" → hidden
- Footer branding → hidden
- Default favicon → workspace favicon
- Login page → workspace branded
- Email notifications → workspace name, not AMC

```tsx
export function Logo() {
  const { hideBranding } = useBranding();
  const workspace = useWorkspace();

  if (hideBranding && workspace.branding?.logo) {
    return <Image src={workspace.branding.logo} alt={workspace.name} />;
  }

  return (
    <div className="flex items-center gap-2">
      <Shield className="h-6 w-6 text-primary" />
      <span className="font-semibold">Aegis MC</span>
    </div>
  );
}
```

---

## 15. Accessibility Checklist

### 15.1 Keyboard Navigation

| Pattern | Key | Behavior |
|---------|-----|----------|
| **Tab navigation** | Tab | Move focus to next focusable element |
| **Shift+Tab** | Shift+Tab | Move focus to previous focusable element |
| **Buttons/Links** | Enter/Space | Activate |
| **Select/Dropdown** | Arrow keys | Navigate options |
| **Select/Dropdown** | Enter/Space | Select option |
| **Modal/Dialog** | Escape | Close |
| **Sheet/Drawer** | Escape | Close |
| **Popover** | Escape | Close |
| **Tabs** | Arrow keys | Switch between tabs |
| **Radio group** | Arrow keys | Switch between options |
| **Checkbox** | Space | Toggle |
| **Switch** | Space | Toggle |
| **Accordion** | Enter/Space | Toggle section |
| **Command palette** | Escape | Close |
| **Data table** | Arrow keys | Navigate rows/cells |
| **Data table** | Space | Select row |
| **Data table** | Shift+Click | Range select |
| **Slider** | Arrow keys | Increment/decrement |
| **Slider** | Home/End | Min/Max |

### 15.2 Focus Management

```tsx
// Focus trap for modals (Radix handles this automatically)
// Custom focus management for dynamic content:

import { useCallback, useRef } from 'react';

export function useFocusTrap(active: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!active) return;
    const container = containerRef.current;
    if (!container) return;

    const focusableElements = container.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const first = focusableElements[0];
    const last = focusableElements[focusableElements.length - 1];

    first?.focus();

    const handleTab = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    container.addEventListener('keydown', handleTab);
    return () => container.removeEventListener('keydown', handleTab);
  }, [active]);

  return containerRef;
}
```

### 15.3 ARIA Labels

| Component | ARIA Attributes | Notes |
|-----------|----------------|-------|
| Button | `aria-label` for icon-only buttons | Required |
| Input | `aria-invalid`, `aria-describedby` | Connect to error message |
| Dialog | `aria-modal="true"`, `aria-labelledby`, `aria-describedby` | Required |
| Tab | `role="tab"`, `aria-selected`, `aria-controls` | Required |
| TabPanel | `role="tabpanel"`, `aria-labelledby` | Required |
| Alert | `role="alert"` | For dynamic alerts |
| Status | `role="status"` | For live regions |
| Progress | `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax` | Required |
| Tooltip | `role="tooltip"` | Plus `aria-describedby` on trigger |
| Switch | `role="switch"`, `aria-checked` | Required |
| Menu | `role="menu"`, `aria-orientation` | Required |
| MenuItem | `role="menuitem"` | Required |
| Navigation | `role="navigation"` or `<nav>` | Landmark |
| Main | `<main>` or `role="main"` | Landmark |
| Banner | `<header>` or `role="banner"` | Landmark |
| Complementary | `<aside>` or `role="complementary"` | Landmark |
| DataTable | `<table>` with `<caption>` | Caption required for screen readers |

### 15.4 Screen Reader Announcements

```tsx
// Live region for dynamic announcements
export function ScreenReaderAnnouncement({ message, priority = 'polite' }: {
  message: string;
  priority?: 'polite' | 'assertive';
}) {
  return (
    <div
      role="status"
      aria-live={priority}
      aria-atomic="true"
      className="sr-only"
    >
      {message}
    </div>
  );
}

// Usage in data loading
<ScreenReaderAnnouncement message={`Loaded ${count} contacts`} />

// Usage in form submission
<ScreenReaderAnnouncement
  message="Campaign created successfully"
  priority="assertive"
/>
```

### 15.5 Color Contrast Ratios

| Token Pair | Ratio | WCAG Level | Status |
|-----------|-------|-----------|--------|
| `text-primary` on `bg-primary` | 15:1 | AAA ✅ | Pass |
| `text-secondary` on `bg-primary` | 7:1 | AAA ✅ | Pass |
| `text-primary` on `bg-secondary` | 14:1 | AAA ✅ | Pass |
| `text-muted` on `bg-primary` | 4.5:1 | AA ✅ | Pass |
| **Primary 500** (blue bg) on white text | 4.6:1 | AA ✅ | Pass |
| **Primary 600** on white text | 5.5:1 | AAA ✅ | Pass |
| **Success 500** on white text | 4.5:1 | AA ✅ | Pass |
| **Warning 400** on dark text | 4.5:1 | AA ✅ | Pass |
| **Error 500** on white text | 4.5:1 | AA ✅ | Pass |
| Focus ring (primary 500) on any bg | 3:1 min | AA (1.4.11) ✅ | Pass |

**Color combinations to avoid:**
- Red/Green pair for status (use icons + text for colorblind users)
- Blue/Purple pair for data viz (use patterns + labels)
- Low-contrast text on image backgrounds

### 15.6 Reduced Motion Support

```css
/* Global reduced motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}

/* Opt-in animations for specific components */
@media (prefers-reduced-motion: no-preference) {
  .slide-in {
    animation: slideIn 0.3s var(--ease-out);
  }
  .fade-in {
    animation: fadeIn 0.2s var(--ease-out);
  }
}
```

**Accessibility testing checklist (run per sprint):**

```typescript
// a11y-testing.ts
export const a11yChecklist = [
  // Automated
  'axe-core scan on all pages — zero critical violations',
  'Color contrast check — all text passes 4.5:1',
  'Alt text on all images — no missing alt attributes',
  'Form labels — all inputs have associated labels',
  'ARIA attributes — no invalid or missing required attributes',

  // Manual
  'Full keyboard navigation — all features reachable with Tab',
  'Focus indicators visible — 2px ring on all interactive elements',
  'Screen reader test — navigate a complete workflow with NVDA/VoiceOver',
  'Zoom to 200% — no content cutoff or horizontal scroll',
  'Reduced motion — no jarring animations',

  // Devices
  'Touch targets — minimum 44x44px',
  'Voice control — all actions available via voice',
];
```

---

## 16. Performance Guidelines

### 16.1 Bundle Size Budgets

Per-route JavaScript bundle budgets (gzipped):

| Route | Budget | Current | Status |
|-------|--------|---------|--------|
| `/login` | 80 KB | — | Target |
| `/dashboard` | 150 KB | — | Target |
| `/campaigns` | 160 KB | — | Target |
| `/campaigns/[id]` | 180 KB | — | Target |
| `/campaigns/new` | 200 KB | — | Target |
| `/crm` | 160 KB | — | Target |
| `/crm/[id]` | 170 KB | — | Target |
| `/agents` | 120 KB | — | Target |
| `/agents/[id]` | 140 KB | — | Target |
| `/analytics` | 250 KB | — | Target |
| `/settings` | 100 KB | — | Target |
| `/marketplace` | 180 KB | — | Target |
| `/seo` | 150 KB | — | Target |
| `/social` | 150 KB | — | Target |
| `/knowledge` | 130 KB | — | Target |
| `/automation` | 200 KB | — | Target |

**Thresholds:**
- ⚠️ Warning: +10% over budget
- 🚫 Blocking: +20% over budget (CI fails)

### 16.2 Image Optimization Strategy

```tsx
import Image from 'next/image';

// Use next/image for all images
<Image
  src="/campaigns/summer-sale-banner.jpg"
  alt="Summer Sale Campaign Banner"
  width={1200}
  height={630}
  priority={isAboveTheFold}
  placeholder="blur"
  blurDataURL="data:image/webp;base64,..."
/>

// Responsive images with srcSet
<Image
  src="/hero.jpg"
  alt="Dashboard preview"
  sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
  fill
  className="object-cover"
/>

// Lazy loading is default — below-fold images load on scroll
// Use `priority` for above-fold images
```

**Image format priorities:**
1. **WebP** — primary format (smaller than PNG/JPEG at same quality)
2. **AVIF** — where supported (20% smaller than WebP)
3. **JPEG** — fallback for older browsers
4. **PNG** — only for images requiring transparency

**CDN optimization:**
- Serve images from CDN with query-based transformations
- `?w=480&q=75` — resize to 480px width at 75% quality
- `?format=webp` — auto-convert to WebP

### 16.3 Code Splitting

**Route-based splitting (Next.js App Router — automatic):**

```typescript
// app/dashboard/page.tsx — automatically code-split from app/campaigns/page.tsx
// Each route gets its own JS chunk
```

**Component-based splitting (dynamic imports):**

```tsx
import dynamic from 'next/dynamic';

// Heavy analytics chart — only loads when needed
const RevenueChart = dynamic(() => import('@/components/charts/revenue-chart'), {
  loading: () => <Skeleton className="h-[300px] w-full" />,
  ssr: false, // Client-only rendering for chart libraries
});

// Markdown editor — large library, load on demand
const MDEditor = dynamic(() => import('@uiw/react-md-editor'), {
  loading: () => <Skeleton className="h-[400px] w-full" />,
});

// Conditional rendering
export function CampaignDetail({ campaign }) {
  return (
    <>
      <CampaignOverview />
      {campaign.hasAnalytics && <RevenueChart data={campaign.analytics} />}
    </>
  );
}
```

### 16.4 Server Components vs Client Components

**Server Components (default in App Router):**

```tsx
// THIS IS A SERVER COMPONENT — no 'use client' directive
// Runs on server only, zero JS sent to client
export default async function CampaignPage() {
  const campaigns = await db.campaigns.findMany({
    where: { workspaceId: getWorkspaceId() },
    take: 25,
  });

  return (
    <div>
      <h1>Campaigns</h1>
      <CampaignList campaigns={campaigns} />
      {/* CampaignList can be a Client Component */}
    </div>
  );
}
```

**Client Components (when you need interactivity):**

```tsx
'use client';

// Only use 'use client' when you need:
// 1. State (useState, useReducer)
// 2. Effects (useEffect)
// 3. Event handlers (onClick, onChange)
// 4. Browser-only APIs
// 5. Custom hooks that use the above
// 6. Context providers

export function CampaignForm() { /* ... */ }
```

**Decision guide:**

| Need | Use |
|------|-----|
| Fetch data, render static content | Server Component ✅ |
| Form with validation | Client Component (react-hook-form) |
| Interactive charts | Client Component (recharts) |
| Static page metadata | Server Component ✅ |
| Navigation, sidebar state | Client Component |
| Data fetching with loading states | Server Component + Client data-fetching |
| Heavy computation | Server Component (run on server) |

### 16.5 Data Fetching Patterns

```typescript
// Server-side fetch (no loading state needed)
async function getDashboardData() {
  const res = await fetch('http://api/dashboard', { next: { revalidate: 60 } });
  return res.json();
}

// React Query for client-side data with caching
'use client';

export function useCampaigns(page: number, filters: Filters) {
  return useQuery({
    queryKey: ['campaigns', page, filters],
    queryFn: () => fetchCampaigns({ page, filters }),
    staleTime: 30_000,        // 30s before refetch
    gcTime: 5 * 60 * 1000,    // Keep in cache 5 min
    refetchOnWindowFocus: true,
    placeholderData: keepPreviousData, // Keep old data while loading next page
  });
}

// Infinite queries for paginated data
export function useInfiniteContacts() {
  return useInfiniteQuery({
    queryKey: ['contacts'],
    queryFn: ({ pageParam = 0 }) => fetchContacts({ offset: pageParam, limit: 25 }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.nextOffset ?? null,
  });
}

// Mutation with optimistic updates
export function useCreateCampaign() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CampaignInput) => fetch('/api/campaigns', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Campaign created');
    },
  });
}
```

### 16.6 Memoization Strategy

```tsx
// React.memo — prevent re-renders when props haven't changed
export const CampaignCard = React.memo(function CampaignCard({ campaign }: {
  campaign: Campaign
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{campaign.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p>{campaign.description}</p>
      </CardContent>
    </Card>
  );
});

// useMemo — expensive computations
function DashboardMetrics({ campaigns }: { campaigns: Campaign[] }) {
  const totals = useMemo(() => ({
    totalImpressions: campaigns.reduce((sum, c) => sum + c.impressions, 0),
    totalClicks: campaigns.reduce((sum, c) => sum + c.clicks, 0),
    averageCTR: campaigns.length > 0
      ? campaigns.reduce((sum, c) => sum + c.ctr, 0) / campaigns.length
      : 0,
  }), [campaigns]);

  return <StatCards data={totals} />;
}

// useCallback — stable function references
function CampaignList() {
  const queryClient = useQueryClient();

  const handleDelete = useCallback(async (id: string) => {
    await deleteCampaign(id);
    queryClient.invalidateQueries({ queryKey: ['campaigns'] });
  }, [queryClient]);

  return <CampaignCards onDelete={handleDelete} />;
}

// When NOT to memoize:
// 1. Simple JSX without expensive computations
// 2. Components that always re-render anyway
// 3. Props that are always different (objects/arrays created in render)
```

**Memoization decision matrix:**

| Scenario | Memoize? | Technique |
|----------|---------|-----------|
| Pure component, same props | ✅ | `React.memo` |
| Expensive computation (>1ms) | ✅ | `useMemo` |
| Callback passed to child | ✅ | `useCallback` |
| Simple div with static content | ❌ | Nothing |
| Props always new objects | ❌ | Fix at source |
| Component renders once | ❌ | Nothing |

---

## 17. Visual Mockups (Text-Based)

### 17.1 Login/Register Page

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                   │
│                    ┌─────────────────────────┐                    │
│                    │                         │                    │
│                    │    🛡️ Aegis MC          │                    │
│                    │   Marketing Cloud       │                    │
│                    │                         │                    │
│                    │  ┌───────────────────┐  │                    │
│                    │  │ Email             │  │                    │
│                    │  │ [user@company.co] │  │                    │
│                    │  └───────────────────┘  │                    │
│                    │                         │                    │
│                    │  ┌───────────────────┐  │                    │
│                    │  │ Password          │  │                    │
│                    │  │ [••••••••••••]    │  │                    │
│                    │  └───────────────────┘  │                    │
│                    │                         │                    │
│                    │  □ Remember me          │                    │
│                    │                         │                    │
│                    │  ┌───────────────────┐  │                    │
│                    │  │   Sign In         │  │                    │
│                    │  └───────────────────┘  │                    │
│                    │                         │                    │
│                    │  Forgot password?        │                    │
│                    │                         │                    │
│                    │  ──── or continue with ────                 │
│                    │                         │                    │
│                    │  [ Google ] [ GitHub ]  │                    │
│                    │                         │                    │
│                    │  Don't have an account?  │                    │
│                    │     Create one →         │                    │
│                    │                         │                    │
│                    └─────────────────────────┘                    │
│                                                                   │
│                    © 2026 Aegis Marketing Cloud                   │
└─────────────────────────────────────────────────────────────────┘
```

### 17.2 Main App Shell with Sidebar

```
┌─────────────────────────────────────────────────────────────────┐
│  ┌────────────┬──────────────────────────────────────────────┐  │
│  │ 🔍 Search  │  🏠 Dashboard  ›  Overview                   │  │
│  │ ⌘K         │              🔔 3  ⚙️  👤 John ▼             │  │
│  ├────────────┼──────────────────────────────────────────────┤  │
│  │            │                                              │  │
│  │ 📊 CRM     │  ┌──────────────────────────────────────┐   │  │
│  │ 📧 Email   │  │  Say hi to your AI Marketing         │   │  │
│  │ 🤖 AI      │  │  Assistant! 🎉                       │   │  │
│  │ 📈 Anal.   │  └──────────────────────────────────────┘   │  │
│  │ 🔍 SEO     │                                              │  │
│  │ 📱 Social  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │  │
│  │ 🔄 Auto.   │  │Revenue│ │Leads │ │Conv. │ │ROAS  │       │  │
│  │ 📚 Know.   │  │$124K  │ │1,892 │ │3.09% │ │4.2x  │       │  │
│  │ 🏪 Market  │  │↑12%   │ │↑8%   │ │↑2%   │ │↓1%   │       │  │
│  │ ⚙️ Settings│  └──────┘ └──────┘ └──────┘ └──────┘       │  │
│  │            │                                              │  │
│  │ ────────   │  ┌──────────────────┐ ┌──────────────────┐  │  │
│  │ 👤 John    │  │ Revenue Chart    │ │ Channel Breakd.  │  │  │
│  │    Acme    │  │ (line chart)     │ │ (pie chart)      │  │  │
│  └────────────┘  └──────────────────┘ └──────────────────┘  │  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 17.3 CRM Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  CRM                                                             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌────────────────────┐   │
│  │Total │ │Active│ │Leads │ │Deals │ │ [+ Add Contact]   │   │
│  │2,847 │ │1,892 │ │  847 │ │$124K │ │ [Import] [Export] │   │
│  └──────┘ └──────┘ └──────┘ └──────┘ └────────────────────┘   │
│                                                                  │
│  Pipeline View                                        [List ▼] │
│  ┌──────────┬──────────┬──────────┬──────────┐                  │
│  │ Lead     │Qualified │Proposal │Closed    │                  │
│  │ 342      │ 215      │ 178      │ 112      │                  │
│  ├──────────┼──────────┼──────────┼──────────┤                  │
│  │ Card 1   │ Card 1   │ Card 1   │ Card 1   │                  │
│  │ Card 2   │ Card 2   │ Card 2   │ Card 2   │                  │
│  │ Card 3   │ Card 3   │          │          │                  │
│  └──────────┴──────────┴──────────┴──────────┘                  │
│                                                                  │
│  Recent Activity                               View All →       │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ ● Jane Smith — Email opened — 2 min ago               │     │
│  │ ● Acme Corp — Deal moved to Proposal — 15 min ago     │     │
│  │ ● Bob Wilson — New lead added — 1 hour ago            │     │
│  │ ● Sarah Lee — Email clicked — 2 hours ago             │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 17.4 Campaign Builder Wizard

```
┌─────────────────────────────────────────────────────────────────┐
│  Create Campaign                                                 │
│                                                                  │
│  Step 1 of 4: Campaign Basics                                    │
│  ┌──────┬──────┬──────┬──────┐                                   │
│  │ ●    │ ○    │ ○    │ ○    │                                   │
│  │Basic │Audience│Content│Review│                                │
│  └──────┴──────┴──────┴──────┘                                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Campaign Name                                         │     │
│  │  [Summer Sale 2026                                ]    │     │
│  │                                                        │     │
│  │  Channel                                               │     │
│  │  ○ Email   ● Both (Email + Social)   ○ Social Only     │     │
│  │                                                        │     │
│  │  Description                                           │     │
│  │  [Promote our summer collection with exclusive    ]    │     │
│  │  [discounts and limited-time offers.              ]    │     │
│  │                                                        │     │
│  │  ✨ AI Suggestion                                      │     │
│  │  ┌────────────────────────────────────────────────┐   │     │
│  │  │  Consider targeting "warm leads" for 40%       │   │     │
│  │  │  higher conversion rate.                       │   │     │
│  │  │  [Apply] [Dismiss]                             │   │     │
│  │  └────────────────────────────────────────────────┘   │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  [Save Draft]                              [Next Step  →]       │
└─────────────────────────────────────────────────────────────────┘
```

### 17.5 AI Agent Chat Interface

```
┌─────────────────────────────────────────────────────────────────┐
│  AI Agents                              Marketing Strategist ▼  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  🤖 Marketing Strategist    ● Online                    │     │
│  │  I'm your AI marketing strategist. I can help you      │     │
│  │  create campaigns, analyze performance, and optimize   │     │
│  │  your marketing strategy.                              │     │
│  │                                                        │     │
│  │  How can I help you today?                              │     │
│  │  10:32 AM                                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Create a summer sale campaign for our warm leads      │     │
│  │  10:33 AM                                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  🤖 I'll help you build that! Here's my plan:          │     │
│  │                                                        │     │
│  │  ✓ Analyzed past summer campaigns (3 found)            │     │
│  │  ✓ Identified warm lead segment (1,247 contacts)       │     │
│  │  ⏳ Drafting email copy...                             │     │
│  │  ⏳ Selecting social creative assets...                 │     │
│  │                                                        │     │
│  │  Here's what I recommend:                              │     │
│  │  ┌────────────────────────────────────────────────┐   │     │
│  │  │ Campaign: Summer Sale 2026                     │   │     │
│  │  │ Channel: Email + Instagram + Facebook          │   │     │
│  │  │ Budget: $5,000                                 │   │     │
│  │  │ Timeline: Jul 1 – Jul 15                       │   │     │
│  │  │ Target: Warm leads (1,247) + Lookalike (5K)   │   │     │
│  │  │ Offer: 20% off, free shipping over $50         │   │     │
│  │  └────────────────────────────────────────────────┘   │     │
│  │                                                        │     │
│  │  [Create Campaign]  [Refine Details]  [Modify]         │     │
│  │  10:33 AM                                              │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Type a message...              [📎] [🎤] [→ Send]  │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 17.6 Analytics Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  Analytics                         Last 30 Days ▼    [Export]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐       │
│  │ Sessions │ PageViews│ Bounce   │ Avg.Sess.│ Conversion│      │
│  │ 124,592  │ 847,283  │ 32.1%   │ 4m 23s   │ 3.09%    │       │
│  │ ↑12.4%   │ ↑8.2%    │ ↓2.1%   │ ↑0.5%    │ ↑0.8%    │       │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Performance Over Time                                  │     │
│  │  ┌─────────────────────────────────────────────────┐   │     │
│  │  │  ▁▃▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▇▆▅▆▇▆▅▇▆▅▆▇▆▅▇▆▅▇▆  │   │     │
│  │  │ ▕         📈 Revenue over time              ▏  │   │     │
│  │  │ ▕  ─ Sessions    ─ Conversions              ▏  │   │     │
│  │  │  └──────────────────────────────────────────   │   │     │
│  │  │  May 1                          May 30        │   │     │
│  │  └─────────────────────────────────────────────────┘   │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  ┌───────────────────────┐ ┌───────────────────────┐            │
│  │  Traffic Sources      │ │  Top Campaigns        │            │
│  │  ┌─────────────────┐  │ │  ┌─────────────────┐  │            │
│  │  │  Organic  45%   │  │ │  │ 1. Summer Sale  │  │            │
│  │  │  Direct   22%   │  │ │  │ 2. Product Laun │  │            │
│  │  │  Social   18%   │  │ │  │ 3. Newsletter   │  │            │
│  │  │  Email    10%   │  │ │  │ 4. Webinar     │  │            │
│  │  │  Other     5%   │  │ │  │ 5. Retargeting │  │            │
│  │  └─────────────────┘  │ │  └─────────────────┘  │            │
│  └───────────────────────┘ └───────────────────────┘            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 17.7 Settings Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Settings                                                        │
├────────────────┬────────────────────────────────────────────────┤
│                │                                                 │
│  General  ●    │  General Settings                               │
│  Workspace     │  ┌─────────────────────────────────────────┐   │
│  Team          │  │  Workspace Name                         │   │
│  Billing       │  │  [Acme Corporation                  ]   │   │
│  API Keys      │  │                                         │   │
│  Notifications │  │  Workspace Slug                         │   │
│  Appearance    │  │  acme-corp                               │   │
│  Integrations  │  │                                         │   │
│                │  │  Industry                               │   │
│                │  │  [Marketing & Advertising      ▼]       │   │
│                │  │                                         │   │
│                │  │  Timezone                               │   │
│                │  │  [(UTC-5) Eastern Time (US & Canada)]   │   │
│                │  │                                         │   │
│                │  │  Default Currency                        │   │
│                │  │  [USD ($)                        ▼]     │   │
│                │  └─────────────────────────────────────────┘   │
│                │                                                 │
│                │  Branding                                       │
│                │  ┌─────────────────────────────────────────┐   │
│                │  │  Workspace Logo                         │   │
│                │  │  [Upload Logo]  [Remove]                │   │
│                │  │  Recommended: 256x256, PNG              │   │
│                │  │                                         │   │
│                │  │  Brand Color                             │   │
│                │  │  [#3B82F6       ]  [🎨 Pick]            │   │
│                │  │                                         │   │
│                │  │  □ White-label (hide AMC branding)      │   │
│                │  └─────────────────────────────────────────┘   │
│                │                                                 │
│                │  ┌─────────────────────────────────────────┐   │
│                │  │  [Save Changes]                         │   │
│                │  └─────────────────────────────────────────┘   │
└────────────────┴─────────────────────────────────────────────────┘
```

### 17.8 Marketplace Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Marketplace                               [Search extensions]  │
├─────────────────────────────────────────────────────────────────┤
│  Categories: All ● Analytics ● Automation ● Social ● Email     │
│              ● AI ● Integrations ● Templates                    │
│                                                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │   │
│  │ │  🤖         │ │ │ │  📊         │ │ │ │  📧         │ │   │
│  │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │   │
│  │  AI Copywriter  │ │  Advanced Anal. │ │  Mailchimp Sync │   │
│  │  Generate email │ │  Custom reports │ │  Two-way sync   │   │
│  │  copy with AI   │ │  & dashboards   │ │  with Mailchimp │   │
│  │                 │ │                 │ │                 │   │
│  │  ★★★★☆ (124)   │ │  ★★★★★ (89)    │ │  ★★★★☆ (256)   │   │
│  │  Free           │ │  $19/mo         │ │  Free           │   │
│  │  [Install]      │ │  [Install]      │ │  [Install]      │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │   │
│  │ │  📱         │ │ │ │  🔄         │ │ │ │  📈         │ │   │
│  │ └─────────────┘ │ │ └─────────────┘ │ │ └─────────────┘ │   │
│  │  Social Manager │ │  Zapier Connect │ │  SEO Optimizer  │   │
│  │  Schedule posts │ │  Connect 5000+  │ │  Keyword track  │   │
│  │  across networks│ │  apps & services│ │  & rank monitor │   │
│  │                 │ │                 │ │                 │   │
│  │  ★★★★☆ (445)   │ │  ★★★★★ (678)   │ │  ★★★★☆ (167)   │   │
│  │  $9/mo          │ │  Free           │ │  $29/mo         │   │
│  │  [Install]      │ │  [Install]      │ │  [Install]      │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                                                                  │
│  Page 1 of 12  ◀ 1 2 3 ... 12 ▶                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Appendices

### Appendix A: File Structure Reference

```
src/
├── app/                          # Next.js App Router pages
│   ├── (auth)/                   # Auth pages (login, register)
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/              # Authenticated pages
│   │   ├── dashboard/page.tsx
│   │   ├── campaigns/
│   │   ├── crm/
│   │   ├── agents/
│   │   ├── analytics/
│   │   ├── seo/
│   │   ├── social/
│   │   ├── automation/
│   │   ├── knowledge/
│   │   ├── marketplace/
│   │   ├── settings/
│   │   └── layout.tsx            # Dashboard layout (Sidebar + Topbar)
│   ├── offline/page.tsx          # PWA offline fallback
│   ├── layout.tsx                # Root layout
│   └── providers.tsx             # Theme, Query, Session providers
│
├── components/
│   ├── ui/                       # shadcn/ui base atoms
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── badge.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── dropdown-menu.tsx
│   │   ├── form.tsx
│   │   ├── table.tsx
│   │   ├── tabs.tsx
│   │   ├── toast.tsx
│   │   ├── tooltip.tsx
│   │   └── ... (40+ components)
│   ├── forms/                    # Form molecules
│   │   ├── form-field.tsx
│   │   ├── search-bar.tsx
│   │   ├── multi-step-wizard.tsx
│   │   ├── ai-assisted-field.tsx
│   │   └── inline-edit.tsx
│   ├── data-display/             # Data display organisms
│   │   ├── data-table.tsx
│   │   ├── stat-card.tsx
│   │   ├── timeline.tsx
│   │   ├── json-viewer.tsx
│   │   └── ai-summary.tsx
│   ├── layout/                   # Layout organisms
│   │   ├── app-shell.tsx
│   │   ├── sidebar.tsx
│   │   ├── topbar.tsx
│   │   └── workspace-switcher.tsx
│   ├── agents/                   # AI Agent components
│   │   ├── agent-card.tsx
│   │   ├── chat-message.tsx
│   │   ├── chat-interface.tsx
│   │   ├── approval-card.tsx
│   │   └── memory-browser.tsx
│   ├── charts/                   # Chart components
│   │   ├── line-chart.tsx
│   │   ├── bar-chart.tsx
│   │   ├── area-chart.tsx
│   │   ├── pie-chart.tsx
│   │   ├── radar-chart.tsx
│   │   └── funnel-chart.tsx
│   └── shared/                   # Shared components
│       ├── empty-state.tsx
│       ├── error-state.tsx
│       ├── loading-skeleton.tsx
│       ├── page-header.tsx
│       └── screen-reader.tsx
│
├── hooks/                        # Custom hooks
│   ├── use-debounce.ts
│   ├── use-online-status.ts
│   ├── use-auto-save.ts
│   ├── use-focus-trap.ts
│   └── use-data-table.ts
│
├── lib/                          # Utilities, config, types
│   ├── utils.ts                  # cn() helper
│   ├── chart-config.ts
│   └── design-tokens.ts
│
├── store/                        # Zustand stores
│   ├── use-sidebar.ts
│   ├── use-workspace.ts
│   └── use-theme.ts
│
├── styles/                       # Global styles
│   ├── globals.css
│   └── themes.css
│
└── types/                        # TypeScript types
    ├── design-system.ts
    ├── components.ts
    └── api.ts
```

### Appendix B: Design System Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | June 2026 | Design Systems Team | Initial release |

### Appendix C: Design Review Checklist

Before submitting a UI change, verify:

- [ ] All colors use design tokens (no hardcoded hex values)
- [ ] Component variants match documentation
- [ ] All interactive states implemented (hover, focus, active, disabled)
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] Screen reader labels present on all controls
- [ ] Color contrast passes 4.5:1 (normal text) / 3:1 (large text)
- [ ] Responsive: works on mobile (320px), tablet (768px), desktop (1280px)
- [ ] Loading skeleton present for async content
- [ ] Empty state defined for zero-data scenarios
- [ ] Error boundary catches rendering failures
- [ ] Dark mode renders correctly
- [ ] Motion respects `prefers-reduced-motion`
- [ ] Bundle size impact is within budget (check with `@next/bundle-analyzer`)
- [ ] No console errors or warnings
- [ ] Storybook story added for new components
- [ ] Accessibility audit (axe-core) passes

---

*End of Volume 7: Frontend UI/UX Design System*

> **Next Volume:** Volume 8 — API Design & Integration Patterns
