# Not in the project as the IDE configuration will be lost if the project is moved
# ~/.virtualenvs is a [convention](https://docs.python.org/3/library/venv.html)
export UV_PROJECT_ENVIRONMENT="$HOME/.virtualenvs/aitm"

# creates .venv + installs deps automatically
uv sync

# Activate
# Modify the path
if [ -f "$UV_PROJECT_ENVIRONMENT/Scripts/activate" ]; then
  # Windows (Git Bash / WSL boundary)
  source "$UV_PROJECT_ENVIRONMENT/Scripts/activate"
else
  # Linux/macOS
  source "$UV_PROJECT_ENVIRONMENT/bin/activate"
fi

# When a virtual environment is active,
# the VIRTUAL_ENV environment variable is set
if [ "$VIRTUAL_ENV" != "$UV_PROJECT_ENVIRONMENT" ]; then
  echo "Virtual env value ($VIRTUAL_ENV) is not $UV_PROJECT_ENVIRONMENT"
fi

# Cert file
SSL_DIR="./resources/ssl-certs"
if [ ! -f "$SSL_DIR/cert.pem" ]; then
  mkcert --cert-file "$SSL_DIR/cert.pem" -key-file "$SSL_DIR/key.pem" localhost 127.0.0.1 ::1
fi
