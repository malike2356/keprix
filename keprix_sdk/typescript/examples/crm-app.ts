import { KeprixApp, Domain, Entity, Field, Operation } from "../src/index.js";

const domain: Domain = {
  name: "crm",
  entities: [
    {
      name: "Contact",
      fields: [{ name: "name", type: "string", required: true }],
      operations: [{ name: "create" }, { name: "delete", confirmation_required: true }],
    },
    {
      name: "Deal",
      fields: [{ name: "title", type: "string", required: true }],
      operations: [{ name: "create" }],
    },
  ],
};

const app = new KeprixApp({
  name: "crm-example-ts",
  keprixUrl: process.env.KEPRIX_URL || "http://localhost:3333",
  apiToken: process.env.KEPRIX_API_TOKEN || "demo-token",
});

app.registerDomain(domain);

if (process.env.KEPRIX_API_TOKEN) {
  await app.connect();
  console.log("CRM TS example registered.");
} else {
  console.log("CRM TS example ready. Set KEPRIX_API_TOKEN to connect.");
}
