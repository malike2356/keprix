# Developer mode

Developer mode marks this host as the installation owner. It unlocks local-only conveniences documented in Prompt 01.

## Enable

```bash
keprix init
```

Answer `y` when asked if you are the owner. Identity files are written under `~/.keprix/identity/`.

## Check status

```bash
keprix identity status
```

## Revoke

```bash
keprix identity revoke
```

## Environment flag

`KEPRIX_DEVELOPER_MODE` is set automatically by `keprix init`. Do not toggle it manually unless you understand the security impact.

See also [Developer identity](../configuration/developer-identity.md).
