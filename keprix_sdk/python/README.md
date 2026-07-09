# Keprix App Foundation SDK (Python)

Install:

```bash
pip install -e keprix_sdk/python
```

Quick start:

```python
from keprix_sdk import KeprixApp, Domain, Entity, Field, Operation

app = KeprixApp(
    name="my-app",
    keprix_url="http://localhost:3333",
    api_token="your-api-key",
)
```

See `examples/invoice_app.py` and `examples/crm_app.py`.
