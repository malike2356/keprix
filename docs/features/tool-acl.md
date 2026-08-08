# Tool ACL admin console

Operators manage **product tool ACL** and **resource-scoped grants** from the
workspace Admin group at `/admin/tool-acl`.

This is distinct from **Generated tools** (`/admin/tools`), which reviews
mutation-engine proposals. The nav item **Tool ACL** must open `/admin/tool-acl`
only.

## Who can use it

| Role | Access |
| --- | --- |
| admin / owner / superadmin / developer | Full GUI (grants, revoke, broad, checks) |
| other roles | Honest 403-style message in the GUI; grant mutations return HTTP 403 |

## UI sections

1. **Products** - list registered products; show allowed/denied tool patterns (read-only matrix view).
2. **Resource grants** - load by actor type + ID; create exact grants; revoke with confirm; record broad (legacy unrestricted) grants with confirm.
3. **Check playground** - dry-run `POST /api/security/acl/check` and `POST /api/security/acl/resources/check`.
4. **Audit** - filterable tail of ACL decisions.

## API

| Method | Path |
| --- | --- |
| GET | `/api/security/acl/products` |
| GET | `/api/security/acl/products/{product_id}` |
| POST | `/api/security/acl/check` |
| GET | `/api/security/acl/audit` |
| GET | `/api/security/acl/resources/catalog` |
| GET | `/api/security/acl/resources/grants` |
| PUT | `/api/security/acl/resources/grants` |
| DELETE | `/api/security/acl/resources/grants` |
| POST | `/api/security/acl/resources/check` |
| POST | `/api/security/acl/resources/broad` |

See also [Resource-scoped tool ACL](resource-tool-acl.md).

## Empty states

- No products registered
- No actor loaded / no exact grants (unrestricted until narrowed)
- No audit entries

## Related

- [Resource-scoped tool ACL](resource-tool-acl.md)
- [Navigation and roles](navigation-and-roles.md)
- [Governance](../security/governance.md)
- Operator GUI gap inventory: `docs/architecture/operator-gui-gap-inventory.md` (prompt 468)
