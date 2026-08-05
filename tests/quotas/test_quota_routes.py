from fastapi import FastAPI
from fastapi.testclient import TestClient

from keprix.api.quota_routes import router


def test_quota_routes_expose_scheduler_before_product_route() -> None:
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    response = client.get("/api/admin/quotas/scheduler")

    assert response.status_code == 200
    assert response.json()["max_slots"] >= 1
    assert "active_slots" in response.json()
