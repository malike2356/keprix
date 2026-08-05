# Onboard

Use this skill when an operator says `/onboard`, asks to set up their AI operating system, or needs day-one context files.

## Flow

Ask one question at a time and save each answer:

1. Who are you, what do you sell, and who is your ICP?
2. Paste 1-2 recent writing samples verbatim. Do not summarize or rewrite them.
3. What are your top 2-3 priorities for the next 90 days?
4. What are your biggest pains or bottlenecks?
5. What tools do you use daily?
6. What should the agent never do?
7. What working cadence do you prefer?

On completion, write `context/*.md`, `context/intake.json`, and a `connections.md` draft through the onboard API or service.

## Welcome Copy

Mention the three habits once at the start:

- Default shift: ask how AI could do 30% before manual work.
- Function breakdown: split the work into context, connections, capabilities, and cadence.
- Curiosity: keep looking for small repeatable loops to automate.

## Completion

After the seventh answer, summarize the created files and link the next steps:

- Day 2: connection matrix.
- Day 7: Four C's maturity audit.
