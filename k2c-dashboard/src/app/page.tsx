"use client";

import { useState } from "react";
import {
  Renderer,
  DataProvider,
  VisibilityProvider,
  ActionProvider,
  useUIStream,
} from "@json-render/react";
import type { UITree } from "@json-render/core";
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

// Sample UI tree to demonstrate json-render
const sampleUITree: UITree = {
  root: "container-1",
  elements: {
    "container-1": {
      key: "container-1",
      type: "Container",
      props: { className: "space-y-4" },
      children: ["card-1"],
    },
    "card-1": {
      key: "card-1",
      type: "Card",
      props: {},
      children: ["header-1", "content-1"],
      parentKey: "container-1",
    },
    "header-1": {
      key: "header-1",
      type: "CardHeader",
      props: {},
      children: ["title-1", "description-1"],
      parentKey: "card-1",
    },
    "title-1": {
      key: "title-1",
      type: "CardTitle",
      props: { text: "Welcome to K2C Dashboard" },
      parentKey: "header-1",
    },
    "description-1": {
      key: "description-1",
      type: "CardDescription",
      props: {
        text: "This UI is rendered using json-render with shadcn/ui components",
      },
      parentKey: "header-1",
    },
    "content-1": {
      key: "content-1",
      type: "CardContent",
      props: {},
      children: ["flex-1"],
      parentKey: "card-1",
    },
    "flex-1": {
      key: "flex-1",
      type: "Flex",
      props: { direction: "col", gap: 4 },
      children: ["text-1", "flex-2"],
      parentKey: "content-1",
    },
    "text-1": {
      key: "text-1",
      type: "Text",
      props: {
        text: "json-render allows you to define UI as JSON and render it with React components.",
        className: "text-muted-foreground",
      },
      parentKey: "flex-1",
    },
    "flex-2": {
      key: "flex-2",
      type: "Flex",
      props: { gap: 2 },
      children: ["button-1", "button-2", "button-3"],
      parentKey: "flex-1",
    },
    "button-1": {
      key: "button-1",
      type: "Button",
      props: { text: "Primary", variant: "default" },
      parentKey: "flex-2",
    },
    "button-2": {
      key: "button-2",
      type: "Button",
      props: { text: "Secondary", variant: "secondary" },
      parentKey: "flex-2",
    },
    "button-3": {
      key: "button-3",
      type: "Button",
      props: { text: "Outline", variant: "outline" },
      parentKey: "flex-2",
    },
  },
};

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const { tree, isStreaming, send } = useUIStream({
    api: "/api/generate",
  });

  const handleGenerate = () => {
    if (!prompt.trim()) return;
    send(prompt);
  };

  return (
    <DataProvider initialData={{}}>
      <VisibilityProvider>
        <ActionProvider handlers={actionHandlers}>
          <div className="min-h-screen bg-background p-8">
            <div className="mx-auto max-w-4xl space-y-8">
              <header className="text-center">
                <h1 className="text-4xl font-bold tracking-tight">
                  K2C Dashboard
                </h1>
                <p className="mt-2 text-muted-foreground">
                  json-render + shadcn/ui Demo
                </p>
              </header>

              {/* Sample UI Section */}
              <section>
                <h2 className="mb-4 text-2xl font-semibold">
                  Sample UI (Static)
                </h2>
                <Renderer registry={registry} tree={sampleUITree} />
              </section>

              {/* AI Generator Section */}
              <section>
                <Card>
                  <CardHeader>
                    <CardTitle>Generate UI with AI</CardTitle>
                    <CardDescription>
                      Describe the UI you want to create and let AI generate it
                      for you
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex gap-2">
                      <Input
                        placeholder="e.g., Create a login form with email and password fields"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
                      />
                      <Button onClick={handleGenerate} disabled={isStreaming}>
                        {isStreaming ? "Generating..." : "Generate"}
                      </Button>
                    </div>

                    {tree && (
                      <div className="mt-4 rounded-lg border p-4">
                        <h3 className="mb-2 font-medium">Generated UI:</h3>
                        <Renderer
                          registry={registry}
                          tree={tree}
                          loading={isStreaming}
                        />
                      </div>
                    )}
                  </CardContent>
                </Card>
              </section>

              {/* JSON Preview Section */}
              {tree && (
                <section>
                  <Card>
                    <CardHeader>
                      <CardTitle>JSON Preview</CardTitle>
                      <CardDescription>
                        The generated UI definition in JSON format
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <pre className="overflow-auto rounded-lg bg-muted p-4 text-sm">
                        {JSON.stringify(tree, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                </section>
              )}
            </div>
          </div>
        </ActionProvider>
      </VisibilityProvider>
    </DataProvider>
  );
}
