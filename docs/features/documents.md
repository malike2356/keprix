# Documents

Browse, upload, and edit workspace documents from `/documents`.

## Features

- List documents with title, format, and tags
- Create markdown or plain text documents
- Update content and metadata
- Delete with confirmation

Documents are stored per workspace user in PostgreSQL.

## API

| Action | Endpoint |
| --- | --- |
| List | `GET /api/workspace/documents` |
| Create | `POST /api/workspace/documents` |
| Update | `PUT /api/workspace/documents/{id}` |
| Delete | `DELETE /api/workspace/documents/{id}` |

## Agent access

Agents can read and write documents via workspace tools. Exported sessions may include document references.

## Related

- [Notes](notes.md)
- [Memory and RAG](memory.md)
- [Workspace overview](workspace.md)
