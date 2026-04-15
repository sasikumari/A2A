"""
Document Agent — embedded pipeline integration.

All document generation now runs in-process via document_pipeline.py.
No HTTP calls to a separate microservice.

Gaps addressed:
  Gap 1  — correct RAG collection (upi_knowledge, not "default")
  Gap 2  — content cached after first fetch, never re-read on every poll
  Gap 4  — fallback flag propagated so frontend can show a warning
  Gap 5  — single poll error no longer triggers fallback; handled in frontend
  Gap 6  — retry_document() for per-doc retry
  Gap 8  — edit runs in sync endpoint thread, never blocks event loop
  Gap 9  — no HTTP timeout; edit runs to completion
  Gap 14 — per-doc-type fallback content via agents/fallbacks.py
  Gap 17 — TTL eviction in document_pipeline
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("docgen.agent")

# ---------------------------------------------------------------------------
# Canvas → prompt
# ---------------------------------------------------------------------------

def _canvas_to_prompt(canvas: dict, feedback: Optional[str] = None) -> str:
    """Convert a product canvas dict into a rich natural-language prompt."""
    feature     = canvas.get("featureName", "UPI Feature")
    build_title = canvas.get("buildTitle", feature)

    lines = [
        "Generate a comprehensive NPCI-grade document suite for the following UPI feature.",
        "",
        f"Feature Name: {feature}",
        f"Build Title: {build_title}",
        "",
    ]

    for section in canvas.get("sections", []):
        title   = section.get("title", "").strip()
        content = section.get("content", "").strip()
        if title and content:
            lines += [f"### {title}", content, ""]

    rbi = canvas.get("rbiGuidelines", "").strip()
    if rbi:
        lines += ["### RBI / NPCI Regulatory Context", rbi, ""]

    eco = canvas.get("ecosystemChallenges", "").strip()
    if eco:
        lines += ["### Ecosystem Challenges", eco, ""]

    if feedback:
        lines += ["### Additional Refinement Instructions", feedback, ""]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Document Agent
# ---------------------------------------------------------------------------

class DocumentAgent:
    """
    Orchestrates document generation through the embedded LangGraph pipeline.

    Public interface (matches what main.py calls):
      start_generation(canvas, feedback)      → {status, bundle_id, feature_name}
      get_bundle_status(bundle_id, feature)   → full bundle status dict
      fetch_document(job_id, doc_type, feature) → Document dict | None
      edit_document(job_id, instruction, feature, doc_type) → Document dict
      retry_document(canvas, bundle_id, doc_type) → {bundle_id, job_id}
    """

    # ------------------------------------------------------------------
    # start_generation
    # ------------------------------------------------------------------

    def start_generation(self, canvas: dict, feedback: Optional[str] = None) -> dict:
        """
        Submit all 4 documents for generation and return tracking metadata immediately.
        Never blocks. If pipeline is unavailable, returns fallback documents so the
        frontend can show something (Gap 4: flagged explicitly as 'fallback').
        """
        import document_pipeline as dp

        prompt  = _canvas_to_prompt(canvas, feedback)
        feature = canvas.get("featureName", "UPI Feature")

        logger.info("[DocumentAgent] Submitting bundle for feature='%s'", feature)
        bundle_id = dp.submit_bundle(
            prompt=prompt,
            feature=feature,
            organization_name="NPCI",
            brd_title=f"BRD — {feature}",
            tsd_title=f"TSD — {feature}",
            product_note_title=f"Product Note — {feature}",
            circular_title=f"Circular — {feature}",
        )

        if not bundle_id:
            logger.warning(
                "[DocumentAgent] Pipeline unavailable — returning fallback docs for '%s'", feature
            )
            return {
                "status":       "fallback",
                "feature_name": feature,
                "documents":    self._fallback_docs(canvas),
                "reason":       "Document generation pipeline could not be loaded. "
                                "Showing local preview only.",
            }

        # Store the prompt so per-doc retries can reuse it
        dp.store_bundle_prompt(bundle_id, prompt)

        return {
            "status":       "pending",
            "bundle_id":    bundle_id,
            "feature_name": feature,
        }

    # ------------------------------------------------------------------
    # get_bundle_status
    # ------------------------------------------------------------------

    def get_bundle_status(self, bundle_id: str, feature_name: str) -> dict:
        """
        Return normalized bundle status.
        Gap 2 FIX: completed doc content is fetched from disk exactly once then cached.
        """
        import document_pipeline as dp

        try:
            return dp.get_bundle(bundle_id, feature_name)
        except KeyError:
            # Bundle not in memory — server may have restarted
            logger.warning(
                "[DocumentAgent] bundle_id=%s not found in memory "
                "(server restart?) — returning empty-completed state",
                bundle_id,
            )
            return {
                "bundle_id":      bundle_id,
                "overall_status": "failed",
                "jobs":           [],
                "documents":      [],
                "reason":         "Bundle state lost — please regenerate documents.",
            }

    # ------------------------------------------------------------------
    # fetch_document
    # ------------------------------------------------------------------

    def fetch_document(
        self, job_id: str, doc_type: str, feature: str, force_refresh: bool = False
    ) -> Optional[dict]:
        """Return the Document dict for a single completed job."""
        import document_pipeline as dp
        return dp.get_job_content(job_id, doc_type, feature, force_refresh=force_refresh)

    # ------------------------------------------------------------------
    # edit_document
    # ------------------------------------------------------------------

    def edit_document(
        self,
        job_id: str,
        edit_instruction: str,
        feature: str,
        doc_type: str,
    ) -> dict:
        """
        Apply a full-document edit instruction and return the refreshed Document dict.

        Gap 8 FIX: runs synchronously in FastAPI's thread pool — no event-loop blocking.
        Gap 9 FIX: no HTTP timeout — runs until completion.
        """
        import document_pipeline as dp

        dp.run_edit(job_id, edit_instruction)

        # Re-fetch from disk (cache was cleared by run_edit)
        refreshed = dp.get_job_content(job_id, doc_type, feature, force_refresh=True)
        if not refreshed:
            raise RuntimeError(
                f"Edit completed for job {job_id} but refreshed content could not be read."
            )
        return refreshed

    # ------------------------------------------------------------------
    # retry_document  (Gap 6)
    # ------------------------------------------------------------------

    def retry_document(
        self, canvas: dict, bundle_id: str, doc_type: str
    ) -> dict:
        """
        Spawn a fresh pipeline job for a single failed document without regenerating
        the whole bundle.
        Gap 6 FIX: per-doc retry preserves the 3 already-completed documents.
        """
        import document_pipeline as dp

        feature = canvas.get("featureName", "UPI Feature")
        prompt  = dp.get_bundle_prompt(bundle_id) or _canvas_to_prompt(canvas)

        new_job_id = dp.retry_doc(
            bundle_id=bundle_id,
            doc_type=doc_type,
            prompt=prompt,
            feature=feature,
        )
        if not new_job_id:
            raise RuntimeError("Pipeline unavailable for retry.")

        return {"bundle_id": bundle_id, "job_id": new_job_id, "doc_type": doc_type}

    # ------------------------------------------------------------------
    # generate  (legacy blocking path — kept for backwards compat)
    # ------------------------------------------------------------------

    def generate(self, canvas: dict, feedback: Optional[str] = None) -> list:
        """
        Legacy: submit bundle and poll synchronously until all docs complete.
        Used only by old code paths that haven't migrated to the async poll flow.
        """
        import document_pipeline as dp
        import time

        result = self.start_generation(canvas, feedback)
        if result["status"] == "fallback":
            return result.get("documents", [])

        bundle_id   = result["bundle_id"]
        feature     = result["feature_name"]
        deadline    = time.time() + 300  # 5 min max
        poll_interval = 3

        while time.time() < deadline:
            try:
                status = self.get_bundle_status(bundle_id, feature)
                overall = status.get("overall_status", "running")
                jobs    = status.get("jobs", [])

                all_terminal = all(
                    j.get("status") in {"completed", "failed"} for j in jobs
                )
                if overall in {"completed", "partial"} or all_terminal:
                    docs = status.get("documents", [])
                    if not docs:
                        docs = self._fallback_docs(canvas)
                    return docs
            except Exception as exc:
                logger.warning("[DocumentAgent.generate] Poll error: %s", exc)

            time.sleep(poll_interval)

        logger.warning("[DocumentAgent.generate] Timed out — returning fallback docs")
        return self._fallback_docs(canvas)

    # ------------------------------------------------------------------
    # Fallbacks  (Gap 14: per-doc-type, not generic)
    # ------------------------------------------------------------------

    def _fallback_docs(self, canvas: dict) -> list:
        try:
            from agents.fallbacks import generate_fallback_documents
            return generate_fallback_documents(canvas)
        except Exception as exc:
            logger.warning("[DocumentAgent] Fallback generator failed: %s", exc)
            return []
