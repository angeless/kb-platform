import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md text-center">
        <div className="mb-6 text-6xl text-gray-300">404</div>
        <h1 className="mb-2 text-2xl font-bold text-gray-900">页面不存在</h1>
        <p className="mb-8 text-gray-500">您访问的页面可能已被移除或地址输入有误。</p>
        <Link
          href="/projects"
          className="inline-block rounded-lg bg-primary-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-primary-700"
        >
          返回首页
        </Link>
      </div>
    </div>
  );
}
