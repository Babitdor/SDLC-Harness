# syntax=docker/dockerfile:1.7
# ── SDLC Harness Frontend ────────────────────────────────────────────────
#
# Multi-stage build: compile Next.js in a full Node image, serve with a
# slim production runtime. The app talks to the backend at localhost:8000
# (the browser connects directly — both ports are exposed in compose).

# ── Build stage ──────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /build

# Install ALL dependencies (including devDependencies). Build-time CSS
# tooling like `@tailwindcss/postcss` lives in devDependencies but is
# required during `next build` — skipping dev deps here causes Turbopack
# to fail with `Cannot find module '@tailwindcss/postcss'` while compiling
# globals.css. The runtime image stays slim regardless because it only
# pulls in `.next/standalone` + `public` + `.next/static` below.
#
# Mount the npm cache so dep installs reuse already-downloaded tarballs
# between builds.
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

# Copy source and build the standalone bundle.
COPY . .
RUN npm run build

# ── Runtime stage ────────────────────────────────────────────────────
FROM node:22-alpine

WORKDIR /app

# Non-root account. node:22-alpine doesn't ship one by default, so we
# create `nextjs:nodejs` (1001:1001) and chown the copied artefacts.
RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 --ingroup nodejs --disabled-password --shell /sbin/nologin nextjs

# Standalone output bundles only the production-required `node_modules`
# subset Next.js detected via tracing; full dev deps don't ship.
COPY --from=builder --chown=nextjs:nodejs /build/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /build/.next/static     ./.next/static
COPY --from=builder --chown=nextjs:nodejs /build/public           ./public

USER 1001:1001

EXPOSE 3000

ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
