"""Deep research background pipeline."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from keprix.research.depth import get_depth_config
from keprix.research.errors import ResearchConfigError, ResearchPipelineError
from keprix.research.fetch import fetch_page_text
from keprix.research import search as research_search
from keprix.research.store import ResearchJob, get_research_store
from keprix.research.synthesis import decompose_query, synthesize_report


async def run_research_job(job: ResearchJob) -> None:
    store = get_research_store()
    cfg = get_depth_config(job.depth)
    started = time.time()
    try:
        sub_questions = await decompose_query(
            job.query,
            cfg.sub_questions,
            job.model_used,
            user_id=job.user_id,
            session_id=job.id,
        )
        job.sub_questions = sub_questions
        await store.emit(job, "sub_question_start", sub_questions=sub_questions)

        all_sources: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for question in sub_questions:
            if job._cancelled:
                job.status = "cancelled"
                await store.emit(job, "complete", status="cancelled")
                return
            results = await research_search.web_search(question, limit=cfg.sources_per_question)
            await store.emit(job, "source_fetched", question=question, count=len(results))
            for result in results:
                url = result.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                source_entry: dict[str, Any] = {
                    "title": result.get("title", ""),
                    "url": url,
                    "snippet": result.get("snippet", ""),
                    "sub_question": question,
                }
                try:
                    title, excerpt = await fetch_page_text(url)
                    if title:
                        source_entry["title"] = title
                    source_entry["excerpt"] = excerpt
                    await store.emit(job, "source_read", url=url, title=source_entry["title"])
                except Exception as exc:
                    source_entry["read_error"] = str(exc)
                all_sources.append(source_entry)
                job.sources = list(all_sources)

        if not all_sources:
            raise ResearchPipelineError("No sources were collected for this research job.")

        report, tokens = await synthesize_report(
            query=job.query,
            depth=job.depth,
            sub_questions=sub_questions,
            sources=all_sources,
            model=job.model_used,
            started_at=started,
            user_id=job.user_id,
            session_id=job.id,
        )
        job.report_markdown = report
        job.tokens_used = tokens
        job.status = "complete"
        from datetime import datetime, timezone

        job.completed_at = datetime.now(timezone.utc)
        try:
            from keprix.workspace.repository import workspace_repo

            user = {"id": job.user_id, "username": job.user_id}
            doc = workspace_repo.create_document(
                user,
                title=f"Research: {job.query[:80]}",
                content=report,
                tags=["research", "auto-generated"],
            )
            job.result_document_id = doc["id"]
        except Exception:
            job.result_document_id = None
        await store.persist(job)
        await store.emit(job, "synthesis_chunk", preview=report[:400])
        await store.emit(job, "complete", status="complete")
    except ResearchConfigError as exc:
        await _fail_job(job, store, str(exc), status="failed")
    except ResearchPipelineError as exc:
        await _fail_job(job, store, str(exc), status="failed")
    except Exception as exc:
        await _fail_job(job, store, str(exc), status="error")


async def _fail_job(job: ResearchJob, store: Any, message: str, *, status: str) -> None:
    job.status = status
    job.report_markdown = f"# Research failed\n\n{message}\n"
    from datetime import datetime, timezone

    job.completed_at = datetime.now(timezone.utc)
    await store.persist(job)
    await store.emit(job, "complete", status=status, error=message)


def schedule_research_job(job: ResearchJob) -> None:
    asyncio.create_task(run_research_job(job))
