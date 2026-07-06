# Localization

Keprix supports multiple interface languages and locale-aware formatting for dates, times, and numbers. System messages, UI labels, and agent persona prompts are all translated.

## Supported languages

| Language | Code | Coverage |
| --- | --- | --- |
| English (default) | `en` | 100% |
| French | `fr` | ~85% |
| German | `de` | ~80% |
| Spanish | `es` | ~80% |
| Portuguese (Brazil) | `pt-BR` | ~75% |
| Arabic | `ar` | ~70% (RTL support) |
| Chinese (Simplified) | `zh-CN` | ~70% |
| Japanese | `ja` | ~65% |

Strings not yet translated fall back to English.

## Setting the instance default language

```bash
KEPRIX_LOCALE=en    # default for new users and unauthenticated pages
```

## Per-user language preference

Each user can set their preferred language in **Profile > Preferences > Language**. The selected locale is stored with the user account and used for all UI text, agent messages, and date/time formatting.

## Date and time formatting

```bash
KEPRIX_TIMEZONE=UTC    # instance default timezone (IANA name, e.g. Africa/Accra)
```

Users can override the timezone in their profile. All stored timestamps are UTC; formatting is applied at display time.

## Contributing translations

Translation files live in `frontend/messages/` as JSON files, one per locale (e.g., `en.json`, `fr.json`). Add a missing string:

1. Add the key-value pair to the relevant locale file.
2. Add the same key to all other locale files with an empty string or a machine-translated draft.
3. Open a pull request.

The translation system uses `next-intl`. See the `next-intl` documentation for pluralisation and interpolation syntax.

## Agent language

The agent's response language follows the conversation's locale setting. By default, the agent mirrors the language the user writes in.

To force responses in a specific language regardless of input language:

```bash
KEPRIX_AGENT_RESPONSE_LANGUAGE=en   # force English responses
```

Or add an instruction to the persona system prompt in **Admin > Settings > Persona > SAGE**:

```
Always respond in English, regardless of the language used in the input.
```

## RTL support

Arabic and Hebrew interfaces render right-to-left. The frontend uses CSS logical properties throughout for correct RTL layout. If you encounter an RTL layout bug, file an issue.

## Number and currency formatting

The agent formats numbers and currencies according to the active locale. Tool outputs (research reports, analytics results) use the instance locale by default.

## Related

- [Voice](voice.md)
- [Configuration: environment variables](../configuration/environment-variables.md)
- [Control center](control-center.md)
