# Legal Placeholder Checklist

All legal documents across Carina Aiva, Keprix, and Petraclus contain
placeholders that must be filled before any document is published to users.

This checklist must be completed before any product goes live. A product that
publishes legal documents with `[TO BE INSERTED]` in them is operating without
valid legal terms.

---

## Information Needed (Get These First)

| Item | Status | Value |
| --- | --- | --- |
| Verlox Limited company number | UNFILLED | |
| Verlox Limited registered address | UNFILLED | |
| Email provider name and location | FILLED | Resend Inc. (primary), Postmark by ActiveCampaign (fallback). Both US-based. SCCs in place for UK GDPR transfers. |
| ICO registration number | FILLED | ZC108946 |
| Scout Govern price | CONFIRMED: £79/month | RAG-007 updated to £79 on 2026-06-30. PRODUCT_POSITIONING.md was correct. |

---

## Files to Update

### Carina Aiva Legal

**`/opt/lampp/htdocs/verlox/carina/aiva/legal/TERMS_OF_SERVICE.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - replace with effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - replace with last updated date
- [ ] Line 38: `[TO BE INSERTED]` (company number) - replace with Verlox Ltd company number
- [ ] Line 38: `[TO BE INSERTED]` (registered address) - replace with registered address

**`/opt/lampp/htdocs/verlox/carina/aiva/legal/PRIVACY_POLICY.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - last updated date
- [ ] Line 20: `[TO BE INSERTED]` - company number
- [ ] Line 21: `[TO BE INSERTED]` - registered address
- [x] Line 136: email provider - FILLED: Resend Inc. (primary) / Postmark by ActiveCampaign (fallback)

**`/opt/lampp/htdocs/verlox/carina/aiva/legal/DATA_PROCESSING_AGREEMENT.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - last updated date
- [x] Line 286: email provider - FILLED: Resend Inc. (primary) / Postmark by ActiveCampaign (fallback), US, SCCs

### Keprix Legal

**`/opt/lampp/htdocs/verlox/keprix/legal/TERMS_OF_SERVICE.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - last updated date
- [ ] Line 12: `[TO BE INSERTED]` (company number)
- [ ] Line 12: `[TO BE INSERTED]` (registered address)

**`/opt/lampp/htdocs/verlox/keprix/legal/PRIVACY_POLICY.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - last updated date
- [ ] Line 17: `[TO BE INSERTED]` - company number
- [ ] Line 18: `[TO BE INSERTED]` - registered address

### Petraclus Legal

**`/opt/lampp/htdocs/verlox/carina/petraclus/legal/TERMS_OF_SERVICE.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - last updated date
- [ ] Line 12: `[TO BE INSERTED]` (company number)
- [ ] Line 12: `[TO BE INSERTED]` (registered address)

**`/opt/lampp/htdocs/verlox/carina/petraclus/legal/PRIVACY_POLICY.md`**
- [ ] Line 4: `[TO BE SET ON FIRST PUBLICATION]` - effective date
- [ ] Line 5: `[TO BE SET ON FIRST PUBLICATION]` - last updated date
- [ ] Line 11: `[TO BE INSERTED]` - company number
- [ ] Line 12: `[TO BE INSERTED]` - registered address

**`/opt/lampp/htdocs/verlox/carina/petraclus/legal/AUTHORIZED_USE_POLICY.md`**
- [ ] Check for any remaining placeholders

---

## After Filling Placeholders

1. Have a UK solicitor review all documents before publication. This is not optional
   for the Aiva DPA or Petraclus AUP. Both carry significant legal obligations.

2. Confirm the ICO registration covers all three products. ZC108946 is registered
   for Verlox Limited. Verify that processing activities for Keprix key server data
   and Petraclus key server data are covered under the existing registration or
   require an update notification to ICO.

3. Create version 1.0 tags in each product's GitHub repo when legal docs go live.
   Legal document version is tracked by the file's own version field, not git tags,
   but a repo tag helps establish a timestamp for when terms became active.

4. Set up a legal@verlox.uk alias or route all contact@verlox.uk legal queries to
   a dedicated folder. Legal documents reference contact@verlox.uk for all queries.
