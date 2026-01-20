"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { Action } from "@json-render/core";
import type { ComponentRegistry } from "@json-render/react";
import {
  AlertCircle,
  BarChart3,
  CheckCircle,
  Clock,
  DollarSign,
  Info,
  Minus,
  TrendingDown,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";
import { useMemo, useState } from "react";

// Action handlers for use in ActionProvider
export const actionHandlers = {
  navigate: async (params: Record<string, unknown>) => {
    const url = params.url as string;
    window.location.href = url;
  },
  submit: async (params: Record<string, unknown>) => {
    const formId = params.formId as string | undefined;
    if (formId) {
      const form = document.getElementById(formId) as HTMLFormElement;
      form?.submit();
    }
  },
  alert: async (params: Record<string, unknown>) => {
    const message = params.message as string;
    alert(message);
  },
};

// Icon mapping for MetricCard
const iconMap = {
  chart: BarChart3,
  users: Users,
  clock: Clock,
  check: CheckCircle,
  alert: AlertCircle,
  dollar: DollarSign,
};

// Create the registry with React component implementations
export const registry: ComponentRegistry = {
  Container: ({ element, children }) => (
    <div
      className={cn("w-full", element.props.className as string | undefined)}
    >
      {children}
    </div>
  ),

  Card: ({ element, children }) => (
    <Card className={element.props.className as string | undefined}>
      {children}
    </Card>
  ),

  CardHeader: ({ element, children }) => (
    <CardHeader className={element.props.className as string | undefined}>
      {children}
    </CardHeader>
  ),

  CardTitle: ({ element }) => (
    <CardTitle className={element.props.className as string | undefined}>
      {element.props.text as string}
    </CardTitle>
  ),

  CardDescription: ({ element }) => (
    <CardDescription className={element.props.className as string | undefined}>
      {element.props.text as string}
    </CardDescription>
  ),

  CardContent: ({ element, children }) => (
    <CardContent className={element.props.className as string | undefined}>
      {children}
    </CardContent>
  ),

  CardFooter: ({ element, children }) => (
    <CardFooter className={element.props.className as string | undefined}>
      {children}
    </CardFooter>
  ),

  Button: ({ element, onAction }) => {
    const props = element.props as {
      text: string;
      action?: Action;
      variant?:
        | "default"
        | "destructive"
        | "outline"
        | "secondary"
        | "ghost"
        | "link";
      size?: "default" | "sm" | "lg" | "icon";
      disabled?: boolean;
      className?: string;
    };

    return (
      <Button
        variant={props.variant}
        size={props.size}
        disabled={props.disabled}
        className={props.className}
        onClick={() => {
          if (!onAction) return;
          if (props.action) {
            onAction(props.action);
            return;
          }
          onAction({
            name: "alert",
            params: { message: `${props.text} clicked!` },
          });
        }}
      >
        {props.text}
      </Button>
    );
  },

  Input: ({ element }) => {
    const props = element.props as {
      type?: "text" | "email" | "password" | "number" | "tel" | "url";
      placeholder?: string;
      disabled?: boolean;
      name?: string;
      className?: string;
    };

    return (
      <Input
        type={props.type}
        placeholder={props.placeholder}
        disabled={props.disabled}
        name={props.name}
        className={props.className}
      />
    );
  },

  Text: ({ element }) => {
    const props = element.props as {
      text: string;
      as?: "p" | "span" | "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
      className?: string;
    };
    const Component = props.as || "p";
    return <Component className={props.className}>{props.text}</Component>;
  },

  Flex: ({ element, children }) => {
    const props = element.props as {
      direction?: "row" | "col" | "row-reverse" | "col-reverse";
      justify?: "start" | "end" | "center" | "between" | "around" | "evenly";
      align?: "start" | "end" | "center" | "stretch" | "baseline";
      gap?: number;
      className?: string;
    };

    const directionClass = {
      row: "flex-row",
      col: "flex-col",
      "row-reverse": "flex-row-reverse",
      "col-reverse": "flex-col-reverse",
    }[props.direction || "row"];

    const justifyClass = {
      start: "justify-start",
      end: "justify-end",
      center: "justify-center",
      between: "justify-between",
      around: "justify-around",
      evenly: "justify-evenly",
    }[props.justify || "start"];

    const alignClass = {
      start: "items-start",
      end: "items-end",
      center: "items-center",
      stretch: "items-stretch",
      baseline: "items-baseline",
    }[props.align || "stretch"];

    const gapClass = props.gap ? `gap-${props.gap}` : "";

    return (
      <div
        className={cn(
          "flex",
          directionClass,
          justifyClass,
          alignClass,
          gapClass,
          props.className,
        )}
      >
        {children}
      </div>
    );
  },

  Grid: ({ element, children }) => {
    const props = element.props as {
      cols?: number;
      gap?: number;
      className?: string;
    };

    const colsClass = props.cols ? `grid-cols-${props.cols}` : "grid-cols-1";
    const gapClass = props.gap ? `gap-${props.gap}` : "";

    return (
      <div className={cn("grid", colsClass, gapClass, props.className)}>
        {children}
      </div>
    );
  },

  // Data visualization components
  MetricCard: ({ element }) => {
    const props = element.props as {
      label: string;
      value: string | number;
      change?: number;
      trend?: "up" | "down" | "neutral";
      icon?: "chart" | "users" | "clock" | "check" | "alert" | "dollar";
      className?: string;
    };

    const Icon = props.icon ? iconMap[props.icon] : null;
    const TrendIcon =
      props.trend === "up"
        ? TrendingUp
        : props.trend === "down"
          ? TrendingDown
          : Minus;

    const trendColor =
      props.trend === "up"
        ? "text-green-600"
        : props.trend === "down"
          ? "text-red-600"
          : "text-gray-500";

    return (
      <Card className={cn("p-6", props.className)}>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-muted-foreground">
              {props.label}
            </p>
            <p className="text-2xl font-bold">{props.value}</p>
            {props.change !== undefined && (
              <div className={cn("flex items-center text-sm", trendColor)}>
                <TrendIcon className="mr-1 h-4 w-4" />
                <span>{Math.abs(props.change)}%</span>
              </div>
            )}
          </div>
          {Icon && (
            <div className="rounded-full bg-muted p-3">
              <Icon className="h-6 w-6 text-muted-foreground" />
            </div>
          )}
        </div>
      </Card>
    );
  },

  DataTable: ({ element }) => {
    const props = element.props as {
      columns: Array<{
        key: string;
        label: string;
        align?: "left" | "center" | "right";
      }>;
      data: Array<Record<string, unknown>>;
      className?: string;
    };

    const alignClass = {
      left: "text-left",
      center: "text-center",
      right: "text-right",
    };

    return (
      <div className={cn("overflow-x-auto rounded-lg border", props.className)}>
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              {props.columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-4 py-3 font-medium",
                    alignClass[col.align || "left"],
                  )}
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {props.data.map((row, idx) => (
              <tr key={idx} className="border-t">
                {props.columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn("px-4 py-3", alignClass[col.align || "left"])}
                  >
                    {String(row[col.key] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  },

  Badge: ({ element }) => {
    const props = element.props as {
      text: string;
      variant?: "default" | "success" | "warning" | "error" | "info";
      className?: string;
    };

    const variantClass = {
      default: "bg-gray-100 text-gray-800",
      success: "bg-green-100 text-green-800",
      warning: "bg-yellow-100 text-yellow-800",
      error: "bg-red-100 text-red-800",
      info: "bg-blue-100 text-blue-800",
    }[props.variant || "default"];

    return (
      <span
        className={cn(
          "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
          variantClass,
          props.className,
        )}
      >
        {props.text}
      </span>
    );
  },

  ProgressBar: ({ element }) => {
    const props = element.props as {
      value: number;
      label?: string;
      showValue?: boolean;
      color?: "default" | "success" | "warning" | "error";
      className?: string;
    };

    const colorClass = {
      default: "bg-primary",
      success: "bg-green-500",
      warning: "bg-yellow-500",
      error: "bg-red-500",
    }[props.color || "default"];

    return (
      <div className={cn("space-y-1", props.className)}>
        {(props.label || props.showValue) && (
          <div className="flex justify-between text-sm">
            {props.label && (
              <span className="text-muted-foreground">{props.label}</span>
            )}
            {props.showValue && (
              <span className="font-medium">{props.value}%</span>
            )}
          </div>
        )}
        <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
          <div
            className={cn("h-full transition-all", colorClass)}
            style={{ width: `${Math.min(100, Math.max(0, props.value))}%` }}
          />
        </div>
      </div>
    );
  },

  StatGroup: ({ element, children }) => {
    const props = element.props as {
      className?: string;
    };

    return (
      <div
        className={cn(
          "grid gap-4 md:grid-cols-2 lg:grid-cols-4",
          props.className,
        )}
      >
        {children}
      </div>
    );
  },

  Divider: ({ element }) => {
    const props = element.props as {
      className?: string;
    };

    return <hr className={cn("my-4 border-t", props.className)} />;
  },

  Alert: ({ element }) => {
    const props = element.props as {
      title?: string;
      message: string;
      variant?: "info" | "success" | "warning" | "error";
      className?: string;
    };

    const variantStyles = {
      info: "bg-blue-50 border-blue-200 text-blue-800",
      success: "bg-green-50 border-green-200 text-green-800",
      warning: "bg-yellow-50 border-yellow-200 text-yellow-800",
      error: "bg-red-50 border-red-200 text-red-800",
    }[props.variant || "info"];

    const IconComponent = {
      info: Info,
      success: CheckCircle,
      warning: AlertCircle,
      error: AlertCircle,
    }[props.variant || "info"];

    return (
      <div
        className={cn(
          "flex items-start gap-3 rounded-lg border p-4",
          variantStyles,
          props.className,
        )}
      >
        <IconComponent className="mt-0.5 h-5 w-5 flex-shrink-0" />
        <div>
          {props.title && <p className="font-medium">{props.title}</p>}
          <p className={props.title ? "text-sm opacity-90" : ""}>
            {props.message}
          </p>
        </div>
      </div>
    );
  },

  Graph: ({ element, onAction }) => {
    const props = element.props as {
      title?: string;
      nodeAction?: Action;
      nodes: Array<{
        id: string;
        label: string;
        type?: string;
        summary?: string;
        ocr?: string;
        metadata?: Record<string, unknown>;
      }>;
      edges: Array<{ from: string; to: string; label?: string }>;
      className?: string;
    };

    const [selectedNode, setSelectedNode] = useState<{
      id: string;
      label?: string;
      type?: string;
      summary?: string;
      ocr?: string;
      metadata?: Record<string, unknown>;
    } | null>(null);

    const nodes = useMemo(
      () => (Array.isArray(props.nodes) ? props.nodes : []),
      [props.nodes],
    );
    const edges = useMemo(
      () => (Array.isArray(props.edges) ? props.edges : []),
      [props.edges],
    );
    const size = 520;
    const center = size / 2;
    const radius = 180;
    const positions = new Map<string, { x: number; y: number }>();

    nodes.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / Math.max(1, nodes.length);
      positions.set(node.id, {
        x: center + radius * Math.cos(angle),
        y: center + radius * Math.sin(angle),
      });
    });

    const flowNodes = nodes.map((node) => ({
      id: node.id,
      position: positions.get(node.id) ?? { x: center, y: center },
      data: {
        label: node.label,
        type: node.type,
        summary: node.summary,
        ocr: node.ocr,
        metadata: node.metadata,
      },
    }));

    const flowEdges = edges.map((edge, index) => ({
      id: `${edge.from}-${edge.to}-${index}`,
      source: edge.from,
      target: edge.to,
      label: edge.label,
      animated: true,
    }));

    return (
      <div className={cn("space-y-4", props.className)}>
        {props.title && (
          <div className="text-sm font-medium text-muted-foreground">
            {typeof props.title === "string"
              ? props.title
              : JSON.stringify(props.title)}
          </div>
        )}
        <div className="rounded-lg border bg-card p-4">
          <div className="h-[520px] w-full">
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              fitView
              zoomOnScroll={false}
              zoomOnPinch
              panOnScroll
              minZoom={0.2}
              maxZoom={2}
              onNodeClick={(_, node) => {
                setSelectedNode({
                  id: node.id,
                  label: node.data?.label,
                  type: node.data?.type,
                  summary: node.data?.summary,
                  ocr: node.data?.ocr,
                  metadata: node.data?.metadata,
                });
              }}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={18} size={1} />
              <MiniMap />
              <Controls />
            </ReactFlow>
          </div>
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          {nodes.map((node) => (
            <div
              key={`${node.id}-legend`}
              className="flex items-center justify-between rounded-md border bg-muted/30 px-3 py-2 text-xs"
            >
              <span className="font-medium">{node.label}</span>
              <span className="text-muted-foreground">
                {node.type || "node"}
              </span>
            </div>
          ))}
        </div>

        {selectedNode && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
            onClick={() => setSelectedNode(null)}
          >
            <div
              className="w-full max-w-xl rounded-xl border bg-card shadow-xl"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="flex items-start justify-between border-b px-5 py-4">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">
                    Node detail
                  </p>
                  <h3 className="text-lg font-semibold">
                    {selectedNode.label ?? selectedNode.id}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {selectedNode.type ?? "unknown"}
                  </p>
                </div>
                <button
                  className="rounded-md border p-1 text-muted-foreground hover:bg-muted/40"
                  onClick={() => setSelectedNode(null)}
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-4 px-5 py-4">
                <div className="rounded-md border bg-muted/30 p-3 text-sm">
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    Summary
                  </div>
                  <p className="mt-1 text-sm">
                    {selectedNode.summary || "No summary available."}
                  </p>
                </div>
                <div className="rounded-md border bg-muted/30 p-3 text-sm">
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    OCR
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    {selectedNode.ocr || "No OCR evidence captured."}
                  </p>
                </div>
                <div className="rounded-md border bg-muted/30 p-3 text-sm">
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    Metadata
                  </div>
                  <pre className="mt-2 max-h-40 overflow-auto text-xs text-muted-foreground">
                    {selectedNode.metadata
                      ? JSON.stringify(selectedNode.metadata, null, 2)
                      : "No metadata."}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  },
};
