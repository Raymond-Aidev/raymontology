# ===========================================
# Raymontology Frontend - Production Dockerfile
# ===========================================
# Multi-stage build for optimized production image

# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files for dependency caching
COPY package*.json ./

# Install dependencies (ci for reproducible builds)
RUN npm ci

# Copy source code
COPY . .

# Build argument for API URL (set during build)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# ===========================================
# Production stage - nginx
# ===========================================
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.template

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port (Railway uses dynamic PORT)
EXPOSE 80

# Replace PORT_PLACEHOLDER with actual PORT and start nginx
CMD ["sh", "-c", "sed \"s/PORT_PLACEHOLDER/${PORT:-80}/g\" /etc/nginx/nginx.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
