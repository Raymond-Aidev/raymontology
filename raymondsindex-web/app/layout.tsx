import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/layout/header";
import { Footer } from "@/components/layout/footer";
import { Providers } from "@/components/providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin", "latin-ext"],
  display: "swap", // 폰트 로딩 중에도 시스템 폰트로 텍스트 표시
  fallback: [
    "Apple SD Gothic Neo",  // macOS 한글
    "Malgun Gothic",        // Windows 한글
    "Noto Sans KR",         // Android/Linux 한글
    "system-ui",
    "-apple-system",
    "sans-serif",
  ],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin", "latin-ext"],
  display: "swap",
  fallback: [
    "SF Mono",
    "Monaco",
    "Consolas",
    "Liberation Mono",
    "Courier New",
    "monospace",
  ],
});

export const metadata: Metadata = {
  title: "RaymondsIndex 2025 - 자본 배분 효율성 평가",
  description: "당신의 투자금, 제대로 쓰이고 있습니까? AI 기반 자본 배분 효율성 평가 지표",
  openGraph: {
    title: "RaymondsIndex 2025",
    description: "AI 기반 자본 배분 효율성 평가 지표",
    siteName: "RaymondsIndex",
    locale: "ko_KR",
    type: "website",
  },
  other: {
    'theme-color': '#FFFFFF',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <head>
        {/* Google Fonts preconnect - 폰트 로딩 속도 개선 */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Theme color for mobile browsers */}
        <meta name="theme-color" content="#FFFFFF" />
        <meta name="color-scheme" content="light" />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen flex flex-col bg-white text-gray-900`}
      >
        <Providers>
          <Header />
          <main className="flex-1 bg-white">
            {children}
          </main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
