#!/bin/bash

# =============================================================================
# Raymontology - Health Check Script
# =============================================================================
#
# Railway 배포 후 서비스 상태를 확인하는 스크립트
#
# 사용법:
#   chmod +x scripts/health-check.sh
#   ./scripts/health-check.sh https://your-backend.up.railway.app
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Icons
CHECK="✓"
CROSS="✗"
ARROW="→"

# Backend URL (명령행 인수 또는 기본값)
BACKEND_URL="${1:-https://raymontology-backend.up.railway.app}"

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${BLUE}  Raymontology - Health Check${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""
echo -e "${BLUE}Backend URL:${NC} ${BACKEND_URL}"
echo ""

# =============================================================================
# 1. Basic Health Check
# =============================================================================

echo -e "${YELLOW}[1/7] Checking Basic Health...${NC}"

HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health" || echo "000")

if [ "$HEALTH_RESPONSE" == "200" ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Health endpoint: OK (200)"

    # Get health details
    HEALTH_DETAILS=$(curl -s "${BACKEND_URL}/health")
    echo -e "  ${BLUE}${ARROW}${NC} Response: ${HEALTH_DETAILS}"
else
    echo -e "  ${RED}${CROSS}${NC} Health endpoint: FAILED (${HEALTH_RESPONSE})"
    exit 1
fi

echo ""

# =============================================================================
# 2. Root Endpoint
# =============================================================================

echo -e "${YELLOW}[2/7] Checking Root Endpoint...${NC}"

ROOT_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/" || echo "000")

if [ "$ROOT_RESPONSE" == "200" ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Root endpoint: OK (200)"
else
    echo -e "  ${RED}${CROSS}${NC} Root endpoint: FAILED (${ROOT_RESPONSE})"
fi

echo ""

# =============================================================================
# 3. API Documentation
# =============================================================================

echo -e "${YELLOW}[3/7] Checking API Documentation...${NC}"

DOCS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/docs" || echo "000")

if [ "$DOCS_RESPONSE" == "200" ]; then
    echo -e "  ${GREEN}${CHECK}${NC} API docs available at ${BACKEND_URL}/docs"
elif [ "$DOCS_RESPONSE" == "404" ]; then
    echo -e "  ${YELLOW}${ARROW}${NC} API docs disabled (production mode)"
else
    echo -e "  ${RED}${CROSS}${NC} API docs: FAILED (${DOCS_RESPONSE})"
fi

echo ""

# =============================================================================
# 4. Response Time Test
# =============================================================================

echo -e "${YELLOW}[4/7] Testing Response Time...${NC}"

START_TIME=$(date +%s%N)
curl -s "${BACKEND_URL}/health" > /dev/null
END_TIME=$(date +%s%N)

RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))

if [ $RESPONSE_TIME -lt 200 ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Response time: ${RESPONSE_TIME}ms (excellent)"
elif [ $RESPONSE_TIME -lt 500 ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Response time: ${RESPONSE_TIME}ms (good)"
elif [ $RESPONSE_TIME -lt 1000 ]; then
    echo -e "  ${YELLOW}${ARROW}${NC} Response time: ${RESPONSE_TIME}ms (acceptable)"
else
    echo -e "  ${RED}${CROSS}${NC} Response time: ${RESPONSE_TIME}ms (slow)"
fi

echo ""

# =============================================================================
# 5. CORS Headers
# =============================================================================

echo -e "${YELLOW}[5/7] Checking CORS Headers...${NC}"

CORS_HEADERS=$(curl -s -I -X OPTIONS "${BACKEND_URL}/health" | grep -i "access-control")

if [ -n "$CORS_HEADERS" ]; then
    echo -e "  ${GREEN}${CHECK}${NC} CORS headers present"
    echo "$CORS_HEADERS" | while read line; do
        echo -e "      ${line}"
    done
else
    echo -e "  ${YELLOW}${ARROW}${NC} No CORS headers (might be OK)"
fi

echo ""

# =============================================================================
# 6. SSL/TLS Certificate
# =============================================================================

echo -e "${YELLOW}[6/7] Checking SSL Certificate...${NC}"

if [[ $BACKEND_URL == https* ]]; then
    SSL_INFO=$(curl -s -vI "${BACKEND_URL}/health" 2>&1 | grep -E "SSL|subject|issuer|expire" | head -5)

    if [ -n "$SSL_INFO" ]; then
        echo -e "  ${GREEN}${CHECK}${NC} HTTPS enabled"
    else
        echo -e "  ${YELLOW}${ARROW}${NC} SSL info not available"
    fi
else
    echo -e "  ${YELLOW}${ARROW}${NC} Not using HTTPS (development only)"
fi

echo ""

# =============================================================================
# 7. Metrics Endpoint (Production Only)
# =============================================================================

echo -e "${YELLOW}[7/7] Checking Metrics Endpoint...${NC}"

METRICS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/metrics" || echo "000")

if [ "$METRICS_RESPONSE" == "200" ]; then
    echo -e "  ${GREEN}${CHECK}${NC} Metrics endpoint available (production mode)"

    # Sample metrics
    SAMPLE_METRICS=$(curl -s "${BACKEND_URL}/metrics" | head -10)
    echo -e "  ${BLUE}${ARROW}${NC} Sample metrics:"
    echo "$SAMPLE_METRICS" | while read line; do
        if [[ $line != \#* ]] && [ -n "$line" ]; then
            echo -e "      ${line}"
        fi
    done
elif [ "$METRICS_RESPONSE" == "404" ]; then
    echo -e "  ${YELLOW}${ARROW}${NC} Metrics disabled (development mode)"
else
    echo -e "  ${RED}${CROSS}${NC} Metrics endpoint: FAILED (${METRICS_RESPONSE})"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================

echo -e "${BLUE}=====================================================================${NC}"
echo -e "${GREEN}  Health Check Complete!${NC}"
echo -e "${BLUE}=====================================================================${NC}"
echo ""

if [ "$HEALTH_RESPONSE" == "200" ]; then
    echo -e "${GREEN}Status:${NC} All critical checks passed ✓"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "  1. Test API endpoints manually"
    echo -e "  2. Check Railway logs for errors"
    echo -e "  3. Verify database connections"
    echo -e "  4. Monitor Sentry for errors"
    echo -e "  5. Check Better Uptime dashboard"
    echo ""
    echo -e "${BLUE}Useful URLs:${NC}"
    echo -e "  ${ARROW} API Docs: ${BACKEND_URL}/docs"
    echo -e "  ${ARROW} Health: ${BACKEND_URL}/health"
    echo -e "  ${ARROW} Metrics: ${BACKEND_URL}/metrics"
    echo ""
    exit 0
else
    echo -e "${RED}Status:${NC} Health check failed ✗"
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    echo -e "  1. Check Railway deployment logs"
    echo -e "  2. Verify environment variables"
    echo -e "  3. Check database connectivity"
    echo -e "  4. Review Sentry errors"
    echo ""
    exit 1
fi
