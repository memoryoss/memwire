# ── Builder stage ─────────────────────────────
FROM node:20-alpine AS builder
ARG VITE_API_URL=http://localhost:8000

WORKDIR /app
COPY ui/package.json ./
RUN npm install

COPY ui/ .
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# ── Production stage (nginx) ──────────────────
FROM nginx:1.27-alpine AS production
LABEL maintainer="ChatMemory"

COPY --from=builder /app/dist /usr/share/nginx/html
COPY ui/nginx.conf /etc/nginx/conf.d/default.conf
COPY ui/generate-runtime-config.sh /docker-entrypoint.d/40-generate-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/40-generate-runtime-config.sh

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
