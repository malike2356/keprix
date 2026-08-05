# Built app starter

This starter manifest demonstrates the `built_app.yaml` shape used by installed apps.

Install it into a development data directory:

```bash
mkdir -p "$KEPRIX_DATA_DIR/built_apps/starter"
cp examples/built-app-starter/built_app.yaml "$KEPRIX_DATA_DIR/built_apps/starter/"
```

The app appears once under Installed apps and owns its inner navigation under `/apps/starter`.

## AbbiS handoff

AbbiS should mount as `/apps/abbis` with its product code in `verlox/apps-on-keprix/abbis/`. Copy this manifest shape, change `id` to `abbis`, and keep AbbiS module routes in the built app layout instead of Keprix core navigation.
