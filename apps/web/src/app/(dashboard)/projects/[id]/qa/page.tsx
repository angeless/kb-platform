"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Source {
  doc_id: string;
  title: string;
  snippet: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
  error?: boolean;
}

export default function QAPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setIsLoading(true);

    const assistantIdx = messages.length + 1; // index of the new assistant message
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", isStreaming: true },
    ]);

    try {
      const resp = await fetch(`${API_BASE}/v1/qa/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          project_id: projectId,
          question,
          stream: true,
          top_k: 5,
        }),
      });

      if (!resp.ok) {
        const errText = await resp.text();
        let errMsg = "请求失败";
        try {
          const errJson = JSON.parse(errText);
          errMsg = errJson.message || errMsg;
        } catch {
          // keep default
        }
        setMessages((prev) =>
          prev.map((m, i) =>
            i === assistantIdx
              ? { ...m, content: errMsg, isStreaming: false, error: true }
              : m
          )
        );
        setIsLoading(false);
        return;
      }

      const reader = resp.body?.getReader();
      if (!reader) {
        setIsLoading(false);
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let sources: Source[] = [];

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const jsonStr = line.slice(6);
          try {
            const event = JSON.parse(jsonStr);
            if (event.type === "chunk") {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === assistantIdx
                    ? { ...m, content: m.content + event.content }
                    : m
                )
              );
            } else if (event.type === "sources") {
              sources = event.sources || [];
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === assistantIdx
                    ? { ...m, isStreaming: false, sources }
                    : m
                )
              );
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((m, i) =>
                  i === assistantIdx
                    ? {
                        ...m,
                        content: event.message || "AI 服务出错",
                        isStreaming: false,
                        error: true,
                      }
                    : m
                )
              );
            }
          } catch {
            // skip malformed SSE lines
          }
        }
      }

      // Ensure streaming flag is cleared
      setMessages((prev) =>
        prev.map((m, i) =>
          i === assistantIdx && m.isStreaming
            ? { ...m, isStreaming: false, sources }
            : m
        )
      );
    } catch {
      setMessages((prev) =>
        prev.map((m, i) =>
          i === assistantIdx
            ? {
                ...m,
                content: "网络连接失败，请检查网络后重试",
                isStreaming: false,
                error: true,
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, messages.length, projectId]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div className="text-center text-gray-400">
              <div className="mb-2 text-4xl">💬</div>
              <p className="text-lg font-medium">向本项目的知识库提问</p>
              <p className="mt-1 text-sm">AI 将基于已有文档回答</p>
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-primary-600 text-white"
                      : msg.error
                        ? "border border-red-200 bg-red-50 text-red-700"
                        : "border border-gray-200 bg-white text-gray-800"
                  }`}
                >
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {msg.content}
                    {msg.isStreaming && (
                      <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-gray-400" />
                    )}
                  </div>

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && !msg.isStreaming && (
                    <div className="mt-3 border-t border-gray-100 pt-2">
                      <div className="mb-1 text-xs font-medium text-gray-500">
                        引用来源
                      </div>
                      <div className="space-y-1">
                        {msg.sources.map((src, si) => (
                          <div
                            key={si}
                            className="rounded bg-gray-50 px-2 py-1 text-xs text-gray-600"
                          >
                            {src.title}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-gray-200 bg-white px-4 py-3">
        <div className="mx-auto flex max-w-3xl gap-2">
          <textarea
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            rows={1}
            placeholder="输入你的问题..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="rounded-xl bg-primary-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-primary-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {isLoading ? "等待中..." : "发送"}
          </button>
        </div>
      </div>
    </div>
  );
}
