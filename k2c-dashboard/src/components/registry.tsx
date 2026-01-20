"use client";

import type { ComponentRegistry } from "@json-render/react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

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

// Create the registry with React component implementations
export const registry: ComponentRegistry = {
  Container: ({ element, children }) => (
    <div className={cn("w-full", element.props.className as string | undefined)}>
      {children}
    </div>
  ),

  Card: ({ element, children }) => (
    <Card className={element.props.className as string | undefined}>{children}</Card>
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
      variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
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
          // Handle action if defined - for now just use alert for demo
          if (onAction) {
            onAction({
              name: "alert",
              params: { message: `${props.text} clicked!` },
            });
          }
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
          props.className
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
};
