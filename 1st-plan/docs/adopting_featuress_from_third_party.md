I inspected:

  /opt/lampp/htdocs/verlox/carina/aiva/01-devends/planning/competitor-research/03-agents-researched_gap/3-agents-to-
  adopt

  Excluding Hermes, OpenClaw, and Odysseus, the useful agents are:

  - AutoGen
  - CrewAI
  - LangGraph
  - LaVague
  - SWE-agent
  - TaskWeaver

  My recommendation: do not “merge everything”. Adopt the patterns that strengthen Keprix’s platform thesis: governed
  agent operating system, playbooks, tool execution, deep research, workflow memory, browser action, analytics, and
  developer automation.

  Highest Value Adoption

   Source          Adopt                             What It Does                      How It Improves Keprix
  ━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   LangGraph       Durable state graphs              Long-running agent workflows      Makes Keprix reliable for
                                                     resume after failure              multi-hour research, launch,
                                                                                       coding, and business workflows
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   LangGraph       Human-in-the-loop interrupts      Pause workflow, inspect state,    Fits Keprix governance and
                                                     approve next step                 Scout bridge perfectly
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   CrewAI          Crews and Flows model             Role-based autonomous agents      Gives Keprix a clean way to
                                                     plus deterministic workflow       combine specialist agents with
                                                     control                           controlled execution
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   TaskWeaver      Code-first analytics execution    Plans, writes, verifies, and      Makes Keprix strong for data,
                                                     runs Python analysis code         SPSS/PSPP/Jamovi-style
                                                                                       workflows, finance, research,
                                                                                       ML
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   LaVague         Web action engine                 Turns web objectives into         Gives Keprix real browser
                                                     browser actions via Selenium,     automation for funnels,
                                                     Playwright, Chrome extension      testing, scraping, dashboards,
                                                                                       CRM work
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   SWE-agent       Agent-computer interface          File editing, shell workflows,    Improves Keprix’s self-coding,
                                                     repo issue solving, patch         repo repair, PR generation,
                                                     loops                             and developer automation
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   CrewAI tools    Large external tool library       Search, scraping, RAG,            Expands Keprix tools quickly
                                                     databases, OCR, YouTube,          without inventing every
                                                     GitHub, Zapier, sandboxes         connector
  ──────────────  ────────────────────────────────  ────────────────────────────────  ────────────────────────────────
   AutoGen         Multi-agent message runtime       Agent-to-agent messaging,         Useful for Keprix’s specialist
                                                     group chat, distributed           agent teams and cross-runtime
                                                     runtimes                          future

  AutoGen
  AutoGen is in maintenance mode, but the architecture is still worth learning from.

  Adopt these:

   Feature                        What It Does                               Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   AgentChat-style abstraction    Simple assistant agents, specialist        Clean user-facing multi-agent mode
                                  agents, group chats
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   AgentTool pattern              One agent can be exposed as a tool to      Lets Keprix build expert subagents like
                                  another agent                              researcher, coder, analyst, designer
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Multi-agent orchestration      Agents collaborate through structured      Better Opportunity Engine and deep
                                  messages                                   research workflows
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   MCP workbench pattern          Connects agents to MCP servers safely      Strengthens Keprix’s MCP host and tool
                                                                             discovery
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Streaming console pattern      Streams agent runs to terminal/UI          Better CLI, TUI, and web run visibility
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Studio concept                 No-code GUI for composing multi-agent      Keprix could have a visual Playbook
                                  workflows                                  Builder later
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Benchmark suite idea           Evaluates agent performance across         Keprix should add eval packs for
                                  tasks                                      research, coding, browser, security,
                                                                             business workflows
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Cross-runtime idea             Python and .NET style runtimes             Long-term useful for external SDKs and
                                                                             enterprise embedding

  Do not copy AutoGen as a dependency. Adopt the patterns.

  CrewAI
  CrewAI is the richest source for production-style agent workflow design.

  Adopt these:

   Feature                         What It Does                               Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Crews                           Groups of role-based agents with goals     Better multi-agent teams inside Keprix
                                   and backstories
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Flows                           Event-driven deterministic workflows       Lets Keprix keep autonomy under control
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Agent roles                     Role, goal, backstory, tools, LLM,         Cleaner agent configuration UI
                                   memory, guardrails
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Task objects                    Task description, dependencies,            Better playbook step definitions
                                   structured output, review
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   YAML project scaffolding        Defines agents and tasks declaratively     Keprix could import/export playbooks as
                                                                              YAML
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Human review in task design     Adds explicit review gates                 Matches security-first approval
                                                                              architecture
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Knowledge and memory modules    Crew-level knowledge and retrieval         Improves workspace-specific agent
                                                                              context
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Events and hooks                Lifecycle events around runs and tools     Useful for audit logs, Scout events,
                                                                              observability
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Tracing integrations            OpenTelemetry, Langfuse-like               Improves Keprix debug and enterprise
                                   integrations, Datadog-style                readiness
                                   observability
  ──────────────────────────────  ─────────────────────────────────────────  ─────────────────────────────────────────
   Pipeline tests                  Tests full multi-agent workflows           Better regression coverage for
                                                                              Opportunity Engine

  CrewAI tools worth adopting as Keprix tool ideas:

   Tool Area                     Tools Found                                 Keprix Use
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Search                        Brave, SerpAPI, Serper, Serply, Tavily,     Better deep research and opportunity
                                 Exa, Linkup                                 discovery
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Web scraping                  Firecrawl, Jina, ScrapeGraph, Scrapfly,     Better market research, competitor
                                 Spider, Selenium, Stagehand,                analysis, lead research
                                 Hyperbrowser, BrightData, Oxylabs
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Browser automation            Browserbase, Multion, Stagehand             Managed browser actions for sites that
                                                                             need interaction
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   RAG and documents             PDF, DOCX, TXT, CSV, JSON, XML, MDX,        Stronger document intelligence
                                 website search
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Databases                     MySQL, Snowflake, Databricks, Couchbase,    Keprix becomes useful for enterprise
                                 SingleStore                                 data work
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Vector stores                 Qdrant, Weaviate, MongoDB vector search     More deployment options for RAG
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Code and docs search          GitHub search, code docs search,            Better developer workflows
                                 directory search
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Media                         OCR, vision, DALL-E, YouTube channel and    Better multimodal research and content
                                 video search                                creation
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Sandboxes                     E2B, Daytona                                Safer code execution and agent
                                                                             experiments
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Automation                    Zapier action tool, CrewAI automation       Keprix can trigger external business
                                 generation and invocation                   workflows
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Evaluation                    Patronus eval tool                          Quality gates for generated outputs
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Compression and file tools    File read/write, directory read,            Better workspace file operations
                                 compressor

  LangGraph
  LangGraph is the best source for reliable workflow architecture.

  Adopt these:

   Feature                        What It Does                               Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   State graph runtime            Represents workflows as nodes and edges    Perfect architecture for Keprix
                                  with shared state                          playbooks
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Durable execution              Persist and resume long-running            Critical for research, launch, coding,
                                  workflows                                  and data pipelines
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Checkpointing                  Save state at each step                    Safer recovery after crash or restart
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Postgres checkpoint backend    Durable persistence in Postgres            Fits Keprix’s Postgres architecture
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   SQLite checkpoint backend      Lightweight local persistence              Good for single-user self-host installs
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Human interrupts               Pause for review, state edits, approval    Core governance primitive for Keprix
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Subgraphs                      Reusable nested workflows                  Reusable playbook modules
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Branching                      Conditional workflow paths                 Better decisions in Opportunity Engine
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Streaming state updates        Live workflow progress                     Better UI/TUI timeline
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Memory model                   Short-term and long-term state             Cleaner agent memory separation
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Prebuilt agent patterns        Common agent graph templates               Faster Keprix feature development
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   JS and Python SDK idea         Multi-language client support              Good for Keprix SDK roadmap
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Studio/prototyping concept     Visual workflow debugging                  Future Keprix Playbook Studio

  This is high priority. Keprix’s playbook engine should borrow heavily from LangGraph concepts.

  LaVague
  LaVague is valuable for browser automation and QA.

  Adopt these:

   Feature                        What It Does                               Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   World Model                    Reads objective plus current web page      Better web agent reasoning
                                  state and decides next instruction
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Action Engine                  Compiles instructions into Selenium or     Real browser execution layer
                                  Playwright actions
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Selenium driver                Browser automation with iframe support     Useful for admin panels, forms,
                                  and headless support                       dashboards
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Playwright driver              Browser automation with modern tooling     Stronger browser automation than raw
                                                                             scraping
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Chrome extension driver        Lets agent act in a user browser           Powerful desktop/browser companion
                                  session                                    feature
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Element highlighting           Shows what the agent is acting on          Trust and debugging for web UI
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Multi-tab support              Operates across tabs                       Better research and CRM workflows
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Test runner                    Tests web agents against sites             Regression testing for browser skills
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Token counter                  Estimates browser-agent cost               Useful for Keprix cost routing
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Logging and debugging tools    Captures actions, observations,            Better observability
                                  failures
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Gradio demo pattern            Quick interactive demo UI                  Useful for internal testing, not product
                                                                             UI
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   LaVague QA                     Turns Gherkin specs into web tests         Keprix could generate and run acceptance
                                                                             tests
  ─────────────────────────────  ─────────────────────────────────────────  ──────────────────────────────────────────
   Chrome extension               Browser-side agent control                 Strong candidate for Keprix browser
                                                                             extension

  Adopt with strict guardrails:

  - Never bypass login.
  - Never click purchase, publish, send, or delete without approval.
  - Log every browser action.
  - Screenshot before and after risky steps.

  SWE-agent
  SWE-agent is useful for Keprix’s self-coding and developer automation.

  Adopt these:

   Feature                       What It Does                                Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Single YAML configuration     Controls tools, prompts, environment,       Cleaner Keprix agent profile configs
                                 model, parsing
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Agent-computer interface      Structured shell and file editing           Better coding agent reliability
                                 workflow
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Issue-solving loop            Reads issue, edits repo, tests, iterates    Keprix can fix bugs and build prompts
                                                                             autonomously
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Patch trajectory recording    Stores the path of actions and decisions    Audit trail for self-coding
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Benchmark mode                Runs tasks across SWE-bench style           Keprix can evaluate coding performance
                                 datasets
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Bash-only config              Minimal shell mode                          Good for locked-down developer
                                                                             environments
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Human config                  Human-in-the-loop execution                 Good for approvals and pair programming
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Windowed replace              Safer file editing by scoped replacement    Reduce accidental file damage
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Parsing modes                 Backticks, XML, thought/action style        Better structured action extraction
                                 formats
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Filemap review configs        Helps agent understand repo structure       Useful for large monorepos like Carina
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   Coding challenge mode         General code task execution                 Good for Keprix project builder
  ────────────────────────────  ──────────────────────────────────────────  ──────────────────────────────────────────
   EnIGMA idea                   CTF/security challenge solving              Could improve Petraclus, but keep gated
                                                                             and approval-led

  Adopt especially:

  - trajectory logs
  - patch review loop
  - scoped file edits
  - benchmark harness
  - YAML-configured agent profiles

  TaskWeaver
  TaskWeaver is the strongest reference for analytics, ML, data science, and research notebooks.

  Adopt these:

   Feature                      What It Does                                Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   Code-first planning          Converts user task into executable          Better analytics and ML workflows
                                Python plan
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Stateful code execution      Preserves code history and in-memory        Essential for data analysis sessions
                                data
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Rich data structures         Handles DataFrames and complex objects,     Better SPSS/PSPP/Jamovi-style work
                                not just text
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Code verification            Checks generated code before execution      Safer execution
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Reflective execution         Agent reviews failures and adjusts          More reliable analysis
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Planner role                 Decomposes complex tasks                    Better project and research workflows
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Code Interpreter role        Executes Python safely                      Better local data work
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Shared memory                Stores information across roles             Better multi-role collaboration
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Experience selection         Reuses past workflows dynamically           Keprix can learn reusable playbooks
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Container execution          Runs code in isolated container             Security-first analytics execution
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Plugin-only mode             Calls approved plugins without arbitrary    Safer enterprise mode
                                code
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   CLI-only mode                Natural language command-line operation     Better terminal UX
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Vision input                 Reads charts, screenshots, images           Useful for research, dashboards, mobile
                                                                            screenshots
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Recepta reasoning role       Extra reasoning-oriented role               Could improve complex planning
  ───────────────────────────  ──────────────────────────────────────────  ───────────────────────────────────────────
   Observability integration    AgentOps-style monitoring                   Better debugging and enterprise reporting

  TaskWeaver plugins worth adopting:

   Plugin                 What It Does                          Keprix Benefit
  ━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   sql_pull_data          Pulls data from SQL into DataFrame    Business analytics, reporting
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   anomaly_detection      Detects abnormal data patterns        Fraud, operations, finance, SIEM
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   paper_summary          Summarises research papers            Deep research
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   speech2text            Transcribes audio                     Voice notes, meetings, local languages
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   text2speech            Generates speech                      Voice output
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   image2text             Extracts text from images             OCR and document workflows
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   text_classification    Classifies text                       Support, CRM, research tagging
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   klarna_search          Product search example                Ecommerce and product research
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   ascii_render           Renders text visuals                  Low priority
  ─────────────────────  ────────────────────────────────────  ────────────────────────────────────────
   tell_joke              Demo plugin                           Do not adopt

  Recommended Keprix Adoption Roadmap

  1. Workflow Engine Upgrade
     Adopt LangGraph-style state graphs, checkpointing, subgraphs, interrupts, and durable execution.

  2. Playbook Runtime
     Use CrewAI Flows plus LangGraph-style persistence to make Keprix playbooks reliable and inspectable.

  3. Role-Based Agent Teams
     Adopt CrewAI Crews and AutoGen AgentTool patterns:

  - Researcher
  - Analyst
  - Builder
  - Browser Operator
  - QA Agent
  - Compliance Reviewer
  - Launch Operator

  4. Browser Action Layer
     Adopt LaVague-style World Model plus Action Engine:

  - Selenium
  - Playwright
  - Chrome extension
  - element highlighting
  - action logs
  - screenshots

  5. Data and ML Workspace
     Adopt TaskWeaver-style stateful code execution:

  - DataFrame memory
  - Python notebooks
  - verified code
  - container execution
  - SQL pull
  - anomaly detection
  - paper summary
  - speech and OCR tools

  6. Self-Coding Agent
     Adopt SWE-agent style:

  - issue to patch loop
  - repo filemap
  - scoped replace
  - trajectory logs
  - benchmark harness

  7. Tool Expansion
     Adopt CrewAI tool categories:

  - search
  - scraping
  - RAG documents
  - vector stores
  - databases
  - OCR and media
  - GitHub and code search
  - Zapier and automation
  - E2B/Daytona sandbox

  8. Evaluation and Observability
     Adopt:

  - AutoGen Bench idea
  - CrewAI tracing
  - LangGraph execution traces
  - SWE-agent benchmark runs
  - TaskWeaver logs

  9. Enterprise-Ready Control
     Add:

  - approval gates
  - replayable traces
  - execution checkpoints
  - operator review
  - cost estimates
  - Scout event bridge

  What This Does For Keprix
  It turns Keprix from “self-hosted AI agent” into a real AI operating system:

  - LangGraph makes it durable.
  - CrewAI makes it collaborative.
  - LaVague makes it able to operate the web.
  - SWE-agent makes it able to build and repair software.
  - TaskWeaver makes it strong for data, analytics, ML, and research.
  - AutoGen gives mature multi-agent messaging ideas.

  What I Would Not Adopt Directly

  - AutoGen as a dependency, because it is in maintenance mode.
  - LaVague telemetry defaults, because Keprix should be privacy-first.
  - Uncontrolled browser execution.
  - Uncontrolled offensive cybersecurity execution from SWE-agent EnIGMA.
  - Demo-only tools like joke plugins or Gradio UI patterns for production.
  - Any feature that sends, publishes, spends, deletes, or changes customer data without approval.

