# Multi-stage build: production-ready React frontend
# Optimized for AWS CloudFront, S3, or ECS deployment

# Stage 1: Builder
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies (production only)
RUN npm ci --only=production

# Copy source code
COPY . .

# Build React app (creates /app/dist)
RUN npm run build

# Stage 2: Runtime (serve with lightweight HTTP server)
FROM node:18-alpine

WORKDIR /app

# Install serve to run the built app
RUN npm install -g serve

# Copy built app from builder
COPY --from=builder /app/dist ./dist

# Create non-root user for security
RUN addgroup -g 1000 cloudguard && \
    adduser -D -u 1000 -G cloudguard cloudguard && \
    chown -R cloudguard:cloudguard /app
USER cloudguard

# Environment
ENV NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Expose port
EXPOSE 3000

# Serve the built app
CMD ["serve", "-s", "dist", "-l", "3000", "-n"]
