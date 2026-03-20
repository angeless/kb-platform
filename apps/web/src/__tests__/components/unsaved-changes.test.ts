import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

/**
 * Tests for the beforeunload unsaved-changes behavior.
 * We test the pattern used in edit/page.tsx: addEventListener('beforeunload')
 * that calls preventDefault() when content differs from initial value.
 */
describe("beforeunload unsaved changes guard", () => {
  let handler: (e: BeforeUnloadEvent) => void;
  let initialContent: string;
  let currentContent: string;

  beforeEach(() => {
    initialContent = "original content";
    currentContent = "original content";

    handler = (e: BeforeUnloadEvent) => {
      if (currentContent !== initialContent) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
  });

  afterEach(() => {
    window.removeEventListener("beforeunload", handler);
  });

  it("does not prevent leaving when content is unchanged", () => {
    const event = new Event("beforeunload") as BeforeUnloadEvent;
    const preventSpy = vi.spyOn(event, "preventDefault");
    window.dispatchEvent(event);
    expect(preventSpy).not.toHaveBeenCalled();
  });

  it("prevents leaving when content is modified", () => {
    currentContent = "modified content";
    const event = new Event("beforeunload") as BeforeUnloadEvent;
    const preventSpy = vi.spyOn(event, "preventDefault");
    window.dispatchEvent(event);
    expect(preventSpy).toHaveBeenCalled();
  });

  it("does not prevent leaving after content is saved (dirty cleared)", () => {
    currentContent = "modified content";
    // Simulate save: update initial to match current
    initialContent = currentContent;

    const event = new Event("beforeunload") as BeforeUnloadEvent;
    const preventSpy = vi.spyOn(event, "preventDefault");
    window.dispatchEvent(event);
    expect(preventSpy).not.toHaveBeenCalled();
  });
});
