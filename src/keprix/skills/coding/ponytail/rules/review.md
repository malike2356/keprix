# ponytail-review

Review current code changes for over-engineering only, not correctness. One line per finding: `L<line>: <tag> <what to cut>. <replacement>.`

Tags: `delete`, `stdlib`, `native`, `yagni`, `shrink`.

End with net lines removable. If nothing to cut: `Lean already. Ship.`
