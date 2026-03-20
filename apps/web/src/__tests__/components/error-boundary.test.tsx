import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ErrorBoundary } from "@/components/error-boundary";

function GoodChild() {
  return <div>正常内容</div>;
}

function BadChild(): JSX.Element {
  throw new Error("渲染爆炸了");
}

describe("ErrorBoundary", () => {
  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("正常内容")).toBeInTheDocument();
  });

  it("renders error page when child throws", () => {
    // Suppress React's console.error for expected error boundary logs
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );
    expect(screen.getByText("页面出现错误")).toBeInTheDocument();
    expect(screen.getByText("请刷新重试")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "刷新页面" })).toBeInTheDocument();

    spy.mockRestore();
  });

  it("logs error to console", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    const errorCalls = spy.mock.calls.filter(
      (call) => typeof call[0] === "string" && call[0].includes("[ErrorBoundary]"),
    );
    expect(errorCalls.length).toBeGreaterThan(0);

    spy.mockRestore();
  });
});
