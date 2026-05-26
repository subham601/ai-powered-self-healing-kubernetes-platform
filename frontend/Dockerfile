FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

# Serve static assets
FROM nginx:alpine
COPY --from=0 /app/dist /usr/share/nginx/html
EXPOSE 8085

