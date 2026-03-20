import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MarkdownView } from "@/components/markdown-view";

describe("MarkdownView", () => {
  it("renders normal heading", () => {
    render(<MarkdownView content="# Hello World" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Hello World");
  });

  it("renders normal link", () => {
    render(<MarkdownView content="[example](https://example.com)" />);
    const link = screen.getByRole("link", { name: "example" });
    expect(link).toHaveAttribute("href", "https://example.com");
  });

  it("renders inline code", () => {
    render(<MarkdownView content="use `console.log`" />);
    expect(screen.getByText("console.log")).toBeInTheDocument();
  });

  it("renders list items", () => {
    render(<MarkdownView content={"- item one\n- item two"} />);
    expect(screen.getByText("item one")).toBeInTheDocument();
    expect(screen.getByText("item two")).toBeInTheDocument();
  });

  it("does not render script tags (XSS)", () => {
    const { container } = render(
      <MarkdownView content='<script>alert("xss")</script>' />
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.innerHTML).not.toContain("alert");
  });

  it("does not render onerror attribute (XSS)", () => {
    const { container } = render(
      <MarkdownView content='<img onerror="alert(1)" src="x">' />
    );
    expect(container.innerHTML).not.toContain("onerror");
  });

  it("does not render onclick attribute (XSS)", () => {
    const { container } = render(
      <MarkdownView content='<div onclick="alert(1)">click me</div>' />
    );
    expect(container.innerHTML).not.toContain("onclick");
  });

  it("applies custom className", () => {
    const { container } = render(
      <MarkdownView content="test" className="custom-class" />
    );
    expect(container.firstChild).toHaveClass("custom-class");
  });
});
