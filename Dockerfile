FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm and dependencies
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Copy source
COPY . .

# Build frontend
RUN pnpm build

# Production image
FROM node:20-alpine

WORKDIR /app

# Install serve (simple HTTP server for static files)
RUN npm install -g serve

# Copy built assets from builder
COPY --from=builder /app/apps/admin-web/dist ./dist

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

# Expose port
EXPOSE 3000

# Start server
ENV NODE_ENV=production
CMD ["serve", "-s", "dist", "-l", "3000"]
