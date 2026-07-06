export const INTEGRATION_GROUPS = [
  {
    label: "LLM Providers",
    items: ["Anthropic", "OpenAI", "Gemini", "Groq", "Ollama", "OpenRouter", "DeepSeek"],
  },
  {
    label: "Channels",
    items: ["Telegram", "Discord", "Slack", "WhatsApp", "Email (IMAP)", "Webhook", "REST API"],
  },
  {
    label: "Infrastructure",
    items: ["Docker", "PostgreSQL", "SQLite", "Redis", "pgvector", "MCP", "SFTP"],
  },
] as const;

export const INTEGRATION_PROVIDERS = [
  { name: "Anthropic", color: "#cc785c" },
  { name: "OpenAI", color: "#10a37f" },
  { name: "Gemini", color: "#4285f4" },
  { name: "Groq", color: "#f55036" },
  { name: "Mistral", color: "#ff7000" },
  { name: "Ollama", color: "#9b9b9b" },
  { name: "Telegram", color: "#2aabee" },
  { name: "Discord", color: "#5865f2" },
  { name: "Deepseek", color: "#3b82f6" },
  { name: "OpenRouter", color: "#7c3aed" },
] as const;
