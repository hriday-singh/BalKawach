# Stage 1: Build the React application
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve the static files with Nginx
FROM nginx:alpine
# Copy the custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf
# Copy the built Vite assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 9122
CMD ["nginx", "-g", "daemon off;"]
