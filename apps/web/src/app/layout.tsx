import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KB Platform — AI 知识系统构建平台",
  description: "将多模态原始资料转化为结构化、可追溯、可被 AI 使用的知识系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        {children}
      </body>
    </html>
  );
}
