#!/bin/bash
while true; do
  clear
  echo "=== CB 공시 수집 진행 상황 ==="
  echo ""
  tail -30 cb_collection_full.log | grep -E "(진행:|CB 발행 회사:|발견된 CB 공시:|에러:)" || echo "아직 진행 상황 없음"
  echo ""
  echo "최근 발견된 CB 공시:"
  tail -10 cb_collection_full.log | grep "CB 공시 발견" || echo "최근 발견 없음"
  echo ""
  echo "$(date) - 5분마다 업데이트"
  sleep 300
done
