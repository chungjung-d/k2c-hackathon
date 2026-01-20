import { streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import { generateCatalogPrompt } from "@json-render/core";
import { catalog } from "@/lib/catalog";
import { query } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type EvaluationRow = {
  id: string;
  feature_id: string;
  evaluation: unknown;
  goal: string;
  evaluated_at: string;
  model: string | null;
  user_id: string | null;
  captured_at: string | null;
};

type SummaryRow = {
  total: string;
  avg_score: string | null;
  success_rate: string | null;
};

type LabelRow = {
  label: string;
  count: string;
};

type ModelRow = {
  model: string | null;
  total: string;
  avg_score: string | null;
  success_rate: string | null;
};

function parseEvaluation(value: unknown): Record<string, unknown> {
  if (!value) return {};
  if (typeof value === "string") {
    try {
      return JSON.parse(value) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  if (typeof value === "object") return value as Record<string, unknown>;
  return {};
}

async function fetchEvaluationData() {
  const [{ rows: summaryRows }, { rows: recentRows }, { rows: labelRows }, { rows: modelRows }] =
    await Promise.all([
      query<SummaryRow>(
        `
        SELECT
          COUNT(*)::text AS total,
          AVG((evaluation->>'score')::numeric)::text AS avg_score,
          AVG(CASE WHEN (evaluation->>'score')::int >= 70 THEN 1 ELSE 0 END)::text AS success_rate
        FROM evaluations
        `
      ),
      query<EvaluationRow>(
        `
        SELECT
          e.id,
          e.feature_id,
          e.evaluation,
          e.goal,
          e.evaluated_at::text AS evaluated_at,
          e.model,
          d.user_id,
          d.captured_at::text AS captured_at
        FROM evaluations e
        LEFT JOIN features f ON f.id = e.feature_id
        LEFT JOIN data_events d ON d.id = f.event_id
        ORDER BY e.evaluated_at DESC
        LIMIT 50
        `
      ),
      query<LabelRow>(
        `
        SELECT label::text AS label, COUNT(*)::text AS count
        FROM evaluations
        CROSS JOIN LATERAL jsonb_array_elements_text(evaluation->'labels') label
        GROUP BY label
        ORDER BY COUNT(*) DESC
        LIMIT 8
        `
      ),
      query<ModelRow>(
        `
        SELECT
          model,
          COUNT(*)::text AS total,
          AVG((evaluation->>'score')::numeric)::text AS avg_score,
          AVG(CASE WHEN (evaluation->>'score')::int >= 70 THEN 1 ELSE 0 END)::text AS success_rate
        FROM evaluations
        GROUP BY model
        ORDER BY COUNT(*) DESC
        `
      ),
    ]);

  const summary = summaryRows[0] ?? {
    total: "0",
    avg_score: null,
    success_rate: null,
  };

  const recentEvaluations = recentRows.map((row) => {
    const evaluation = parseEvaluation(row.evaluation);
    const score =
      typeof evaluation.score === "number"
        ? evaluation.score
        : evaluation.score !== undefined
          ? Number(evaluation.score)
          : null;
    const status =
      score === null
        ? "unknown"
        : score >= 80
          ? "success"
          : score >= 50
            ? "warning"
            : "error";
    return {
      id: row.id,
      featureId: row.feature_id,
      userId: row.user_id,
      goal: row.goal,
      score,
      status,
      labels: evaluation.labels ?? [],
      summary: evaluation.summary ?? null,
      source: evaluation.source ?? null,
      evaluatedAt: row.evaluated_at,
      capturedAt: row.captured_at,
      model: row.model,
    };
  });

  const labelBreakdown = labelRows.map((row) => ({
    label: row.label,
    count: Number(row.count),
  }));

  const modelPerformance = modelRows.map((row) => ({
    model: row.model ?? "unknown",
    total: Number(row.total),
    avgScore: row.avg_score ? Number(row.avg_score) : null,
    successRate: row.success_rate ? Number(row.success_rate) * 100 : null,
  }));

  return {
    summary: {
      totalEvaluations: Number(summary.total),
      avgScore: summary.avg_score ? Number(summary.avg_score) : null,
      successRate: summary.success_rate ? Number(summary.success_rate) * 100 : null,
      recentCount: recentEvaluations.length,
    },
    labelBreakdown,
    modelPerformance,
    recentEvaluations,
  };
}

const STREAMING_INSTRUCTIONS = `
## Output Format

You MUST output JSON Lines (JSONL) format where each line is a JSON patch operation.
Each line must be a complete JSON object on its own line.

### Patch Operations:
- {"op":"set","path":"/root","value":"element-key"} - Set the root element key
- {"op":"set","path":"/elements/key","value":{...}} - Add/update an element

### Element Structure:
{
  "key": "unique-key",
  "type": "ComponentType",
  "props": { ... },
  "children": ["child-key-1", "child-key-2"],
  "parentKey": "parent-key"
}

### Available Components for Dashboard:
- Container: wrapper with className
- Card, CardHeader, CardTitle, CardDescription, CardContent: card components
- Flex: flexbox container (direction: row|col, gap, justify, align)
- Grid: grid container (cols, gap)
- Text: text content (text, as: p|span|h1|h2|h3)
- Button: clickable action (text, action)
- MetricCard: metric display (label, value, change, trend: up|down|neutral, icon: chart|users|clock|check|alert|dollar)
- DataTable: data table (columns: [{key, label, align}], data: [{...}])
- Badge: status badge (text, variant: default|success|warning|error|info)
- ProgressBar: progress indicator (value, label, showValue, color: default|success|warning|error)
- StatGroup: container for MetricCards
- Alert: alert message (title, message, variant: info|success|warning|error)
- Divider: horizontal divider

### Example Output:
{"op":"set","path":"/root","value":"dashboard-1"}
{"op":"set","path":"/elements/dashboard-1","value":{"key":"dashboard-1","type":"Container","props":{"className":"space-y-6"},"children":["stats-1","table-1"]}}
{"op":"set","path":"/elements/stats-1","value":{"key":"stats-1","type":"StatGroup","props":{},"children":["metric-1","metric-2"],"parentKey":"dashboard-1"}}
{"op":"set","path":"/elements/metric-1","value":{"key":"metric-1","type":"MetricCard","props":{"label":"Success Rate","value":"94.5%","change":2.3,"trend":"up","icon":"chart"},"parentKey":"stats-1"}}

### Rules:
1. Output ONLY valid JSONL - one JSON object per line, no markdown, no explanation
2. First line should always set the root element key
3. Then output each element with the set operation
4. Every element needs a unique "key" property
5. Use "children" array to reference child element keys
6. Include "parentKey" for non-root elements
7. Create a visually appealing dashboard layout using the data provided
8. Use appropriate components based on the data type (MetricCard for stats, DataTable for lists, etc.)
9. When adding a Button, include an "action" prop using one of the catalog actions
`;

export async function POST(req: Request) {
  const { prompt, query } = await req.json();
  const catalogPrompt = generateCatalogPrompt(catalog);

  const evaluationData = await fetchEvaluationData();

  const systemPrompt = `You are a dashboard UI generator for an admin monitoring system.
Your job is to create beautiful, informative dashboards based on evaluation data.

${catalogPrompt}

## Available Evaluation Data (from Evaluation Store):
${JSON.stringify(evaluationData, null, 2)}

${STREAMING_INSTRUCTIONS}`;

  const result = streamText({
    model: openai("gpt-5.2"),
    system: systemPrompt,
    prompt:
      prompt ||
      query ||
      "Create a comprehensive evaluation dashboard showing all metrics, recent evaluations, and performance breakdowns",
  });

  return new Response(result.textStream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
      "Cache-Control": "no-cache",
    },
  });
}
