"use client";

import { useEffect, useRef, useState } from "react";
import { MessageSquare, Send, Loader2, AlertCircle, User, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { askQuestion } from "@/lib/api";
import type { QAResponse } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  gameIds?: string[];
  error?: boolean;
  loading?: boolean;
}

const STARTER_QUESTIONS = [
  "When did we lose map control in last week's games?",
  "How does our jungle pathing compare game 1 vs game 3?",
  "What did we trade for Baron and was it worth it?",
  "Which lane had the biggest impact on outcomes this week?",
];

function MessageBubble({ msg }: { msg: Message }) {
  const isUser = msg.role === "user";

  return (
    <div className={cn("flex gap-3 items-start", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border",
          isUser
            ? "border-primary/30 bg-primary/10 text-primary"
            : "border-border bg-muted text-muted-foreground"
        )}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[78%] rounded-lg px-4 py-3 text-sm",
          isUser
            ? "bg-primary/10 border border-primary/20 text-foreground"
            : msg.error
            ? "bg-destructive/10 border border-destructive/30 text-destructive"
            : "bg-card border border-border text-foreground"
        )}
      >
        {msg.loading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span className="text-xs">Thinking…</span>
          </div>
        ) : msg.error ? (
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{msg.content}</span>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="leading-relaxed">{msg.content}</p>
            {msg.gameIds && msg.gameIds.length > 0 && (
              <p className="text-xs text-muted-foreground border-t border-border pt-2">
                References:{" "}
                {msg.gameIds.map((id, i) => (
                  <span key={id}>
                    {i > 0 && ", "}
                    <a
                      href={`/games/${encodeURIComponent(id)}`}
                      className="text-primary hover:underline"
                    >
                      {id}
                    </a>
                  </span>
                ))}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AskPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (question: string) => {
    if (!question.trim() || pending) return;

    const userMsg: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question.trim(),
    };
    const loadingMsg: Message = {
      id: `a-${Date.now()}`,
      role: "assistant",
      content: "",
      loading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInput("");
    setPending(true);

    let response: QAResponse | null = null;
    let errorText: string | null = null;

    try {
      response = await askQuestion(question.trim());
    } catch (e: unknown) {
      errorText = e instanceof Error ? e.message : "Request failed";
    } finally {
      setPending(false);
    }

    setMessages((prev) =>
      prev.map((m) =>
        m.id === loadingMsg.id
          ? {
              ...m,
              loading: false,
              content: response?.answer ?? errorText ?? "Unknown error",
              gameIds: response?.game_ids_referenced,
              error: errorText !== null,
            }
          : m
      )
    );
  };

  const handleSubmit = () => sendMessage(input);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-screen-md flex-col px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5 shrink-0">
        <MessageSquare className="h-5 w-5 text-primary" />
        <div>
          <h1 className="text-lg font-semibold">Scrim Q&amp;A</h1>
          <p className="text-xs text-muted-foreground">
            Ask anything about your scrim history
          </p>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ScrollArea className="h-full pr-2">
          <div className="space-y-4 py-2">
            {messages.length === 0 && (
              <div className="py-6">
                <p className="text-center text-sm text-muted-foreground mb-5">
                  No questions yet. Try one of these:
                </p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {STARTER_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="rounded-lg border border-border bg-card px-3 py-2.5 text-left text-xs text-muted-foreground transition-colors hover:border-primary/30 hover:text-foreground"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        </ScrollArea>
      </div>

      {/* Input bar */}
      <div className="shrink-0 mt-4 flex gap-2">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your scrims… (Enter to send, Shift+Enter for newline)"
          rows={2}
          disabled={pending}
          className={cn(
            "flex-1 resize-none rounded-lg border border-input bg-card px-3 py-2 text-sm placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        />
        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || pending}
          className="h-auto self-end"
        >
          {pending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
