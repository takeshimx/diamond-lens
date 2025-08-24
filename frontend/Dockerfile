FROM node:18-alpine as build

WORKDIR /app

# package.jsonをコピーして依存関係をインストール
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Build argument for password
ARG VITE_APP_PASSWORD
ENV VITE_APP_PASSWORD=$VITE_APP_PASSWORD

# Build the app
RUN npm run build

# Nginxでホスト
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# Nginxの設定（SPA用）
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]