# Build context is the repo root, so the content step can read content/ and photos/.
FROM node:20-alpine AS build
WORKDIR /repo
COPY apps/web/package.json apps/web/package-lock.json ./apps/web/
RUN cd apps/web && npm ci
COPY content ./content
COPY photos ./photos
# The video walks build their record with the Worker's pure core (apps/web/lib/walks.ts).
COPY worker/src/core ./worker/src/core
COPY apps/web ./apps/web
ENV NEXT_TELEMETRY_DISABLED=1
ARG NEXT_PUBLIC_API_ORIGIN=http://localhost:8000
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ENV NEXT_PUBLIC_API_ORIGIN=$NEXT_PUBLIC_API_ORIGIN NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
RUN cd apps/web && npm run build
FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
# next.config.ts traces files from the repository root, so the standalone output keeps the repo's
# layout and its server sits at apps/web/server.js. Static files and public/ go beside it.
COPY --from=build /repo/apps/web/.next/standalone ./
COPY --from=build /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=build /repo/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
