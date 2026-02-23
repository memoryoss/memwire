#!/usr/bin/env bash

set -o nounset
set -o errexit

# ──────────────────────────────────────────────
# MemWire — Memory Infrastructure for AI Agents
# ──────────────────────────────────────────────

blue='\033[94m'
green='\033[32m'
red='\033[31m'
yellow='\033[33m'
reset='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_ENV_FILE="$SCRIPT_DIR/api/.env"
API_SAMPLE_ENV="$SCRIPT_DIR/api/sample.env"

docker_compose_cmd=""

# ── Helpers ──────────────────────────────────

log()     { echo -e "${blue}[memwire]${reset} $1"; }
success() { echo -e "${green}[memwire]${reset} $1"; }
warn()    { echo -e "${yellow}[memwire]${reset} $1"; }
error()   { echo -e "${red}[memwire]${reset} $1"; }

banner() {
  echo ""
  echo -e "${blue}  ███╗   ███╗███████╗███╗   ███╗██╗    ██╗██╗██████╗ ███████╗${reset}"
  echo -e "${blue}  ████╗ ████║██╔════╝████╗ ████║██║    ██║██║██╔══██╗██╔════╝${reset}"
  echo -e "${blue}  ██╔████╔██║█████╗  ██╔████╔██║██║ █╗ ██║██║██████╔╝█████╗  ${reset}"
  echo -e "${blue}  ██║╚██╔╝██║██╔══╝  ██║╚██╔╝██║██║███╗██║██║██╔══██╗██╔══╝  ${reset}"
  echo -e "${blue}  ██║ ╚═╝ ██║███████╗██║ ╚═╝ ██║╚███╔███╔╝██║██║  ██║███████╗${reset}"
  echo -e "${blue}  ╚═╝     ╚═╝╚══════╝╚═╝     ╚═╝ ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚══════╝${reset}"
  echo ""
  echo -e "  ${yellow}Memory Infrastructure for AI Agents${reset}"
  echo ""
}

check_dependencies() {
  if ! command -v docker &>/dev/null; then
    error "Docker not found. Install Docker: https://docs.docker.com/get-docker/"
    exit 1
  fi

  if docker compose version &>/dev/null 2>&1; then
    docker_compose_cmd="docker compose"
  elif command -v docker-compose &>/dev/null; then
    docker_compose_cmd="docker-compose"
  else
    error "Neither 'docker compose' nor 'docker-compose' found."
    exit 1
  fi

  success "Docker detected (${docker_compose_cmd})"
}

get_compose_files() {
  local use_bundled_db="true"
  local llm_provider="openai"

  # Read settings from env file if it exists
  if [ -f "$API_ENV_FILE" ]; then
    use_bundled_db=$(grep -E '^USE_BUNDLED_DB=' "$API_ENV_FILE" | cut -d'=' -f2 | tr -d '[:space:]' || echo "true")
    llm_provider=$(grep -E '^LLM_PROVIDER=' "$API_ENV_FILE" | cut -d'=' -f2 | tr -d '[:space:]' || echo "openai")
  fi

  local files
  if [ "${use_bundled_db:-true}" = "false" ]; then
    files="-f docker-compose.yaml"
  else
    files="-f docker-compose.yaml -f docker-compose.infra.yaml"
  fi

  # Auto-activate Ollama local profile when provider is ollama
  if [ "${llm_provider:-openai}" = "ollama" ]; then
    files="$files --profile local"
  fi

  echo "$files"
}

setup_env() {
  if [ ! -f "$API_ENV_FILE" ]; then
    warn "api/.env not found. Creating from sample.env..."
    cp "$API_SAMPLE_ENV" "$API_ENV_FILE"

    echo ""
    echo -e "${yellow}Configure your LLM provider:${reset}"
    read -rp "  LLM provider [openai/azure_openai/anthropic/ollama] (default: openai): " provider
    provider="${provider:-openai}"

    # Update provider
    sed -i.bak "s|^LLM_PROVIDER=.*|LLM_PROVIDER=${provider}|" "$API_ENV_FILE"

    if [ "$provider" = "ollama" ]; then
      read -rp "  Ollama LLM model (default: llama3.2): " ollama_model
      ollama_model="${ollama_model:-llama3.2}"
      read -rp "  Ollama embed model (default: nomic-embed-text): " ollama_embed
      ollama_embed="${ollama_embed:-nomic-embed-text}"

      sed -i.bak "s|^LLM_API_KEY=.*|LLM_API_KEY=ollama|" "$API_ENV_FILE"
      sed -i.bak "s|^LLM_MODEL=.*|LLM_MODEL=${ollama_model}|" "$API_ENV_FILE"
      sed -i.bak "s|^LLM_BASE_URL=.*|LLM_BASE_URL=http://ollama:11434|" "$API_ENV_FILE"
      sed -i.bak "s|^EMBEDDING_MODEL=.*|EMBEDDING_MODEL=${ollama_embed}|" "$API_ENV_FILE"
      sed -i.bak "s|^EMBEDDING_DIMENSIONS=.*|EMBEDDING_DIMENSIONS=768|" "$API_ENV_FILE"

      warn "Ollama selected — models will be pulled automatically on first start."
      warn "LLM: ${ollama_model}  |  Embedder: ${ollama_embed}"
      warn "First startup may take several minutes while models download."
    else
      read -rp "  API key for ${provider}: " api_key
      sed -i.bak "s|^LLM_API_KEY=.*|LLM_API_KEY=${api_key}|" "$API_ENV_FILE"
    fi

    rm -f "${API_ENV_FILE}.bak"
    success "api/.env configured."
  else
    log "api/.env already exists. Skipping."
  fi
}

cmd_start() {
  banner
  check_dependencies
  setup_env

  local compose_files
  compose_files=$(get_compose_files)

  cd "$SCRIPT_DIR"
  log "Building images (this may take a few minutes on first run)..."
  $docker_compose_cmd $compose_files build

  log "Starting MemWire..."
  $docker_compose_cmd $compose_files up -d

  echo ""
  success "MemWire is running!"
  echo ""
  echo -e "  ${green}→ Dashboard:${reset}  http://localhost:${UI_PORT:-3000}"
  echo -e "  ${green}→ API:${reset}        http://localhost:${API_PORT:-8000}"
  echo -e "  ${green}→ API Docs:${reset}   http://localhost:${API_PORT:-8000}/docs"
  echo ""
}

cmd_stop() {
  check_dependencies
  local compose_files
  compose_files=$(get_compose_files)
  cd "$SCRIPT_DIR"
  log "Stopping MemWire..."
  $docker_compose_cmd $compose_files down
  success "Stopped."
}

cmd_build() {
  check_dependencies
  cd "$SCRIPT_DIR"
  log "Building images locally..."
  $docker_compose_cmd -f docker-compose.yaml -f docker-compose.infra.yaml -f docker-compose.build.yaml build
  success "Build complete."
}

cmd_migrate() {
  check_dependencies
  cd "$SCRIPT_DIR"
  log "Running database migrations..."
  $docker_compose_cmd exec api python -m alembic upgrade head
  success "Migrations complete."
}

cmd_logs() {
  check_dependencies
  local compose_files
  compose_files=$(get_compose_files)
  cd "$SCRIPT_DIR"
  $docker_compose_cmd $compose_files logs -f
}

cmd_reset() {
  check_dependencies
  local compose_files
  compose_files=$(get_compose_files)
  cd "$SCRIPT_DIR"
  warn "This will destroy all containers AND volumes (all data). Are you sure? [y/N]"
  read -r confirm
  if [[ "${confirm}" =~ ^[Yy]$ ]]; then
    $docker_compose_cmd $compose_files down -v --remove-orphans
    success "Reset complete. All data removed."
  else
    log "Reset cancelled."
  fi
}

cmd_status() {
  check_dependencies
  local compose_files
  compose_files=$(get_compose_files)
  cd "$SCRIPT_DIR"
  $docker_compose_cmd $compose_files ps
}

usage() {
  echo ""
  echo "Usage: ./memwire.sh <command>"
  echo ""
  echo "Commands:"
  echo "  start     Start all services (first run: sets up .env)"
  echo "  stop      Stop all services"
  echo "  build     Build Docker images from source"
  echo "  migrate   Run database migrations"
  echo "  logs      Tail all service logs"
  echo "  status    Show running service status"
  echo "  reset     Tear down all containers and volumes (destructive)"
  echo ""
  echo "Local mode (no external LLM):"
  echo "  Set LLM_PROVIDER=ollama in api/.env — Ollama starts automatically."
  echo "  Models pulled on first start: llama3.2 (LLM), nomic-embed-text (embedder)"
  echo ""
}

# ── Entry point ────────────────────────────────

command="${1:-}"

case "$command" in
  start)   cmd_start ;;
  stop)    cmd_stop ;;
  build)   cmd_build ;;
  migrate) cmd_migrate ;;
  logs)    cmd_logs ;;
  status)  cmd_status ;;
  reset)   cmd_reset ;;
  *)       usage; exit 1 ;;
esac
