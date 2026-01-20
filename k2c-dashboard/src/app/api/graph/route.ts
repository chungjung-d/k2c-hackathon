export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type GraphNode = { id: string; label: string; type?: string };
type GraphEdge = { from: string; to: string; label?: string };

const demoGraph = {
  nodes: [
    { id: "n1", label: "iTerm2", type: "app" },
    { id: "n2", label: "Terminal", type: "concept" },
    { id: "n3", label: "Shell", type: "concept" },
    { id: "n4", label: "Scripts", type: "artifact" },
    { id: "n5", label: "macOS", type: "platform" },
    { id: "n6", label: "Screenshot", type: "evidence" },
    { id: "n7", label: "OCR Text", type: "signal" },
    { id: "n8", label: "User Activity", type: "signal" },
    { id: "n9", label: "Menu Bar", type: "ui" },
  ],
  edges: [
    { from: "n1", to: "n2", label: "implements" },
    { from: "n1", to: "n3", label: "uses" },
    { from: "n1", to: "n4", label: "runs" },
    { from: "n1", to: "n5", label: "on" },
    { from: "n6", to: "n1", label: "captures" },
    { from: "n7", to: "n1", label: "mentions" },
    { from: "n8", to: "n1", label: "observes" },
    { from: "n9", to: "n5", label: "part of" },
  ],
};

function extractTopic(prompt: string): string | null {
  const quoted = prompt.match(/\"([^\"]+)\"|\'([^\']+)\'/);
  if (quoted) return quoted[1] || quoted[2] || null;
  const match = prompt.match(/특정\s*지식\s*(?:에\s*대한)?\s*(.+)/);
  if (match) return match[1].trim();
  return null;
}

function filterGraphByTopic(topic: string | null) {
  if (!topic) return demoGraph;
  const lower = topic.toLowerCase();
  const nodes = demoGraph.nodes.filter((node) =>
    node.label.toLowerCase().includes(lower)
  );
  if (nodes.length === 0) return demoGraph;
  const nodeIds = new Set(nodes.map((node) => node.id));
  const edges = demoGraph.edges.filter(
    (edge) => nodeIds.has(edge.from) || nodeIds.has(edge.to)
  );
  const relatedIds = new Set<string>();
  edges.forEach((edge) => {
    relatedIds.add(edge.from);
    relatedIds.add(edge.to);
  });
  return {
    nodes: demoGraph.nodes.filter((node) => relatedIds.has(node.id)),
    edges,
  };
}

function buildGraphTree(title: string, nodes: GraphNode[], edges: GraphEdge[]) {
  const rootKey = "graph-root";
  const cardKey = "graph-card";
  const headerKey = "graph-header";
  const titleKey = "graph-title";
  const contentKey = "graph-content";
  const graphKey = "graph-component";

  return {
    root: rootKey,
    elements: {
      [rootKey]: {
        key: rootKey,
        type: "Container",
        props: { className: "space-y-6" },
        children: [cardKey],
      },
      [cardKey]: {
        key: cardKey,
        type: "Card",
        props: {},
        children: [headerKey, contentKey],
        parentKey: rootKey,
      },
      [headerKey]: {
        key: headerKey,
        type: "CardHeader",
        props: {},
        children: [titleKey],
        parentKey: cardKey,
      },
      [titleKey]: {
        key: titleKey,
        type: "CardTitle",
        props: { text: title },
        parentKey: headerKey,
      },
      [contentKey]: {
        key: contentKey,
        type: "CardContent",
        props: {},
        children: [graphKey],
        parentKey: cardKey,
      },
      [graphKey]: {
        key: graphKey,
        type: "Graph",
        props: {
          title: "Related knowledge nodes",
          nodeAction: {
            name: "alert",
            params: {
              message: "Clicked ${label} (${type})",
            },
          },
          nodes,
          edges,
        },
        parentKey: contentKey,
      },
    },
  };
}

export async function POST(req: Request) {
  const { prompt } = await req.json();
  const topic = extractTopic(typeof prompt === "string" ? prompt : "");
  const data = filterGraphByTopic(topic);
  const title = topic
    ? `Knowledge graph for: ${topic}`
    : "Knowledge graph from recent screenshots";

  const tree = buildGraphTree(title, data.nodes, data.edges);

  return new Response(JSON.stringify(tree), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
}
