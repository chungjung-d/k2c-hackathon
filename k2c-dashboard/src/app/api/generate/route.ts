import { streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import { generateCatalogPrompt } from "@json-render/core";
import { catalog } from "@/lib/catalog";

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

### Example Output (each line is a separate JSON object):
{"op":"set","path":"/root","value":"container-1"}
{"op":"set","path":"/elements/container-1","value":{"key":"container-1","type":"Container","props":{"className":"p-4"},"children":["card-1"]}}
{"op":"set","path":"/elements/card-1","value":{"key":"card-1","type":"Card","props":{},"children":["title-1"],"parentKey":"container-1"}}
{"op":"set","path":"/elements/title-1","value":{"key":"title-1","type":"CardTitle","props":{"text":"Hello World"},"parentKey":"card-1"}}

### Rules:
1. Output ONLY valid JSONL - one JSON object per line, no markdown, no explanation
2. First line should always set the root element key
3. Then output each element with the set operation
4. Every element needs a unique "key" property
5. Use "children" array to reference child element keys
6. Include "parentKey" for non-root elements
`;

export async function POST(req: Request) {
  const { prompt } = await req.json();
  const catalogPrompt = generateCatalogPrompt(catalog);

  const systemPrompt = `You are a UI generator that creates user interfaces based on descriptions.

${catalogPrompt}

${STREAMING_INSTRUCTIONS}`;

  const result = streamText({
    model: openai("gpt-5.2"),
    system: systemPrompt,
    prompt: `Generate a UI for: ${prompt}`,
  });

  return new Response(result.textStream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Transfer-Encoding": "chunked",
      "Cache-Control": "no-cache",
    },
  });
}
