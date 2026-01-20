"use client";

import { useState } from "react";
import {
  Renderer,
  DataProvider,
  VisibilityProvider,
  ActionProvider,
  useUIStream,
} from "@json-render/react";
import { registry, actionHandlers } from "@/components/registry";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { BarChart3 } from "lucide-react";

type TabType = "evaluation";

export default function Home() {
  const [activeTab, setActiveTab] = useState<TabType>("evaluation");
  const [evalQuery, setEvalQuery] = useState("");

  // Evaluation Dashboard stream
  const {
    tree: evalTree,
    isStreaming: isEvalLoading,
    send: sendEvalQuery,
  } = useUIStream({
    api: "/api/evaluation",
  });

  const handleEvalQuery = () => {
    sendEvalQuery(
      evalQuery.trim() ||
        "Create a comprehensive evaluation dashboard showing all metrics, recent evaluations, and agent performance"
    );
  };

  return (
    <DataProvider initialData={{}}>
      <VisibilityProvider>
        <ActionProvider handlers={actionHandlers}>
          <div className="min-h-screen bg-background">
            {/* Header */}
            <header className="border-b bg-card">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">
                    K2C Dashboard
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    AI-Powered Admin Dashboard with json-render
                  </p>
                </div>
                {/* Tab Navigation */}
                <nav className="flex gap-2">
                  <Button
                    variant={activeTab === "evaluation" ? "default" : "ghost"}
                    onClick={() => setActiveTab("evaluation")}
                    className="gap-2"
                  >
                    <BarChart3 className="h-4 w-4" />
                    Evaluation Dashboard
                  </Button>
                </nav>
              </div>
            </header>

            <main className="mx-auto max-w-6xl p-6">
              {/* Evaluation Dashboard Tab */}
              {activeTab === "evaluation" && (
                <div className="space-y-6">
                  {/* Query Input */}
                  <Card>
                    <CardHeader>
                      <CardTitle>Evaluation Dashboard</CardTitle>
                      <CardDescription>
                        View agent evaluation results from the Evaluation Store.
                        Ask questions about the data or generate custom views.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex gap-2">
                        <Input
                          placeholder="e.g., Show me failed evaluations from today, or just click Generate"
                          value={evalQuery}
                          onChange={(e) => setEvalQuery(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === "Enter" && handleEvalQuery()
                          }
                        />
                        <Button
                          onClick={handleEvalQuery}
                          disabled={isEvalLoading}
                        >
                          {isEvalLoading ? "Loading..." : "Generate Dashboard"}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Rendered Dashboard */}
                  {evalTree && (
                    <div className="rounded-lg border bg-card p-6">
                      <Renderer
                        registry={registry}
                        tree={evalTree}
                        loading={isEvalLoading}
                      />
                    </div>
                  )}

                  {/* JSON Preview (collapsible) */}
                  {evalTree && (
                    <details className="rounded-lg border">
                      <summary className="cursor-pointer px-4 py-3 font-medium hover:bg-muted/50">
                        View JSON Structure
                      </summary>
                      <pre className="overflow-auto bg-muted/30 p-4 text-xs">
                        {JSON.stringify(evalTree, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              )}

            </main>
          </div>
        </ActionProvider>
      </VisibilityProvider>
    </DataProvider>
  );
}
