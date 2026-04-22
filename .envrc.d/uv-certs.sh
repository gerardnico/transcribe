export VIRTUAL_ENV="$PROJECT_ROOT/.venv"

# creates .venv + installs deps automatically
uv sync

# activate
source .venv/bin/activate

# Cert file
if [ ! -f localhost.pem ]; then
  SSL_DIR="./ssl-certs"
  mkcert --cert-file "$SSL_DIR/cert.pem" -key-file "$SSL_DIR/key.pem" localhost 127.0.0.1 ::1
fi
