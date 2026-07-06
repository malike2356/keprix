import { createLocalClient, createWorkflow } from "../src/index.js";
import { WorkflowRunner } from "../src/workflow.js";

async function main() {
  const client = createLocalClient();
  const runner = new WorkflowRunner(client);

  const workflow = createWorkflow("ts-example")
    .task("prepare", { key: "topic", value: "sdk-workflow" })
    .branch("route", "topic", "sdk-workflow")
    .branchTo("route", "approve", "true")
    .approval("approve", "Publish workflow artifact?", "low")
    .artifact("report", "workflow-report", "prepare_output", "Workflow complete")
    .edge("approve", "report")
    .build();

  const run = await runner.start(workflow);
  console.log("status:", run.status);

  if (run.status === "waiting_for_approval") {
    const resumed = await runner.resume(run.run_id, { approve_approved: true }, "developer");
    console.log("resumed:", resumed.status, resumed.artifacts);
    return;
  }

  console.log("artifacts:", run.artifacts);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
