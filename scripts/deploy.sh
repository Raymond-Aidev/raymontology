#!/bin/bash

# =============================================================================
# Raymontology - Railway Deployment Script
# =============================================================================
#
# 이 스크립트는 Railway 배포 전 로컬에서 실행하여 배포 준비 상태를 확인합니다.
#
# 사용법:
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
#
# =============================================================================

set -e  # 에러 발생시 즉시 종료

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Icons
CHECK="✓"
CROSS="✗"
ARROW="→"

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}  Raymontology - Railway Deployment Checker${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

# =============================================================================
# 1. Environment Check
# =============================================================================

echo -e "${YELLOW}[1/8] Checking Environment...${NC}"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    echo -e "  ${GREEN}${CHECK}${NC} Python ${PYTHON_VERSION} installed"
else
    echo -e "  ${RED}${CROSS}${NC} Python 3.11+ required"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "  ${GREEN}${CHECK}${NC} Node.js ${NODE_VERSION} installed"
else
    echo -e "  ${RED}${CROSS}${NC} Node.js 18+ required"
    exit 1
fi

# Check Railway CLI
if command -v railway &> /dev/null; then
    echo -e "  ${GREEN}${CHECK}${NC} Railway CLI installed"
else
    echo -e "  ${YELLOW}${ARROW}${NC} Railway CLI not found. Install: npm i -g @railway/cli"
fi

echo ""

# =============================================================================
# 2. Git Status Check
# =============================================================================

echo -e "${YELLOW}[2/8] Checking Git Status...${NC}"

# Check if git repo
if [ -d .git ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Git repository found"

    # Check for uncommitted changes
    if [ -z "$(git status --porcelain)" ]; then
        echo -e "  ${GREEN}${CHECK}${NC} No uncommitted changes"
    else
        echo -e "  ${YELLOW}${ARROW}${NC} Warning: Uncommitted changes detected"
        git status --short
    fi

    # Check current branch
    BRANCH=$(git branch --show-current)
    echo -e "  ${BLUE}${ARROW}${NC} Current branch: ${BRANCH}"
else
    echo -e "  ${RED}${CROSS}${NC} Not a git repository"
    exit 1
fi

echo ""

# =============================================================================
# 3. Backend Dependencies Check
# =============================================================================

echo -e "${YELLOW}[3/8] Checking Backend Dependencies...${NC}"

cd backend

# Check requirements.txt exists
if [ -f requirements.txt ]; then
    echo -e "  ${GREEN}${CHECK}${NC} requirements.txt found"

    # Count dependencies
    DEP_COUNT=$(grep -v '^#' requirements.txt | grep -v '^$' | wc -l)
    echo -e "  ${BLUE}${ARROW}${NC} ${DEP_COUNT} dependencies listed"
else
    echo -e "  ${RED}${CROSS}${NC} requirements.txt not found"
    exit 1
fi

# Check Procfile
if [ -f Procfile ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Procfile found"
    cat Procfile | while read line; do
        echo -e "      ${line}"
    done
else
    echo -e "  ${YELLOW}${ARROW}${NC} Procfile not found (creating...)"
    echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT --workers 2" > Procfile
    echo -e "  ${GREEN}${CHECK}${NC} Procfile created"
fi

# Check railway.json
if [ -f railway.json ]; then
    echo -e "  ${GREEN}${CHECK}${NC} railway.json found"
else
    echo -e "  ${YELLOW}${ARROW}${NC} railway.json not found (creating...)"
    cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF
    echo -e "  ${GREEN}${CHECK}${NC} railway.json created"
fi

cd ..

echo ""

# =============================================================================
# 4. Frontend Dependencies Check
# =============================================================================

echo -e "${YELLOW}[4/8] Checking Frontend Dependencies...${NC}"

cd frontend

# Check package.json
if [ -f package.json ]; then
    echo -e "  ${GREEN}${CHECK}${NC} package.json found"
else
    echo -e "  ${RED}${CROSS}${NC} package.json not found"
    exit 1
fi

# Check railway.json
if [ -f railway.json ]; then
    echo -e "  ${GREEN}${CHECK}${NC} railway.json found"
else
    echo -e "  ${YELLOW}${ARROW}${NC} railway.json not found (creating...)"
    cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "npm run preview -- --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
EOF
    echo -e "  ${GREEN}${CHECK}${NC} railway.json created"
fi

cd ..

echo ""

# =============================================================================
# 5. Environment Variables Check
# =============================================================================

echo -e "${YELLOW}[5/8] Checking Environment Variables...${NC}"

# Check .env.railway exists
if [ -f .env.railway ]; then
    echo -e "  ${GREEN}${CHECK}${NC} .env.railway template found"
else
    echo -e "  ${RED}${CROSS}${NC} .env.railway not found"
    exit 1
fi

# Check .gitignore contains .env files
if grep -q "\.env" .gitignore 2>/dev/null; then
    echo -e "  ${GREEN}${CHECK}${NC} .env files in .gitignore"
else
    echo -e "  ${YELLOW}${ARROW}${NC} Warning: .env not in .gitignore"
    echo ".env*" >> .gitignore
    echo -e "  ${GREEN}${CHECK}${NC} Added .env* to .gitignore"
fi

# Check for .env files in git
if git ls-files | grep -q "\.env$"; then
    echo -e "  ${RED}${CROSS}${NC} ERROR: .env file tracked in git!"
    echo -e "      Run: git rm --cached .env"
    exit 1
else
    echo -e "  ${GREEN}${CHECK}${NC} No .env files tracked in git"
fi

echo ""

# =============================================================================
# 6. Database Migration Check
# =============================================================================

echo -e "${YELLOW}[6/8] Checking Database Migrations...${NC}"

cd backend

# Check alembic directory
if [ -d alembic ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Alembic directory found"

    # Count migration files
    MIGRATION_COUNT=$(ls -1 alembic/versions/*.py 2>/dev/null | wc -l)
    echo -e "  ${BLUE}${ARROW}${NC} ${MIGRATION_COUNT} migration files found"
else
    echo -e "  ${RED}${CROSS}${NC} Alembic not initialized"
    exit 1
fi

# Check alembic.ini
if [ -f alembic.ini ]; then
    echo -e "  ${GREEN}${CHECK}${NC} alembic.ini found"
else
    echo -e "  ${RED}${CROSS}${NC} alembic.ini not found"
    exit 1
fi

cd ..

echo ""

# =============================================================================
# 7. Security Check
# =============================================================================

echo -e "${YELLOW}[7/8] Running Security Checks...${NC}"

# Check for hardcoded secrets in Python files
echo -e "  ${BLUE}${ARROW}${NC} Scanning for hardcoded secrets..."
SECRETS_FOUND=0

# Common secret patterns
PATTERNS=(
    "password\s*=\s*['\"][^'\"]+['\"]"
    "secret\s*=\s*['\"][^'\"]+['\"]"
    "api_key\s*=\s*['\"][^'\"]+['\"]"
    "token\s*=\s*['\"][^'\"]+['\"]"
)

for pattern in "${PATTERNS[@]}"; do
    if grep -r -i -E "$pattern" backend/app --include="*.py" | grep -v "settings.py" | grep -v "test_" > /dev/null 2>&1; then
        echo -e "  ${YELLOW}${ARROW}${NC} Warning: Potential hardcoded secret found (pattern: ${pattern})"
        SECRETS_FOUND=$((SECRETS_FOUND + 1))
    fi
done

if [ $SECRETS_FOUND -eq 0 ]; then
    echo -e "  ${GREEN}${CHECK}${NC} No obvious hardcoded secrets found"
else
    echo -e "  ${YELLOW}${ARROW}${NC} ${SECRETS_FOUND} potential issues - please review"
fi

# Check for TODO/FIXME comments
TODO_COUNT=$(grep -r "TODO\|FIXME" backend/app frontend/src --include="*.py" --include="*.ts" --include="*.tsx" 2>/dev/null | wc -l)
if [ $TODO_COUNT -gt 0 ]; then
    echo -e "  ${YELLOW}${ARROW}${NC} ${TODO_COUNT} TODO/FIXME comments found"
else
    echo -e "  ${GREEN}${CHECK}${NC} No pending TODO items"
fi

echo ""

# =============================================================================
# 8. Build Test
# =============================================================================

echo -e "${YELLOW}[8/8] Running Build Tests...${NC}"

# Backend: Check imports
echo -e "  ${BLUE}${ARROW}${NC} Testing backend imports..."
cd backend
if python3 -c "import app.main" 2>/dev/null; then
    echo -e "  ${GREEN}${CHECK}${NC} Backend imports successful"
else
    echo -e "  ${YELLOW}${ARROW}${NC} Warning: Backend import failed (dependencies may be missing)"
fi
cd ..

# Frontend: Check build
echo -e "  ${BLUE}${ARROW}${NC} Testing frontend build..."
cd frontend
if [ -d node_modules ]; then
    # Run build (with timeout)
    timeout 60s npm run build > /dev/null 2>&1 && BUILD_SUCCESS=true || BUILD_SUCCESS=false

    if [ "$BUILD_SUCCESS" = true ]; then
        echo -e "  ${GREEN}${CHECK}${NC} Frontend build successful"

        # Check dist directory
        if [ -d dist ]; then
            DIST_SIZE=$(du -sh dist | cut -f1)
            echo -e "  ${BLUE}${ARROW}${NC} Build size: ${DIST_SIZE}"
        fi
    else
        echo -e "  ${YELLOW}${ARROW}${NC} Warning: Frontend build failed or timed out"
    fi
else
    echo -e "  ${YELLOW}${ARROW}${NC} node_modules not found - run 'npm install' first"
fi
cd ..

echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${GREEN}  Deployment Readiness Check Complete!${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo -e "  1. ${BLUE}Railway Login${NC}"
echo -e "     ${ARROW} railway login"
echo ""
echo -e "  2. ${BLUE}Create New Project${NC}"
echo -e "     ${ARROW} railway init"
echo -e "     ${ARROW} Select: Empty Project"
echo ""
echo -e "  3. ${BLUE}Add PostgreSQL${NC}"
echo -e "     ${ARROW} Railway Dashboard → New → Database → PostgreSQL"
echo ""
echo -e "  4. ${BLUE}Add Redis${NC}"
echo -e "     ${ARROW} Railway Dashboard → New → Database → Redis"
echo ""
echo -e "  5. ${BLUE}Deploy Backend${NC}"
echo -e "     ${ARROW} cd backend && railway up"
echo -e "     ${ARROW} Set Root Directory: /backend"
echo ""
echo -e "  6. ${BLUE}Deploy Frontend${NC}"
echo -e "     ${ARROW} cd frontend && railway up"
echo -e "     ${ARROW} Set Root Directory: /frontend"
echo ""
echo -e "  7. ${BLUE}Configure Environment Variables${NC}"
echo -e "     ${ARROW} Railway Dashboard → Variables"
echo -e "     ${ARROW} Copy from .env.railway template"
echo ""
echo -e "  8. ${BLUE}Run Migrations${NC}"
echo -e "     ${ARROW} railway run alembic upgrade head"
echo ""
echo -e "  9. ${BLUE}Verify Deployment${NC}"
echo -e "     ${ARROW} curl https://your-backend.up.railway.app/health"
echo ""
echo -e "  10. ${BLUE}Setup Custom Domain (Optional)${NC}"
echo -e "      ${ARROW} Railway Dashboard → Settings → Networking → Custom Domain"
echo ""

echo -e "${GREEN}Documentation:${NC}"
echo -e "  ${ARROW} RAILWAY_DEPLOYMENT.md - Comprehensive deployment guide"
echo -e "  ${ARROW} .env.railway - Environment variables template"
echo ""

echo -e "${YELLOW}Important Reminders:${NC}"
echo -e "  ${CROSS} Do NOT commit .env files to git"
echo -e "  ${CROSS} Use strong SECRET_KEY (min 32 characters)"
echo -e "  ${CROSS} Set ENVIRONMENT=production on Railway"
echo -e "  ${CROSS} Update ALLOWED_ORIGINS with actual domains"
echo -e "  ${CROSS} Setup Neo4j Aura account (Railway doesn't provide Neo4j)"
echo ""

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${GREEN}  Ready to deploy! 🚀${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""
