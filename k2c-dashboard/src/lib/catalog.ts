import { z } from "zod";
import { createCatalog } from "@json-render/core";

// Define component catalog
export const catalog = createCatalog({
  name: "k2c-dashboard",
  components: {
    // Container component
    Container: {
      props: z.object({
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "A container component for wrapping other elements",
    },

    // Card components
    Card: {
      props: z.object({
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "A card container with border and shadow",
    },

    CardHeader: {
      props: z.object({
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "Header section of a card",
    },

    CardTitle: {
      props: z.object({
        text: z.string().describe("The title text"),
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: false,
      description: "Title text for a card",
    },

    CardDescription: {
      props: z.object({
        text: z.string().describe("The description text"),
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: false,
      description: "Description text for a card",
    },

    CardContent: {
      props: z.object({
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "Content section of a card",
    },

    CardFooter: {
      props: z.object({
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "Footer section of a card",
    },

    // Button component
    Button: {
      props: z.object({
        text: z.string().describe("The button label text"),
        variant: z
          .enum(["default", "destructive", "outline", "secondary", "ghost", "link"])
          .optional()
          .describe("The button style variant"),
        size: z
          .enum(["default", "sm", "lg", "icon"])
          .optional()
          .describe("The button size"),
        disabled: z.boolean().optional().describe("Whether the button is disabled"),
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: false,
      description: "A clickable button with various styles",
    },

    // Input component
    Input: {
      props: z.object({
        placeholder: z.string().optional().describe("Placeholder text"),
        type: z
          .enum(["text", "email", "password", "number", "tel", "url"])
          .optional()
          .describe("Input type"),
        disabled: z.boolean().optional().describe("Whether the input is disabled"),
        name: z.string().optional().describe("Input name for form submission"),
        bindTo: z.string().optional().describe("Data path to bind the input value to"),
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: false,
      description: "A text input field",
    },

    // Text component for simple text content
    Text: {
      props: z.object({
        text: z.string().describe("The text content"),
        className: z.string().optional().describe("Additional CSS classes"),
        as: z
          .enum(["p", "span", "h1", "h2", "h3", "h4", "h5", "h6"])
          .optional()
          .describe("HTML element to render as"),
      }),
      hasChildren: false,
      description: "A text element that can render as different HTML tags",
    },

    // Flex container for layout
    Flex: {
      props: z.object({
        direction: z
          .enum(["row", "col", "row-reverse", "col-reverse"])
          .optional()
          .describe("Flex direction"),
        justify: z
          .enum(["start", "end", "center", "between", "around", "evenly"])
          .optional()
          .describe("Justify content"),
        align: z
          .enum(["start", "end", "center", "stretch", "baseline"])
          .optional()
          .describe("Align items"),
        gap: z.number().optional().describe("Gap between items"),
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "A flexbox container for laying out children",
    },

    // Grid container for layout
    Grid: {
      props: z.object({
        cols: z.number().optional().describe("Number of grid columns"),
        gap: z.number().optional().describe("Gap between items"),
        className: z.string().optional().describe("Additional CSS classes"),
      }),
      hasChildren: true,
      description: "A grid container for laying out children in columns",
    },
  },
  actions: {
    navigate: {
      params: z.object({
        url: z.string().describe("The URL to navigate to"),
      }),
      description: "Navigate to a URL",
    },
    submit: {
      params: z.object({
        formId: z.string().optional().describe("The form ID to submit"),
      }),
      description: "Submit a form",
    },
    alert: {
      params: z.object({
        message: z.string().describe("The alert message to display"),
      }),
      description: "Show an alert message",
    },
  },
});

export type AppCatalog = typeof catalog;
