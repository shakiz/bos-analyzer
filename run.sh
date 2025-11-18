#!/usr/bin/env bash
set -euo pipefail

# Developer-friendly run script for local development.
# - Starts the backend (uvicorn) in the background and logs to backend/backend.log
# - Starts the frontend (Vite) in foreground so you can see dev server logs

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Project root: $ROOT_DIR"

### Backend
echo "---- Backend -> installing python requirements (user site) and starting uvicorn on :8000 ----"
cd "$ROOT_DIR/backend"

# If port 8000 is already in use, assume the backend is running and skip starting a second instance.
if lsof -i :8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 already in use — skipping backend start. If this is unexpected, check 'lsof -i :8000' to find the process."
  BACK_PID=""
else
  if [ -f requirements.txt ]; then
    echo "Installing python requirements (to user site packages). This may take a while the first time..."
    python3 -m pip install --user -r requirements.txt
  else
    echo "No requirements.txt found in backend/ — skipping pip install"
  fi

  # Start backend in background and capture logs
  BACKEND_LOG="$ROOT_DIR/backend/backend.log"
  echo "Starting uvicorn (main:app) on 127.0.0.1:8000 — logging to $BACKEND_LOG"
  # Use the module interface so the script works even if the uvicorn CLI isn't on PATH
  python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 &> "$BACKEND_LOG" &
  BACK_PID=$!
  echo "Backend started (PID $BACK_PID)"
fi

### Frontend
echo "---- Frontend -> installing node deps (if needed) and starting vite dev server ----"
cd "$ROOT_DIR/frontend"

# Try to locate npm. In some setups (nvm, asdf, Homebrew) npm may not be on PATH in non-interactive shells.
NPM_CMD=""
if command -v npm >/dev/null 2>&1; then
  NPM_CMD="npm"
else
  # Common locations to probe
  CANDIDATES=("/opt/homebrew/bin/npm" "/usr/local/bin/npm" "$HOME/.nvm/versions/node" "$HOME/.asdf/installs/nodejs")
  for c in "${CANDIDATES[@]}"; do
    if [[ -d "$c" ]]; then
      # find an npm binary under this directory
      found=$(find "$c" -type f -name npm -print -maxdepth 3 2>/dev/null | head -n 1 || true)
      if [[ -n "$found" && -x "$found" ]]; then
        NPM_CMD="$found"
        break
      fi
    elif [[ -x "$c" ]]; then
      NPM_CMD="$c"
      break
    fi
  done
fi

if [[ -z "$NPM_CMD" ]]; then
  echo "Could not find 'npm' in PATH. Frontend will not be started."
  echo "Please install Node.js (which includes npm) or ensure npm is available in PATH." \
       "Common ways: Homebrew (brew install node), nvm (source ~/.nvm/nvm.sh), or download from nodejs.org."
  echo "Backend (if started) will continue running in the background."
  exit 0
fi

echo "Using npm binary: $NPM_CMD"
if [ -d node_modules ]; then
  echo "node_modules found — skipping npm install"
else
  echo "Running npm install (this may take a while the first time)"
  "$NPM_CMD" install
fi

echo "Starting frontend: $NPM_CMD run dev (Vite). If this fails, run '$NPM_CMD install' manually in frontend/ then run '$NPM_CMD run dev'"
"$NPM_CMD" run dev

# Wait for background process to exit if any (keeps script behavior consistent when frontend finishes)
if [[ -n "${BACK_PID-}" ]]; then
  wait $BACK_PID || true
fi
