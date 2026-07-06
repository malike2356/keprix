import { Agent, RagApi, createLocalClient, createMemoryApi } from "../src/index.js";

async function main() {
  const client = createLocalClient();
  const rag = new RagApi(client);
  const memory = createMemoryApi(client);

  await rag.ingest("sdk-readme", "Keprix TypeScript SDK supports RAG-backed agents.");
  const hits = await rag.search("TypeScript SDK");
  console.log("rag hits:", hits.results?.length || 0);

  const agent = Agent.define(client, {
    name: "rag-agent",
    instructions: "Answer using retrieved context when available.",
    memory,
  });

  const answer = await agent.run({
    message: `Use context to explain: ${JSON.stringify(hits.results?.slice(0, 2) || [])}`,
  });
  console.log("agent:", answer.output.slice(0, 200));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
