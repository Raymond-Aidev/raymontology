#!/bin/bash
# 모든 앱 빌드 검증 스크립트
# 사용: ./scripts/build-all.sh

set -e  # 오류 발생 시 즉시 종료

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
FAILED=0

echo "========================================"
echo "멀티 앱 빌드 검증 시작"
echo "========================================"
echo ""

# 1. Frontend (RaymondsRisk 웹)
echo "[1/3] Frontend (RaymondsRisk 웹) 빌드 중..."
cd "$ROOT_DIR/frontend"
if npm run build > /dev/null 2>&1; then
    echo "✅ Frontend 빌드 성공"
else
    echo "❌ Frontend 빌드 실패"
    FAILED=1
fi
echo ""

# 2. RaymondsIndex 웹
echo "[2/3] RaymondsIndex 웹 빌드 중..."
cd "$ROOT_DIR/raymondsindex-web"
if npm run build > /dev/null 2>&1; then
    echo "✅ RaymondsIndex 빌드 성공"
else
    echo "❌ RaymondsIndex 빌드 실패"
    FAILED=1
fi
echo ""

# 3. 앱인토스
echo "[3/3] 앱인토스 빌드 중..."
cd "$ROOT_DIR/raymondsrisk-app"
if npm run build > /dev/null 2>&1; then
    echo "✅ 앱인토스 빌드 성공"
else
    echo "❌ 앱인토스 빌드 실패"
    FAILED=1
fi
echo ""

echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo "✅ 모든 앱 빌드 성공!"
    exit 0
else
    echo "❌ 일부 앱 빌드 실패 - 커밋 전 수정 필요"
    exit 1
fi
