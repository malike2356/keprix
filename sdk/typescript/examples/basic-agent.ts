import {
  Agent,
  KeprixClient,
  createLocalClient,
  createMemoryApi,
  defineTool,
} from "../src/index.js";

async function main() {
  const client = createLocalClient();
  const memory = createMemoryApi(client);
  const agent = Agent.define(client, {
    name: "basic-agent",
    instructions: "You are a concise Keprix assistant.",
    model: "keprix",
    memory,
    tools: [
      defineTool("echo", "Echo text back", {
        type: "object",
        properties: { text: { type: "string" } },
        required: ["text"],
      }),
    ],
  });

  const result = await agent.run({ message: "Say hello in one short sentence." });
  console.log("output:", result.output);
  console.log("trace:", result.trace.traceId);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
