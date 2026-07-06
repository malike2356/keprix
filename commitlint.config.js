/** @type {import('@commitlint/types').UserConfig} */
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "docs", "style", "refactor", "perf", "test", "build", "ci", "chore", "revert"],
    ],
    "scope-enum": [
      1,
      "always",
      [
        "agent",
        "mutation",
        "billing",
        "auth",
        "frontend",
        "api",
        "cli",
        "docker",
        "docs",
        "research",
        "memory",
        "vault",
        "mcp",
        "playbook",
        "evals",
        "deps",
      ],
    ],
    "subject-case": [2, "never", ["start-case", "pascal-case", "upper-case"]],
    "header-max-length": [2, "always", 100],
  },
};
