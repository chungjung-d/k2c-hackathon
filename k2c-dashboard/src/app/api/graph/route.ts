import neo4j, {
  int,
  isInt,
  type Driver,
  type Integer,
  type Node,
  type Session,
} from "neo4j-driver";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type GraphNode = {
  id: string;
  label: string;
  type?: string;
  summary?: string;
  ocr?: string;
  capturedAt?: string;
  userActivity?: string;
  riskLevel?: string;
  metadata?: Record<string, unknown>;
};
type GraphEdge = { from: string; to: string; label?: string };

function extractTopic(prompt: string): string | null {
  const quoted = prompt.match(/\"([^\"]+)\"|\'([^\']+)\'/);
  if (quoted) return quoted[1] || quoted[2] || null;
  const match = prompt.match(/특정\s*지식\s*(?:에\s*대한)?\s*(.+)/);
  if (match) return match[1].trim();
  return null;
}

function filterGraphByTopic(topic: string | null) {
  if (!topic) return { nodes: [], edges: [] };
  return { nodes: [], edges: [] };
}

function normalizeValue(value: unknown): unknown {
  if (isInt(value)) return (value as Integer).toNumber();
  if (Array.isArray(value)) return value.map(normalizeValue);
  if (value && typeof value === "object") {
    const output: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value)) {
      output[key] = normalizeValue(entry);
    }
    return output;
  }
  return value;
}

function recordToProps(
  record: Record<string, unknown>,
): Record<string, unknown> {
  const props = record || {};
  return normalizeValue(props) as Record<string, unknown>;
}

function buildGraphTree(
  title: string,
  nodes: GraphNode[],
  edges: GraphEdge[],
  focusNodeId?: string,
) {
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
          focusNodeId,
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
  const body = await req.json();
  const prompt = body?.prompt;
  const topic = extractTopic(typeof prompt === "string" ? prompt : "");
  const queryText = (topic || "").toLowerCase();
  const limit = Math.max(1, Math.min(10, Math.floor(Number(body?.limit) || 10)));

  const neo4jUri = process.env.NEO4J_URI;
  const neo4jUser = process.env.NEO4J_USER;
  const neo4jPassword = process.env.NEO4J_PASSWORD;
  const neo4jDatabase = process.env.NEO4J_DATABASE || "neo4j";

  let data = { nodes: [] as GraphNode[], edges: [] as GraphEdge[] };

  if (!neo4jUri || !neo4jUser || !neo4jPassword) {
    return new Response(
      JSON.stringify({
        error: "Neo4j configuration is missing. Set NEO4J_URI/USER/PASSWORD.",
      }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  }

  let driver: Driver | null = null;
  let session: Session | null = null;
  try {
    driver = neo4j.driver(
      neo4jUri,
      neo4j.auth.basic(neo4jUser, neo4jPassword),
      {
        encrypted: "ENCRYPTION_OFF",
      },
    );
    session = driver.session({ database: neo4jDatabase });

    const result = await session.run(
      `
      MATCH (e:ScreenshotEvent)
      OPTIONAL MATCH (e)-[:HAS_TAG]->(t:Tag)
      WITH e, collect(t) AS tags
      WITH e, tags,
        (CASE WHEN $q <> '' AND toLower(coalesce(e.summary, '')) CONTAINS $q THEN 2 ELSE 0 END +
         CASE WHEN $q <> '' AND toLower(coalesce(e.content_summary, '')) CONTAINS $q THEN 2 ELSE 0 END +
         CASE WHEN $q <> '' AND toLower(coalesce(e.ocr_text, '')) CONTAINS $q THEN 1 ELSE 0 END +
         size([tag IN tags WHERE $q <> '' AND toLower(tag.name) CONTAINS $q])) AS score
      WHERE $q = '' OR score > 0
      WITH e, tags, score
      ORDER BY score DESC, e.captured_at DESC
      LIMIT $limit
      OPTIONAL MATCH (u:User)-[:CAPTURED]->(e)
      RETURN e, u, tags
      `,
      { q: queryText, limit: int(limit) },
    );

    const nodeMap = new Map<string, GraphNode>();
    const edges: GraphEdge[] = [];

    for (const record of result.records) {
      const eventNode = record.get("e");
      const userNode = record.get("u");
      const tagNodes = record.get("tags") as Array<unknown>;

      if (eventNode) {
        const eventProps = recordToProps(
            (eventNode as Node).properties as Record<string, unknown>,
        );
        const eventId =
          eventProps.event_id ??
          eventProps.id ??
          (eventNode as Node).identity.toString();
        const eventKey = `event:${eventId}`;
        nodeMap.set(eventKey, {
          id: eventKey,
          label: String(
            eventProps.summary || eventProps.content_summary || eventId,
          ),
          type: "ScreenshotEvent",
          summary:
            (eventProps.content_summary as string) ||
            (eventProps.summary as string),
          ocr: eventProps.ocr_text as string | undefined,
          capturedAt: eventProps.captured_at as string | undefined,
          userActivity: eventProps.user_activity as string | undefined,
          riskLevel: eventProps.risk_level as string | undefined,
          metadata:
            (eventProps.metadata as Record<string, unknown>) || undefined,
        });
      }

      if (userNode) {
        const userProps = recordToProps(
            (userNode as Node).properties as Record<string, unknown>,
        );
        const userId =
          userProps.id ?? (userNode as Node).identity.toString();
        const userKey = `user:${userId}`;
        nodeMap.set(userKey, {
          id: userKey,
          label: String(userId),
          type: "User",
        });
      }

      if (eventNode && userNode) {
        const eventProps = recordToProps(
            (eventNode as Node).properties as Record<string, unknown>,
        );
        const eventId =
          eventProps.event_id ??
          eventProps.id ??
          (eventNode as Node).identity.toString();
        const eventKey = `event:${eventId}`;
        const userProps = recordToProps(
            (userNode as Node).properties as Record<string, unknown>,
        );
        const userId =
          userProps.id ?? (userNode as Node).identity.toString();
        const userKey = `user:${userId}`;
        edges.push({ from: userKey, to: eventKey, label: "CAPTURED" });
      }

      if (eventNode && Array.isArray(tagNodes)) {
        const eventProps = recordToProps(
            (eventNode as Node).properties as Record<string, unknown>,
        );
        const eventId =
          eventProps.event_id ??
          eventProps.id ??
          (eventNode as Node).identity.toString();
        const eventKey = `event:${eventId}`;
        for (const tagNode of tagNodes) {
          if (!tagNode) continue;
          const tagProps = recordToProps(
            (tagNode as Node).properties as Record<string, unknown>,
          );
          const tagName =
            tagProps.name ?? (tagNode as Node).identity.toString();
          const tagKey = `tag:${tagName}`;
          nodeMap.set(tagKey, {
            id: tagKey,
            label: String(tagName),
            type: "Tag",
          });
          edges.push({ from: eventKey, to: tagKey, label: "HAS_TAG" });
        }
      }
    }

    const maxNodes = 10;
    const nodesList = Array.from(nodeMap.values());
    const trimmedNodes = nodesList.slice(0, maxNodes);
    const allowedIds = new Set(trimmedNodes.map((node) => node.id));
    const trimmedEdges = edges.filter(
      (edge) => allowedIds.has(edge.from) && allowedIds.has(edge.to)
    );

    data = {
      nodes: trimmedNodes,
      edges: trimmedEdges,
    };
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Unknown Neo4j error";
    return new Response(
      JSON.stringify({
        error: "Neo4j query failed.",
        details: message,
      }),
      { status: 500, headers: { "Content-Type": "application/json" } },
    );
  } finally {
    if (session) await session.close();
    if (driver) await driver.close();
  }

  const focusNodeId = topic
    ? data.nodes.find((node) =>
        node.label.toLowerCase().includes(topic.toLowerCase()),
      )?.id
    : undefined;
  const title = topic
    ? `Knowledge graph for: ${topic}`
    : "Knowledge graph from recent screenshots";

  const tree = buildGraphTree(title, data.nodes, data.edges, focusNodeId);

  return new Response(JSON.stringify(tree), {
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
  });
}
