'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';

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

// 컴팩트 버전 (그리드 레이아웃용)
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
          <span className="text-[11px] font-medium text-white px-1 flex-1 text-center truncate">
            {format(minValue)}
          </span>
        </div>

        <span className="text-zinc-600 text-[10px]">~</span>

        {/* 최대값 */}
        <div className="flex items-center bg-zinc-900/50 rounded border border-zinc-600/50 flex-1">
          <ArrowButtons
            onUp={() => handleMaxChange(1)}
            onDown={() => handleMaxChange(-1)}
          />
          <span className="text-[11px] font-medium text-white px-1 flex-1 text-center truncate">
            {format(maxValue)}
          </span>
        </div>
      </div>
    </div>
  );
}
