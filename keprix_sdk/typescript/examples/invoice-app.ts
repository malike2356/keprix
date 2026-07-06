import { CarinaApp, Domain, Entity, Field, Operation } from "../src/index.js";

const domain: Domain = {
  name: "invoicing",
  entities: [
    {
      name: "Client",
      fields: [
        { name: "name", type: "string", required: true },
        { name: "email", type: "email", required: true },
      ],
      operations: [{ name: "create" }, { name: "delete", confirmation_required: true }],
    },
    {
      name: "Invoice",
      fields: [
        { name: "amount", type: "decimal", required: true },
        { name: "currency", type: "string", default: "GBP" },
      ],
      operations: [{ name: "create" }, { name: "send", confirmation_required: true }],
    },
  ],
};

const app = new CarinaApp({
  name: "invoice-example-ts",
  carinaUrl: process.env.KEPRIX_URL || "http://localhost:3333",
  apiToken: process.env.KEPRIX_API_TOKEN || "demo-token",
});

app.registerDomain(domain);

app.onAction(async (plan) => {
  console.log("Action plan:", JSON.stringify(plan, null, 2));
  return { success: true, steps: plan.steps };
});

if (process.env.KEPRIX_API_TOKEN) {
  await app.connect();
  const plan = await app.handle("create invoice for James £500");
  console.log(plan);
} else {
  console.log("Invoice TS example ready. Set KEPRIX_API_TOKEN to connect.");
}
