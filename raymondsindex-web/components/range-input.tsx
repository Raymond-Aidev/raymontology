'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

// 입력값을 숫자로 파싱 (억/조 단위 지원)
function parseInputValue(input: string, unit: string): number | null {
  if (!input.trim()) return null;

  // 공백 제거
  const cleaned = input.trim().replace(/,/g, '');

  // % 단위인 경우 그냥 숫자만 파싱
  if (unit === '%') {
    const num = parseFloat(cleaned.replace('%', ''));
    return isNaN(num) ? null : num;
  }

  // 억/조 단위 처리
  if (cleaned.includes('조')) {
    const num = parseFloat(cleaned.replace('조', '').replace('억', ''));
    return isNaN(num) ? null : num * 10000; // 조 -> 억 변환
  }

  if (cleaned.includes('억')) {
    const num = parseFloat(cleaned.replace('억', ''));
    return isNaN(num) ? null : num;
  }

  // 숫자만 있는 경우 (억 단위로 간주)
  const num = parseFloat(cleaned);
  return isNaN(num) ? null : num;
}

interface RangeInputProps {
  label: string;
  minValue: number;
  maxValue: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  formatValue?: (value: number) => string;
  onChange: (min: number, max: number) => void;
  tooltip?: string;
}

export function RangeInput({
  label,
  minValue,
  maxValue,
  min,
  max,
  step,
  unit = '',
  formatValue,
  onChange,
  tooltip,
}: RangeInputProps) {
  const [holdInterval, setHoldInterval] = useState<NodeJS.Timeout | null>(null);
  const holdTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const accelerationRef = useRef(1);

  // 값 포맷팅
  const format = formatValue || ((v: number) => `${v.toLocaleString()}${unit}`);

  // 값 변경 핸들러
  const handleMinChange = useCallback((delta: number) => {
    const newMin = Math.max(min, Math.min(maxValue - step, minValue + delta * step * accelerationRef.current));
    onChange(newMin, maxValue);
  }, [minValue, maxValue, min, step, onChange]);

  const handleMaxChange = useCallback((delta: number) => {
    const newMax = Math.max(minValue + step, Math.min(max, maxValue + delta * step * accelerationRef.current));
    onChange(minValue, newMax);
  }, [minValue, maxValue, max, step, onChange]);

  // 홀드 시작
  const startHold = useCallback((handler: () => void) => {
    accelerationRef.current = 1;
    handler();

    // 초기 딜레이 후 반복
    holdTimeoutRef.current = setTimeout(() => {
      const interval = setInterval(() => {
        // 시간이 지날수록 가속
        accelerationRef.current = Math.min(10, accelerationRef.current + 0.5);
        handler();
      }, 80);
      setHoldInterval(interval);
    }, 300);
  }, []);

  // 홀드 종료
  const stopHold = useCallback(() => {
    if (holdTimeoutRef.current) {
      clearTimeout(holdTimeoutRef.current);
      holdTimeoutRef.current = null;
    }
    if (holdInterval) {
      clearInterval(holdInterval);
      setHoldInterval(null);
    }
    accelerationRef.current = 1;
  }, [holdInterval]);

  // 컴포넌트 언마운트 시 정리
  useEffect(() => {
    return () => {
      stopHold();
    };
  }, [stopHold]);

  return (
    <div className="flex items-center gap-2">
      {/* 라벨 */}
      <div className="w-24 shrink-0">
        <span className="text-xs text-zinc-400" title={tooltip}>
          {label}
        </span>
      </div>

      {/* 최소값 조절 */}
      <div className="flex items-center bg-zinc-800 rounded border border-zinc-700">
        <span className="text-xs text-zinc-500 px-1.5">최소</span>
        <div className="flex flex-col border-l border-zinc-700">
          <button
            type="button"
            className="px-1 py-0 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
            onMouseDown={() => startHold(() => handleMinChange(1))}
            onMouseUp={stopHold}
            onMouseLeave={stopHold}
            onTouchStart={() => startHold(() => handleMinChange(1))}
            onTouchEnd={stopHold}
          >
            <ChevronUp className="w-3 h-3" />
          </button>
          <button
            type="button"
            className="px-1 py-0 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
            onMouseDown={() => startHold(() => handleMinChange(-1))}
            onMouseUp={stopHold}
            onMouseLeave={stopHold}
            onTouchStart={() => startHold(() => handleMinChange(-1))}
            onTouchEnd={stopHold}
          >
            <ChevronDown className="w-3 h-3" />
          </button>
        </div>
        <span className="text-xs font-medium text-white px-2 min-w-[60px] text-right">
          {format(minValue)}
        </span>
      </div>

      <span className="text-zinc-600">~</span>

      {/* 최대값 조절 */}
      <div className="flex items-center bg-zinc-800 rounded border border-zinc-700">
        <span className="text-xs text-zinc-500 px-1.5">최대</span>
        <div className="flex flex-col border-l border-zinc-700">
          <button
            type="button"
            className="px-1 py-0 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
            onMouseDown={() => startHold(() => handleMaxChange(1))}
            onMouseUp={stopHold}
            onMouseLeave={stopHold}
            onTouchStart={() => startHold(() => handleMaxChange(1))}
            onTouchEnd={stopHold}
          >
            <ChevronUp className="w-3 h-3" />
          </button>
          <button
            type="button"
            className="px-1 py-0 hover:bg-zinc-700 text-zinc-400 hover:text-white transition-colors"
            onMouseDown={() => startHold(() => handleMaxChange(-1))}
            onMouseUp={stopHold}
            onMouseLeave={stopHold}
            onTouchStart={() => startHold(() => handleMaxChange(-1))}
            onTouchEnd={stopHold}
          >
            <ChevronDown className="w-3 h-3" />
          </button>
        </div>
        <span className="text-xs font-medium text-white px-2 min-w-[60px] text-right">
          {format(maxValue)}
        </span>
      </div>
    </div>
  );
}

// 컴팩트 버전 (그리드 레이아웃용) - 클릭하여 직접 입력 지원
export function CompactRangeInput({
  label,
  minValue,
  maxValue,
  min,
  max,
  step,
  unit = '',
  formatValue,
  onChange,
  tooltip,
}: RangeInputProps) {
  const [holdInterval, setHoldInterval] = useState<NodeJS.Timeout | null>(null);
  const holdTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const accelerationRef = useRef(1);

  // 편집 모드 상태
  const [editingMin, setEditingMin] = useState(false);
  const [editingMax, setEditingMax] = useState(false);
  const [minInputValue, setMinInputValue] = useState('');
  const [maxInputValue, setMaxInputValue] = useState('');
  const minInputRef = useRef<HTMLInputElement>(null);
  const maxInputRef = useRef<HTMLInputElement>(null);

  const format = formatValue || ((v: number) => `${v.toLocaleString()}${unit}`);

  const handleMinChange = useCallback((delta: number) => {
    const newMin = Math.max(min, Math.min(maxValue - step, minValue + delta * step * accelerationRef.current));
    onChange(newMin, maxValue);
  }, [minValue, maxValue, min, step, onChange]);

  const handleMaxChange = useCallback((delta: number) => {
    const newMax = Math.max(minValue + step, Math.min(max, maxValue + delta * step * accelerationRef.current));
    onChange(minValue, newMax);
  }, [minValue, maxValue, max, step, onChange]);

  const startHold = useCallback((handler: () => void) => {
    accelerationRef.current = 1;
    handler();

    holdTimeoutRef.current = setTimeout(() => {
      const interval = setInterval(() => {
        accelerationRef.current = Math.min(10, accelerationRef.current + 0.5);
        handler();
      }, 80);
      setHoldInterval(interval);
    }, 300);
  }, []);

  const stopHold = useCallback(() => {
    if (holdTimeoutRef.current) {
      clearTimeout(holdTimeoutRef.current);
      holdTimeoutRef.current = null;
    }
    if (holdInterval) {
      clearInterval(holdInterval);
      setHoldInterval(null);
    }
    accelerationRef.current = 1;
  }, [holdInterval]);

  useEffect(() => {
    return () => {
      stopHold();
    };
  }, [stopHold]);

  // 편집 모드 진입 시 포커스
  useEffect(() => {
    if (editingMin && minInputRef.current) {
      minInputRef.current.focus();
      minInputRef.current.select();
    }
  }, [editingMin]);

  useEffect(() => {
    if (editingMax && maxInputRef.current) {
      maxInputRef.current.focus();
      maxInputRef.current.select();
    }
  }, [editingMax]);

  // 최소값 편집 시작
  const startEditingMin = () => {
    setMinInputValue(minValue.toString());
    setEditingMin(true);
  };

  // 최대값 편집 시작
  const startEditingMax = () => {
    setMaxInputValue(maxValue.toString());
    setEditingMax(true);
  };

  // 최소값 입력 완료 처리
  const commitMinValue = () => {
    const parsed = parseInputValue(minInputValue, unit);

    // 유효하지 않은 입력이면 무시하고 원래 값 유지
    if (parsed === null) {
      setEditingMin(false);
      return;
    }

    // step 단위로 반올림
    const rounded = Math.round(parsed / step) * step;

    // 범위 검증: min 이상, maxValue 미만이어야 함
    if (rounded < min || rounded >= maxValue) {
      // 범위 벗어남 - 무효 처리, 아무 반응 없이 원래 값 유지
      setEditingMin(false);
      return;
    }

    // 유효한 값이면 적용
    onChange(rounded, maxValue);
    setEditingMin(false);
  };

  // 최대값 입력 완료 처리
  const commitMaxValue = () => {
    const parsed = parseInputValue(maxInputValue, unit);

    // 유효하지 않은 입력이면 무시하고 원래 값 유지
    if (parsed === null) {
      setEditingMax(false);
      return;
    }

    // step 단위로 반올림
    const rounded = Math.round(parsed / step) * step;

    // 범위 검증: max 이하, minValue 초과여야 함
    if (rounded > max || rounded <= minValue) {
      // 범위 벗어남 - 무효 처리, 아무 반응 없이 원래 값 유지
      setEditingMax(false);
      return;
    }

    // 유효한 값이면 적용
    onChange(minValue, rounded);
    setEditingMax(false);
  };

  // 키보드 이벤트 처리
  const handleMinKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      commitMinValue();
    } else if (e.key === 'Escape') {
      setEditingMin(false);
    }
  };

  const handleMaxKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      commitMaxValue();
    } else if (e.key === 'Escape') {
      setEditingMax(false);
    }
  };

  // 화살표 버튼 컴포넌트
  const ArrowButtons = ({ onUp, onDown }: { onUp: () => void; onDown: () => void }) => (
    <div className="flex flex-col">
      <button
        type="button"
        className="px-0.5 hover:bg-zinc-600 text-zinc-400 hover:text-white transition-colors rounded-t"
        onMouseDown={() => startHold(onUp)}
        onMouseUp={stopHold}
        onMouseLeave={stopHold}
        onTouchStart={() => startHold(onUp)}
        onTouchEnd={stopHold}
      >
        <ChevronUp className="w-3 h-3" />
      </button>
      <button
        type="button"
        className="px-0.5 hover:bg-zinc-600 text-zinc-400 hover:text-white transition-colors rounded-b"
        onMouseDown={() => startHold(onDown)}
        onMouseUp={stopHold}
        onMouseLeave={stopHold}
        onTouchStart={() => startHold(onDown)}
        onTouchEnd={stopHold}
      >
        <ChevronDown className="w-3 h-3" />
      </button>
    </div>
  );

  return (
    <div className="bg-zinc-800/50 rounded-lg p-2 border border-zinc-700/50">
      {/* 라벨 */}
      <div className="text-[10px] text-zinc-500 mb-1.5 truncate" title={tooltip}>
        {label}
      </div>

      {/* 입력 영역 */}
      <div className="flex items-center gap-1">
        {/* 최소값 */}
        <div className="flex items-center bg-zinc-900/50 rounded border border-zinc-600/50 flex-1">
          <ArrowButtons
            onUp={() => handleMinChange(1)}
            onDown={() => handleMinChange(-1)}
          />
          {editingMin ? (
            <input
              ref={minInputRef}
              type="text"
              value={minInputValue}
              onChange={(e) => setMinInputValue(e.target.value)}
              onBlur={commitMinValue}
              onKeyDown={handleMinKeyDown}
              className="text-[11px] font-medium text-white px-1 flex-1 text-center bg-transparent outline-none w-full min-w-0"
              placeholder={minValue.toString()}
            />
          ) : (
            <span
              onClick={startEditingMin}
              className="text-[11px] font-medium text-white px-1 flex-1 text-center truncate cursor-pointer hover:bg-zinc-700/50 rounded transition-colors"
              title="클릭하여 직접 입력"
            >
              {format(minValue)}
            </span>
          )}
        </div>

        <span className="text-zinc-600 text-[10px]">~</span>

        {/* 최대값 */}
        <div className="flex items-center bg-zinc-900/50 rounded border border-zinc-600/50 flex-1">
          <ArrowButtons
            onUp={() => handleMaxChange(1)}
            onDown={() => handleMaxChange(-1)}
          />
          {editingMax ? (
            <input
              ref={maxInputRef}
              type="text"
              value={maxInputValue}
              onChange={(e) => setMaxInputValue(e.target.value)}
              onBlur={commitMaxValue}
              onKeyDown={handleMaxKeyDown}
              className="text-[11px] font-medium text-white px-1 flex-1 text-center bg-transparent outline-none w-full min-w-0"
              placeholder={maxValue.toString()}
            />
          ) : (
            <span
              onClick={startEditingMax}
              className="text-[11px] font-medium text-white px-1 flex-1 text-center truncate cursor-pointer hover:bg-zinc-700/50 rounded transition-colors"
              title="클릭하여 직접 입력"
            >
              {format(maxValue)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
