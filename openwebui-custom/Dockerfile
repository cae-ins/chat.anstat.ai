# Dockerfile - OpenWebUI personnalisé pour ANSTAT
# Build: docker build -t openwebui-anstat:latest .

FROM ghcr.io/open-webui/open-webui:main

# Métadonnées
LABEL maintainer="ANSTAT - Agence Nationale de la Statistique"
LABEL description="Chat ANSTAT AI - Interface de chat IA personnalisée"
LABEL version="1.0.0"

# Copier les assets personnalisés
COPY favicon.ico /tmp/favicon.ico
COPY favicon.png /tmp/favicon.png
COPY custom-anstat.css /tmp/custom-anstat.css

# Remplacer TOUS les favicons existants dans l'image + ajouter le CSS
RUN find /app -name "favicon*" -type f 2>/dev/null | while read f; do \
        ext="${f##*.}"; \
        if [ "$ext" = "ico" ]; then cp /tmp/favicon.ico "$f"; \
        elif [ "$ext" = "png" ]; then cp /tmp/favicon.png "$f"; \
        fi; \
        echo "Replaced: $f"; \
    done && \
    # Copier le CSS
    cp /tmp/custom-anstat.css /app/build/static/custom-anstat.css && \
    # Lister tous les fichiers favicon pour vérification
    echo "=== Tous les favicons dans /app ===" && \
    find /app -name "favicon*" -type f 2>/dev/null && \
    # Nettoyer
    rm -f /tmp/favicon.* /tmp/custom-anstat.css

# Script d'entrypoint amélioré
RUN cat > /app/entrypoint-anstat.sh << 'SCRIPT'
#!/bin/bash
set -e

echo "[ANSTAT] Injection des assets personnalisés..."

# Injecter dans tous les fichiers HTML
for html_file in /app/build/*.html /app/build/**/*.html; do
    [ -f "$html_file" ] || continue

    # Injecter le CSS
    if ! grep -q "custom-anstat.css" "$html_file" 2>/dev/null; then
        sed -i 's|</head>|<link rel="stylesheet" href="/static/custom-anstat.css"></head>|g' "$html_file"
        echo "[ANSTAT] CSS injecté dans: $html_file"
    fi

    # Forcer le favicon avec cache-bust
    sed -i 's|<link rel="icon"[^>]*>||g' "$html_file"
    sed -i 's|<link rel="shortcut icon"[^>]*>||g' "$html_file"
    sed -i "s|</head>|<link rel=\"icon\" type=\"image/x-icon\" href=\"/favicon.ico?v=$(date +%s)\"></head>|g" "$html_file"
    echo "[ANSTAT] Favicon injecté dans: $html_file"
done

echo "[ANSTAT] Assets prêts. Démarrage d'OpenWebUI..."
exec "$@"
SCRIPT
RUN chmod +x /app/entrypoint-anstat.sh

ENTRYPOINT ["/app/entrypoint-anstat.sh"]
CMD ["bash", "start.sh"]
