"use client";

import { actionHandlers, registry } from "@/components/registry";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  ActionProvider,
  DataProvider,
  Renderer,
  VisibilityProvider,
} from "@json-render/react";
import { useState } from "react";

export default function Home() {
  const [query, setQuery] = useState("");
  const [graphTree, setGraphTree] = useState<unknown>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchGraph = async (prompt: string) => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/graph", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      if (!res.ok) return;
      const data = (await res.json()) as unknown;
      setGraphTree(data);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = () => {
    const nextQuery =
      query.trim() || "특정 지식에 대한 연관 지식들을 모두 알려줘";
    fetchGraph(nextQuery);
  };

  return (
    <DataProvider initialData={{}}>
      <VisibilityProvider>
        <ActionProvider handlers={actionHandlers}>
          <div className="min-h-screen bg-background">
            <header className="border-b bg-card">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                <div>
                  <div className="flex items-center gap-3">
                    <svg
                      width="28"
                      height="28"
                      viewBox="0 0 28 28"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      className="text-primary"
                      aria-hidden="true"
                    >
                      <circle cx="6" cy="6" r="3" fill="currentColor" />
                      <circle cx="22" cy="6" r="3" fill="currentColor" />
                      <circle cx="6" cy="22" r="3" fill="currentColor" />
                      <circle cx="22" cy="22" r="3" fill="currentColor" />
                      <circle cx="14" cy="14" r="3.5" fill="currentColor" />
                      <line
                        x1="8.6"
                        y1="8.6"
                        x2="12.2"
                        y2="12.2"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      <line
                        x1="19.4"
                        y1="8.6"
                        x2="15.8"
                        y2="12.2"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      <line
                        x1="8.6"
                        y1="19.4"
                        x2="12.2"
                        y2="15.8"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                      <line
                        x1="19.4"
                        y1="19.4"
                        x2="15.8"
                        y2="15.8"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                    <h1 className="text-2xl font-bold tracking-tight">
                      Knowledge Graph Dashboard
                    </h1>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Explore related knowledge extracted from screenshots.
                  </p>
                </div>
                <div className="flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs font-medium text-muted-foreground">
                  <span className="inline-flex h-2 w-2 rounded-full bg-primary/80" />
                  Knowledge Graph
                </div>
              </div>
            </header>

            <main className="mx-auto max-w-6xl p-6">
              <div className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Knowledge Query</CardTitle>
                    <CardDescription>
                      Ask for related knowledge nodes derived from screenshot
                      context. Results render as a graph.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Input
                        placeholder='e.g., "iTerm2"에 대한 연관 지식들을 모두 알려줘'
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
                      />
                      <Button onClick={handleSubmit} disabled={isLoading}>
                        {isLoading ? "Loading..." : "Generate Graph"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {graphTree && (
                  <div className="rounded-lg border bg-card p-6">
                    <Renderer
                      registry={registry}
                      tree={graphTree as never}
                      loading={isLoading}
                    />
                  </div>
                )}
              </div>
            </main>
          </div>
        </ActionProvider>
      </VisibilityProvider>
    </DataProvider>
  );
}
