#!/usr/bin/env bash
set -e

# Aguarda o PostgreSQL ficar disponível.
if [ -n "$POSTGRES_HOST" ]; then
  echo "Aguardando PostgreSQL em $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  until python -c "import socket,sys; s=socket.socket(); s.settimeout(2); \
    sys.exit(0) if not s.connect_ex(('$POSTGRES_HOST', int('${POSTGRES_PORT:-5432}'))) else sys.exit(1)" 2>/dev/null; do
    sleep 1
  done
  echo "PostgreSQL disponível."
fi

# Aplica migrações apenas no processo web (evita corrida entre web/worker/beat).
if [ "$RUN_MIGRATIONS" = "1" ]; then
  echo "Aplicando migrações..."
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput || true
fi

exec "$@"
