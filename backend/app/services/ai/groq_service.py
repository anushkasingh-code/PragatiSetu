import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from backend.app.config import settings
from backend.app.schemas.ai import ExplainResponse, VectorSearchResult
from backend.app.services.ai.vector_retriever import search_schedule_activities

logger = logging.getLogger("pragatisetu.groq_service")

class GroqExplanationService:
    """
    Lightweight Groq LLM integration for generating grounded natural-language explanations
    and reviewer assistance using retrieved Vector DB context.
    
    CRITICAL ARCHITECTURAL CONSTRAINTS:
    - Informational only: Groq never decides Activity ID, status, progress, or schedule state.
    - Grounded: Groq is strictly supplied retrieved candidate activities from the Vector DB.
    - Protected: Any hallucinated activity ID not present in retrieved context is discarded.
    - Graceful: Fully non-blocking and optional; handles missing keys or network timeouts cleanly.
    """

    def __init__(self, client: Any = None):
        self._client = client

    def _get_client(self) -> Optional[Any]:
        if self._client is not None:
            return self._client

        api_key = getattr(settings, "GROQ_API_KEY", "")
        if not api_key:
            return None

        try:
            from groq import Groq  # type: ignore
            self._client = Groq(api_key=api_key)
            return self._client
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")
            return None

    def explain_query_context(
        self,
        project_id: str,
        query: str,
        activity_ids: Optional[List[str]] = None,
        top_k: int = 3,
        chroma_client: Any = None
    ) -> ExplainResponse:
        """
        Retrieves relevant baseline activities via Vector DB and generates a structured explanation using Groq.
        """
        # 1. Retrieve Candidate Context from Vector DB
        retrieved: List[VectorSearchResult] = search_schedule_activities(
            project_id=project_id,
            query=query,
            top_k=top_k,
            client=chroma_client
        )

        # If specific activity_ids were requested, prioritize or filter
        if activity_ids:
            allowed_set = set(activity_ids)
            filtered_retrieved = [r for r in retrieved if r.activity_id in allowed_set]
            if filtered_retrieved:
                retrieved = filtered_retrieved

        valid_candidate_ids = {r.activity_id for r in retrieved}

        # 2. Check Groq Availability
        groq_enabled = getattr(settings, "GROQ_ENABLED", False)
        api_key = getattr(settings, "GROQ_API_KEY", "")

        if not groq_enabled or not api_key:
            return ExplainResponse(
                available=False,
                summary="Groq LLM explanation service is disabled or GROQ_API_KEY is not configured.",
                grounded_candidates=list(valid_candidate_ids),
                reasoning=["Local semantic vector search completed successfully."],
                warnings=["Groq AI reasoning is inactive. Returning semantic retrieval context only."],
                retrieved_context=retrieved
            )

        client = self._get_client()
        if client is None:
            return ExplainResponse(
                available=False,
                summary="Groq client could not be initialized.",
                grounded_candidates=list(valid_candidate_ids),
                reasoning=[],
                warnings=["Groq SDK or client initialization failed."],
                retrieved_context=retrieved
            )

        # 3. Construct Grounded RAG Prompt
        context_items = []
        for r in retrieved:
            meta = r.metadata
            item_desc = (
                f"- Activity ID: {r.activity_id}\n"
                f"  Discipline: {meta.get('discipline', 'N/A')}\n"
                f"  Identifier: {meta.get('identifier', 'N/A')}\n"
                f"  Location: {meta.get('location', 'N/A')}\n"
                f"  Description: {meta.get('description', r.document)}\n"
                f"  Similarity: {r.similarity}"
            )
            context_items.append(item_desc)

        context_block = "\n\n".join(context_items) if context_items else "No matching baseline activities found in vector index."

        system_prompt = (
            "You are PragatiSetu AI Assistant for construction schedule matching.\n"
            "Your role is to provide clear, factual explanations of how field report queries relate to retrieved baseline schedule activities.\n"
            "CRITICAL RULES:\n"
            "1. ONLY reference activity IDs explicitly provided in the RETRIEVED BASELINE CONTEXT.\n"
            "2. NEVER invent or hallucinate activity IDs.\n"
            "3. Return strictly valid JSON adhering to the required schema.\n"
            "4. Do NOT make schedule change decisions; only explain relationships and similarities."
        )

        user_prompt = (
            f"PROJECT ID: {project_id}\n"
            f"FIELD QUERY: \"{query}\"\n\n"
            f"RETRIEVED BASELINE CONTEXT:\n{context_block}\n\n"
            "Provide a structured JSON response with:\n"
            "- summary: A concise 1-2 sentence explanation of the correlation between the query and candidate activities.\n"
            "- candidate_activity_ids: List of activity IDs from the context that best match the query.\n"
            "- reasoning: Array of bullet points explaining specific identifier, location, or discipline alignments.\n"
            "- warnings: Array of any discrepancies or ambiguities noticed."
        )

        model_name = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")

        # 4. Invoke Groq API safely with Exception Guard
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=600
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)

            raw_candidates = parsed.get("candidate_activity_ids", [])
            if isinstance(raw_candidates, str):
                raw_candidates = [raw_candidates]

            # 5. Activity ID Protection & Hallucination Filter
            grounded_candidates: List[str] = []
            warnings: List[str] = list(parsed.get("warnings", []))

            for cid in raw_candidates:
                cid_clean = str(cid).strip()
                if cid_clean in valid_candidate_ids:
                    grounded_candidates.append(cid_clean)
                else:
                    msg = f"Rejected hallucinated activity ID '{cid_clean}' not present in retrieved context."
                    logger.warning(msg)
                    warnings.append(msg)

            return ExplainResponse(
                available=True,
                summary=str(parsed.get("summary", "Explanation generated successfully.")),
                grounded_candidates=grounded_candidates,
                reasoning=[str(r) for r in parsed.get("reasoning", [])],
                warnings=warnings,
                retrieved_context=retrieved
            )

        except Exception as e:
            logger.warning(f"Groq API call failed or timed out: {e}")
            return ExplainResponse(
                available=False,
                summary="Groq LLM explanation unavailable due to service/network error.",
                grounded_candidates=list(valid_candidate_ids),
                reasoning=["Semantic vector search was executed, but LLM completion failed."],
                warnings=[f"Groq error: {str(e)}"],
                retrieved_context=retrieved
            )
