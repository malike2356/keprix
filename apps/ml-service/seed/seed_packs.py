import asyncio
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8200"
SEED_DIR = Path(__file__).parent / "corpus"

PACKS = [
    {"pack_id": "borehole-operations", "display_name": "Borehole Operations Corpus"},
    {"pack_id": "wrc-regulations", "display_name": "WRC Regulations (LI 1827)"},
    {"pack_id": "gbda-guidelines", "display_name": "GBDA Guidelines"},
]


async def seed() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=120) as client:
        existing = {pack["pack_id"] for pack in (await client.get("/embeddings/packs")).json()["packs"]}
        for pack in PACKS:
            if pack["pack_id"] not in existing:
                await client.post("/embeddings/packs", json=pack)
                print(f"Created pack: {pack['pack_id']}")

        for corpus_file in SEED_DIR.rglob("*.txt"):
            pack_id = corpus_file.parent.name
            response = await client.post(
                "/embeddings/ingest",
                json={
                    "pack_id": pack_id,
                    "source_uri": corpus_file.name,
                    "content": corpus_file.read_text(encoding="utf-8"),
                    "metadata": {"source_label": corpus_file.stem},
                },
            )
            data = response.json()
            print(f"Ingested {data['chunks_stored']} chunks from {corpus_file.name} into {pack_id}")


if __name__ == "__main__":
    asyncio.run(seed())
