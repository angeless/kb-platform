import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StatusBadge } from "@/components/status-badge";

describe("StatusBadge", () => {
  it("renders Chinese label for known status", () => {
    render(<StatusBadge status="draft" />);
    expect(screen.getByText("草稿")).toBeInTheDocument();
  });

  it("renders Chinese label for published status", () => {
    render(<StatusBadge status="published" />);
    expect(screen.getByText("已发布")).toBeInTheDocument();
  });

  it("falls back to raw status for unknown values", () => {
    render(<StatusBadge status="custom_status" />);
    expect(screen.getByText("custom_status")).toBeInTheDocument();
  });
});
