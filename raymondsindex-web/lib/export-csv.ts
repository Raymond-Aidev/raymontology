/**
 * CSV 내보내기 유틸리티
 * 스크리너 결과를 CSV 파일로 다운로드
 */

import type { RaymondsIndexResponse } from './types';

interface ExportOptions {
  filename?: string;
  includeSubIndices?: boolean;
}

/**
 * RaymondsIndexResponse 배열을 CSV 문자열로 변환
 */
export function convertToCSV(
  items: RaymondsIndexResponse[],
  options: ExportOptions = {}
): string {
  const { includeSubIndices = true } = options;

  // 헤더 정의
  const baseHeaders = [
    '순위',
    '기업명',
    '종목코드',
    '시장',
    '등급',
    '종합점수',
  ];

  const subIndexHeaders = includeSubIndices
    ? ['CEI', 'RII', 'CGI', 'MAI', '투자괴리율(%)']
    : [];

  const headers = [...baseHeaders, ...subIndexHeaders];

  // 안전한 숫자 포맷팅 헬퍼
  const safeToFixed = (value: number | null | undefined, decimals: number = 1): string => {
    if (value === null || value === undefined || typeof value !== 'number' || isNaN(value)) {
      return '';
    }
    return value.toFixed(decimals);
  };

  // 데이터 행 생성 (방어적 코딩)
  const rows = items.map((item, index) => {
    const baseRow = [
      index + 1,
      item.company_name ?? '',
      item.stock_code ?? '',
      item.market ?? '',
      item.grade ?? '',
      safeToFixed(item.total_score),
    ];

    const subIndexRow = includeSubIndices
      ? [
          safeToFixed(item.cei_score),
          safeToFixed(item.rii_score),
          safeToFixed(item.cgi_score),
          safeToFixed(item.mai_score),
          safeToFixed(item.investment_gap),
        ]
      : [];

    return [...baseRow, ...subIndexRow];
  });

  // CSV 문자열 생성 (BOM 포함 - 한글 엑셀 호환)
  const BOM = '\uFEFF';
  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row
        .map((cell) => {
          // 쉼표나 따옴표가 포함된 셀은 따옴표로 감싸기
          const cellStr = String(cell);
          if (cellStr.includes(',') || cellStr.includes('"') || cellStr.includes('\n')) {
            return `"${cellStr.replace(/"/g, '""')}"`;
          }
          return cellStr;
        })
        .join(',')
    ),
  ].join('\n');

  return BOM + csvContent;
}

/**
 * CSV 파일 다운로드 트리거
 */
export function downloadCSV(
  items: RaymondsIndexResponse[],
  options: ExportOptions = {}
): void {
  const {
    filename = `raymondsindex_${new Date().toISOString().split('T')[0]}.csv`,
  } = options;

  const csvContent = convertToCSV(items, options);

  // Blob 생성 및 다운로드
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // 메모리 정리
  URL.revokeObjectURL(url);
}

/**
 * 전체 데이터 내보내기 (페이지네이션 무시)
 * API에서 전체 데이터를 가져와 CSV로 내보내기
 */
export async function exportAllToCSV(
  fetchAllFn: () => Promise<RaymondsIndexResponse[]>,
  options: ExportOptions = {}
): Promise<void> {
  try {
    const allItems = await fetchAllFn();
    downloadCSV(allItems, options);
  } catch (error) {
    console.error('CSV 내보내기 실패:', error);
    throw error;
  }
}
