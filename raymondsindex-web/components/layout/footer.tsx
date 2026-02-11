'use client';

import Link from 'next/link';
import { BarChart3 } from 'lucide-react';
import { Separator } from '@/components/ui/separator';

export function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-200">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row justify-between items-start gap-8">
          {/* Logo & Description */}
          <div className="flex flex-col gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-[#5E6AD2] text-white">
                <BarChart3 className="w-4 h-4" />
              </div>
              <span className="text-lg font-bold text-gray-900">RaymondsIndex</span>
            </Link>
            <p className="text-sm text-gray-500 max-w-xs">
              AI 기반 자본 배분 효율성 평가 지표로 투자자 관점의 기업 분석을 제공합니다.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-12">
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">서비스</h4>
              <ul className="space-y-2 text-sm text-gray-500">
                <li><Link href="/screener" className="hover:text-gray-900 transition-colors">스크리너</Link></li>
                <li><Link href="/methodology" className="hover:text-gray-900 transition-colors">Whitepaper</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-gray-800 mb-3">지원</h4>
              <ul className="space-y-2 text-sm text-gray-500">
                <li><a href="mailto:support@raymontology.com" className="hover:text-gray-900 transition-colors">문의하기</a></li>
              </ul>
            </div>
          </div>
        </div>

        <Separator className="my-6 bg-gray-200" />

        {/* Disclaimer */}
        <div className="text-xs text-gray-500 space-y-2">
          <p>
            RaymondsIndex는 공시 데이터를 기반으로 한 참고용 지표입니다.
            투자 결정의 유일한 근거로 사용하지 마시고, 반드시 전문가 상담 및 추가 조사를 병행하시기 바랍니다.
          </p>
          <p>
            &copy; {new Date().getFullYear()} RaymondsIndex. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
}
