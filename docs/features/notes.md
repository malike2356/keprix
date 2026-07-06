# Notes

Linked notes for quick capture and reference at `/notes`.

## Features

- Create notes with title, body, and tags
- Pin important notes
- Search across note content
- Link notes to research and chat context

## API

| Action | Endpoint |
| --- | --- |
| List / search | `GET /api/workspace/notes?search=` |
| Create | `POST /api/workspace/notes` |
| Update | `PUT /api/workspace/notes/{id}` |
| Delete | `DELETE /api/workspace/notes/{id}` |

## Obsidian export

Research workspace supports Obsidian vault adapters. See `docs/research/obsidian-vault-adapter.md` for adapter details.

## Related

- [Documents](documents.md)
- [Deep research](research.md)
