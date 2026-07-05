# REDIRECTS

Redirect rules for keprixai.uk. Configure these in your web server (Nginx, Apache, Caddy) or CDN.

## Trailing slash normalisation

All paths should serve with trailing slashes. Non-trailing-slash variants redirect to the canonical form.

```
/architecture   -> /architecture/   301
/consolidation  -> /consolidation/  301
/mutation-engine -> /mutation-engine/ 301
/playbooks      -> /playbooks/      301
/hub            -> /hub/            301
/community      -> /community/      301
/contributing   -> /contributing/   301
/security       -> /security/       301
/roadmap        -> /roadmap/        301
/brand-boundary -> /brand-boundary/ 301
/legal          -> /legal/          301
```

## Domain redirects

If keprix.io is acquired, redirect to keprixai.uk until the primary domain moves:

```
keprix.io/* -> https://keprixai.uk/$1  301
```

## Legacy paths (none yet)

No legacy paths exist at initial launch. Add entries here when paths change to preserve inbound links and search indexing.

## Nginx config snippet

```nginx
server {
    listen 443 ssl http2;
    server_name keprixai.uk;
    root /var/www/keprixai.uk;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }

    # Redirect non-trailing-slash inner paths
    rewrite ^(/[^.]+[^/])$ $1/ permanent;
}
```

## Caddy config snippet

```caddy
keprixai.uk {
    root * /var/www/keprixai.uk
    file_server
    # Caddy handles trailing slashes automatically for directory indexes
    encode gzip
}
```
