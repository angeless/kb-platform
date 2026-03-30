"use client";

import Link from "next/link";

interface OnboardingGuideProps {
  projectId?: string;
}

const steps = [
  { label: "创建项目", description: "创建你的第一个知识库项目", href: "/projects", icon: "1" },
  { label: "上传资料", description: "上传 PDF、文档等原始素材", href: (pid: string) => `/projects/${pid}/assets`, icon: "2" },
  { label: "查看架构", description: "AI 自动整理知识架构", href: (pid: string) => `/projects/${pid}/architectures`, icon: "3" },
  { label: "浏览 Wiki", description: "在 Wiki 中浏览结构化知识", href: (pid: string) => `/projects/${pid}/wiki`, icon: "4" },
];

export function OnboardingGuide({ projectId }: OnboardingGuideProps) {
  return (
    <div className="mb-8 rounded-xl border border-blue-200 bg-blue-50 p-6">
      <h2 className="mb-2 text-lg font-semibold text-blue-900">欢迎使用 KB Platform</h2>
      <p className="mb-6 text-sm text-blue-700">
        按以下步骤快速开始，将你的资料转化为结构化知识。
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((step) => {
          const href = typeof step.href === "function"
            ? projectId ? step.href(projectId) : "#"
            : step.href;
          const isDisabled = typeof step.href === "function" && !projectId;
          return (
            <Link
              key={step.label}
              href={href}
              aria-disabled={isDisabled}
              className={`flex items-start gap-3 rounded-lg bg-white p-4 shadow-sm transition-shadow hover:shadow-md ${isDisabled ? "pointer-events-none opacity-50" : ""}`}
            >
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-bold text-white">
                {step.icon}
              </span>
              <div>
                <div className="text-sm font-medium text-gray-900">{step.label}</div>
                <div className="text-xs text-gray-500">{step.description}</div>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
