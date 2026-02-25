FROM node:20-alpine as build

WORKDIR /app

# package.jsonをコピーして依存関係をインストール (layer caching for faster builds)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

# Instead of passing the password as an env var, a plceholder (dummy) is used
# This is to prevent the actual password from being exposed in the build process in JS files
ENV VITE_APP_PASSWORD=__VITE_APP_PASSWORD_PLACEHOLDER__

# Build the app
RUN npm run build

# Nginxでホスト
FROM nginx:alpine

# Update Alpine packages to fix security vulnerabilities (including pcre2)
RUN apk upgrade --no-cache

COPY --from=build /app/dist /usr/share/nginx/html

# Nginxの設定（SPA用）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# This is to replace the placeholder with the actual password at runtime
# Nginxが起動する直前に、JSファイルの中にあるダミー文字を全部探し出して、本物のパスワード（環境変数）に一括置換（書き換え）する
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

EXPOSE 8080

# nginx が非rootで動くようにディレクトリ権限を設定
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid

USER nginx

CMD ["/docker-entrypoint.sh"]