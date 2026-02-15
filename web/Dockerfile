FROM nginx:1.25-alpine

# Copy walkthrough files from demo/ to nginx root
COPY demo/ /usr/share/nginx/html/

# Custom nginx config for SPA + proper MIME types
COPY web/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
