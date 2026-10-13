# Build the React app, then serve it with Caddy, which also forwards the API and the
# admin site to the backend over Railway's private network, so the browser sees one
# origin and the session and CSRF cookies work exactly as they do locally.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
