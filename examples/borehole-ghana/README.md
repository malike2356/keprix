# Ghana borehole advisor example

This example demonstrates Prompt 27 localization for a borehole drilling intake workflow in Ghana.

## Flow

1. User sends a Twi voice note asking whether a location is suitable for a borehole.
2. Keprix transcribes the voice note and detects Twi/Akan.
3. Keprix translates the request into English (Ghana operating language).
4. The borehole playbook applies the `borehole_drilling_ghana_v1` glossary.
5. Keprix asks for missing fields: community, GPS location, soil type, nearby wells, household count, budget range.
6. Keprix replies in Twi text and optional audio when voice output is enabled.
7. Operator review mode shows original transcript, English translation, and final local-language response.

## Disclaimer

Keprix is not a licensed hydrogeologist. This workflow collects intake, explains next steps, and routes jobs to qualified professionals.

## Playbook metadata

See `playbook.yaml` for localization-aware playbook settings.

## Try it

```bash
cd /opt/lampp/htdocs/verlox/keprix
.venv/bin/python -m pytest tests/localization/test_borehole_example.py -q
.venv/bin/keprix language detect "Me pɛ borehole wɔ Kumasi"
```
