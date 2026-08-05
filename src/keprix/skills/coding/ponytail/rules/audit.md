# ponytail-audit

Audit the repository for over-engineering only, not correctness. Rank biggest cuts first:

`<tag> <what to cut>. <replacement>. [path]`

Tags: `delete`, `stdlib`, `native`, `yagni`, `shrink`.

End with net lines and dependencies removable. If nothing to cut: `Lean already. Ship.`
