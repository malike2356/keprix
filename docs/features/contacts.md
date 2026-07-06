# Contacts

The contacts workspace stores people, emails, phones, and sync preferences for agent-assisted outreach.

## Web UI (`/contacts`)

- Search and browse contacts
- View primary email, labels, and tags
- Link to email and messaging workflows

Sync UI: `/contacts/sync` for address book import status.

## API

| Action | Endpoint |
| --- | --- |
| List | `GET /api/contacts` |
| Create | `POST /api/contacts` |
| Update | `PUT /api/contacts/{id}` |
| Delete | `DELETE /api/contacts/{id}` |
| Search | `GET /api/contacts/search?q=` |

Contact records support multiple emails and phones with primary flags.

## Preferences

`GET /api/contacts/preferences` returns sync and confirmation settings (for example `confirm_before_email`).

## Agent integration

Agents can resolve contacts before sending email or scheduling meetings. Pair with [Email](email.md) and [Calendar](calendar.md).

## Related

- [Email](email.md)
- [Workspace overview](workspace.md)
