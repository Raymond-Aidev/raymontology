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

# Copy custom nginx configuration as template
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy built static files
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port (Railway uses dynamic PORT)
EXPOSE 80

# Start nginx with envsubst for PORT variable
# nginx docker image automatically processes templates in /etc/nginx/templates/
CMD ["sh", "-c", "envsubst '$$PORT' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
