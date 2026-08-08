# Social discovery (API-first)

Keprix social discovery is **API-first**. Scrapers for Instagram, Facebook, TikTok, and LinkedIn are Nice/Ultimate only and stay feature-flagged **off** by default.

## Adapters

| Adapter | Purpose | Credentials |
| --- | --- | --- |
| `linkedin_api` | LinkedIn Marketing / org pages | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` |
| `meta_graph` | Meta Graph (Facebook / Instagram) | `META_APP_ID`, `META_APP_SECRET` |
| `tiktok_api` | TikTok Marketing API | `TIKTOK_APP_ID`, `TIKTOK_APP_SECRET` |
| `social_csv_export` | Ads manager / lead-gen CSV export | none (operator file) |

When credentials are missing, health and discovery return `not_configured` with a clear message. They do not fall back to scrape.

## Scrape refusal

If an agent or operator asks to "scrape Instagram" (or similar), Keprix refuses and points to the API adapters or CSV export path. Scraping those platforms often violates their Terms of Service.

## Soft Wall

Connecting OAuth apps for social APIs should go through Soft Wall (`social_oauth_connect`). Discovery still produces candidates only; contactability and outreach are separate policy decisions.

## Flags

Experimental scrape code (if ever added) must remain behind an explicit flag defaulting to off. Do not ship illegal bots.
