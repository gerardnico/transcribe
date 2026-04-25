export VIRTUAL_ENV="$PROJECT_ROOT/.venv"
export UV_PROJECT_ENVIRONMENT="$VIRTUAL_ENV"

# creates .venv + installs deps automatically
uv sync

# activate
if [ -f ".venv/Scripts/activate" ]; then
  # Windows (Git Bash / WSL boundary)
  source .venv/Scripts/activate
else
  # Linux/macOS
  source .venv/bin/activate
fi

# Cert file
SSL_DIR="./resources/ssl-certs"
if [ ! -f "$SSL_DIR/cert.pem" ]; then
  mkcert --cert-file "$SSL_DIR/cert.pem" -key-file "$SSL_DIR/key.pem" localhost 127.0.0.1 ::1
fi
