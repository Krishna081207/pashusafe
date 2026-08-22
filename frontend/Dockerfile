FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# proxy /api to the backend service inside the compose network
RUN printf 'server {\n\
  listen 80;\n\
  location /api/ { proxy_pass http://backend:8000; }\n\
  location /health { proxy_pass http://backend:8000; }\n\
  location / { root /usr/share/nginx/html; try_files $uri /index.html; }\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
