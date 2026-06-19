# =============================================================================
# Aegis Marketing Cloud — Frontend Dockerfile
# Multi-stage build: dev, production
# =============================================================================

# ── Dependencies stage ──────────────────────────────────────────────────────
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci && npm cache clean --force

# ── Development target ──────────────────────────────────────────────────────
FROM node:20-alpine AS development

WORKDIR /app

# Copy node_modules from deps
COPY --from=deps /app/node_modules ./node_modules

# Copy source (will be overridden by volume mount in dev)
COPY . .

ENV NODE_ENV=development \
    WATCHPACK_POLLING=true \
    CHOKIDAR_USEPOLLING=true \
    NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

CMD ["npm", "run", "dev"]

# ── Build stage ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Production (nginx runtime) ──────────────────────────────────────────────
FROM nginx:alpine AS production

COPY --from=build /app/out /usr/share/nginx/html
COPY deployment/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
