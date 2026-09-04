#!/usr/bin/env bash
set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ROOT="$(cd "$(dirname "$0")" && pwd)"
FRONTEND="$ROOT/frontend"
FRONTEND_PORT=3000
AWS_API_URL="https://4d6spw8ar6.execute-api.us-east-1.amazonaws.com/api"
AWS_SOCKET_URL="https://4d6spw8ar6.execute-api.us-east-1.amazonaws.com"

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       CloudGuard — CDR Simulation Platform       ║${NC}"
echo -e "${BLUE}║       Based on CrowdStrike CDR White Paper        ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -f "$FRONTEND/package.json" ]; then
  echo -e "${RED}✗ Frontend not found at $FRONTEND/package.json${NC}"
  exit 1
fi

echo -e "${YELLOW}Clearing ports $FRONTEND_PORT and 5001...${NC}"
lsof -ti:"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
lsof -ti:5001 | xargs kill -9 2>/dev/null || true
sleep 1

echo -e "${YELLOW}Preparing frontend dependencies...${NC}"
cd "$FRONTEND"
if [ ! -d "node_modules" ]; then
  npm config set strict-ssl false
  npm install --silent
  npm config set strict-ssl true
fi

echo -e "${GREEN}Starting frontend on http://localhost:$FRONTEND_PORT...${NC}"
VITE_API_URL="$AWS_API_URL" VITE_SOCKET_URL="$AWS_SOCKET_URL" npm run dev &
FRONTEND_PID=$!

echo -e "${YELLOW}Waiting for frontend to become available...${NC}"
for _ in {1..30}; do
  if curl -fsS "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend ready${NC}"
    break
  fi
  sleep 1
done

echo -e "${CYAN}Using live AWS backend: $AWS_API_URL${NC}"

echo -e "${GREEN}Opening CloudGuard in browser...${NC}"
open "http://localhost:$FRONTEND_PORT" 2>/dev/null || true

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           CloudGuard is running in AWS mode      ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║   Dashboard → http://localhost:$FRONTEND_PORT                 ║${NC}"
echo -e "${GREEN}║   Backend   → $AWS_API_URL    ║${NC}"
echo -e "${GREEN}║                                                  ║${NC}"
echo -e "${GREEN}║   Press Ctrl+C to stop                           ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Demo flow:${NC}"
echo -e "  1. Open ${BLUE}BP2 · IAM Escalation${NC}"
echo -e "  2. Click ${BLUE}Run Simulation${NC}"
echo -e "  3. Watch ${BLUE}Live Alerts${NC} update"
echo -e "  4. Inspect ${BLUE}Attack Timeline${NC} and ${BLUE}MITRE ATT&CK${NC}"
echo -e "  5. Check ${BLUE}Prowler Findings${NC} for posture issues"
echo ""

cleanup() {
  echo ""
  echo -e "${YELLOW}Shutting down CloudGuard...${NC}"
  kill "$FRONTEND_PID" 2>/dev/null || true
  lsof -ti:"$FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
  lsof -ti:5001 | xargs kill -9 2>/dev/null || true
  echo -e "${GREEN}Done.${NC}"
}

trap cleanup INT TERM

wait
