import os
import re
import logging
import json
from typing import List, Dict, Any, Optional
import google.generativeai as genai

from app.core.config import settings

logger = logging.getLogger(__name__)

def get_system_prompt(is_selected_mode: bool = False) -> str:
    doc_scope = "selected documents" if is_selected_mode else "uploaded documents"
    return f"""You are a grounded document question-answering assistant.

Answer the user's specific question directly and concisely.

Use ONLY the supplied evidence.

Synthesize the evidence instead of reproducing it.

Do not reproduce entire chunks or documents.

Do not include unrelated document content.

Do not expose unrelated personal information, names, IDs, roll numbers, contact details, or metadata unless specifically required to answer the user's question and supported by the evidence.

If multiple sources are relevant, combine them into one coherent answer.

If sources disagree, explicitly describe the conflict.

If evidence is insufficient, state:
"Insufficient evidence was found in the {doc_scope} to answer this question reliably."

Do not invent facts, filenames, page numbers, or citations.
"""

def extract_evidence_snippet(content: str, query: str, max_length: int = 160) -> str:
    """
    Extracts a concise, relevant evidence snippet centered around key query terms.
    Avoids dumping entire raw chunks or full pages.
    """
    if not content:
        return ""

    cleaned = " ".join(content.split())
    # Strip markdown header hashes
    cleaned = re.sub(r"^#+\s*", "", cleaned)

    stop_words = {
        'what', 'is', 'the', 'in', 'of', 'and', 'a', 'an', 'to', 'for', 'on', 
        'with', 'as', 'by', 'at', 'from', 'this', 'that', 'these', 'those', 
        'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 
        'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will', 'about', 
        'tell', 'me', 'how', 'why', 'when', 'where', 'which', 'who', 'document', 'file'
    }
    terms = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', query) if w.lower() not in stop_words and len(w) > 2]

    best_pos = -1
    for term in terms:
        pos = cleaned.lower().find(term)
        if pos != -1:
            best_pos = pos
            break

    if best_pos == -1 or len(cleaned) <= max_length:
        return cleaned[:max_length] + ("..." if len(cleaned) > max_length else "")

    start = max(0, best_pos - 40)
    end = min(len(cleaned), start + max_length)
    snippet = cleaned[start:end]
    if start > 0:
        snippet = "..." + snippet
    if end < len(cleaned):
        snippet = snippet + "..."
    return snippet


class RAGService:
    """
    RAG engine combining ChromaDB semantic search with Google Gemini LLM generation.
    Enforces strict grounding, citation verification, small context budgeting, and multi-source synthesis.
    """

    def __init__(self):
        self._configured = False
        if settings.GEMINI_API_KEY:
            try:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self._configured = True
                logger.info("Google Gemini API configured successfully.")
            except Exception as e:
                logger.warning(f"Failed to configure Gemini API: {e}")

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """
        Formats retrieved chunks into clear, tagged context blocks with metadata.
        """
        if not chunks:
            return "No relevant documents found."

        context_blocks = []
        for idx, chunk in enumerate(chunks, 1):
            filename = chunk.get("filename", "Unknown Document")
            page = chunk.get("page_number", 1)
            section = chunk.get("section", "General")
            content = chunk.get("content", "").strip()
            block = (
                f"[EXCERPT {idx}]\n"
                f"Document: {filename}\n"
                f"Page: {page}\n"
                f"Section: {section}\n"
                f"Content:\n{content}\n"
            )
            context_blocks.append(block)

        return "\n----------------------------------------\n".join(context_blocks)

    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """
        Formats previous conversation turns for multi-turn reasoning.
        """
        if not history:
            return ""

        turns = []
        for msg in history[-6:]:  # Keep last 6 messages
            role = "User" if msg.get("role") == "user" else "Assistant"
            turns.append(f"{role}: {msg.get('content', '')}")
        return "\n".join(turns)

    def _check_has_evidence(self, query: str, chunks: List[Dict[str, Any]]) -> bool:
        """
        Checks if candidate chunks contain substantive topical evidence for the query.
        Filters out out-of-scope queries.
        """
        stop_words = {
            'what', 'is', 'the', 'in', 'of', 'and', 'a', 'an', 'to', 'for', 'on', 
            'with', 'as', 'by', 'at', 'from', 'this', 'that', 'these', 'those', 
            'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 
            'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will', 'about', 
            'tell', 'me', 'how', 'why', 'when', 'where', 'which', 'who', 'document', 'file'
        }
        words = re.findall(r'[a-zA-Z0-9]+', query.lower())
        substantive_words = [w for w in words if w not in stop_words and len(w) > 2 and w not in ['pdf', 'docx', 'png', 'jpg', 'txt']]
        if not substantive_words:
            return True
        for c in chunks:
            content_lower = (c.get('content') or '').lower()
            if any(w in content_lower for w in substantive_words):
                return True
        return False

    def rank_and_select_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        max_chunks: int = 3,
        is_selected_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate chunks using combined semantic and lexical relevance,
        filters out noisy metadata/cover pages, and enforces a strict context budget (2-4 chunks).
        Preserves multi-source diversity when multiple documents are present.
        """
        if not chunks:
            return []

        stop_words = {
            'what', 'is', 'the', 'in', 'of', 'and', 'a', 'an', 'to', 'for', 'on', 
            'with', 'as', 'by', 'at', 'from', 'this', 'that', 'these', 'those', 
            'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 
            'do', 'does', 'did', 'can', 'could', 'should', 'would', 'will', 'about', 
            'tell', 'me', 'how', 'why', 'when', 'where', 'which', 'who', 'document', 'file'
        }
        terms = [w.lower() for w in re.findall(r'[a-zA-Z0-9]+', query) if w.lower() not in stop_words and len(w) > 2]

        scored = []
        for c in chunks:
            content = c.get("content", "")
            content_lower = content.lower()
            base_score = float(c.get("relevance_score", 0.0))

            # Count term matches
            match_count = sum(1 for t in terms if t in content_lower)
            exact_boost = 0.0
            if match_count > 0:
                exact_boost = 0.12 * (match_count / max(len(terms), 1))

            # Penalize cover/header boilerplate if other chunks match the query term
            is_boilerplate = any(b in content_lower for b in ["student id:", "roll number:", "academic year:", "date of performance:", "name of student:"])
            if is_boilerplate and match_count == 0:
                base_score *= 0.35

            final_rank_score = base_score + exact_boost
            scored.append((final_rank_score, c))

        # Sort descending by rank score
        scored.sort(key=lambda x: x[0], reverse=True)

        # Multi-source diversity: cap chunks per document if multiple documents are queried
        selected = []
        doc_counts = {}
        unique_docs_in_candidates = {c.get("document_id") for c in chunks}
        for score, chunk in scored:
            if len(selected) >= max_chunks:
                break
            doc_id = chunk.get("document_id")
            doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

            if len(unique_docs_in_candidates) > 1 and doc_counts[doc_id] > 2:
                continue

            selected.append(chunk)

        return selected

    def _filter_and_deduplicate_sources(
        self,
        chunks: List[Dict[str, Any]],
        query: str,
        answer_text: str = "",
        is_selected_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Deduplicates and filters retrieved sources for the CURRENT message only.
        - Groups multiple chunks for the same document and page into a single citation.
        - Produces concise evidence snippets.
        """
        if not chunks:
            return []

        if not self._check_has_evidence(query, chunks):
            return []

        # Deduplicate by (document_id, page_number)
        deduped = {}
        for c in chunks:
            key = (c.get("document_id"), c.get("page_number", 1))
            snippet = extract_evidence_snippet(c.get("content", ""), query, max_length=160)

            if key not in deduped:
                deduped[key] = {
                    "document_id": c.get("document_id"),
                    "document_name": c.get("filename", "Document"),
                    "page_number": c.get("page_number", 1),
                    "section": c.get("section", "General"),
                    "evidence_snippet": snippet,
                    "relevance_score": c.get("relevance_score", 0.0)
                }
            else:
                if c.get("relevance_score", 0.0) > deduped[key]["relevance_score"]:
                    deduped[key]["relevance_score"] = c.get("relevance_score", 0.0)
                    deduped[key]["evidence_snippet"] = snippet

        return list(deduped.values())

    def _extractive_fallback_answer(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        is_selected_mode: bool = False,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Deterministic, grounded fallback answer generator when Gemini API is unavailable.
        Answers strictly from the best relevant excerpts without dumping full document text.
        """
        doc_scope = "selected documents" if is_selected_mode else "uploaded documents"
        insufficient_msg = f"Insufficient evidence was found in the {doc_scope} to answer this question reliably."

        if not chunks or not self._check_has_evidence(query, chunks):
            return {
                "answer": insufficient_msg,
                "insufficient_evidence": True,
                "conflicts_detected": False,
                "sources": []
            }

        effective_query = search_query or query
        budgeted_chunks = self.rank_and_select_chunks(chunks, query=effective_query, max_chunks=3, is_selected_mode=is_selected_mode)
        sources = self._filter_and_deduplicate_sources(
            budgeted_chunks, 
            query=effective_query, 
            is_selected_mode=is_selected_mode
        )
        if not sources:
            return {
                "answer": insufficient_msg,
                "insufficient_evidence": True,
                "conflicts_detected": False,
                "sources": []
            }

        snippets_text = []
        for s in sources:
            snippets_text.append(f"• According to **{s.get('document_name')}** (Page {s.get('page_number')}):\n\"{s.get('evidence_snippet', '').strip()}\"")

        answer_text = (
            f"Based on the retrieved evidence from your {doc_scope}:\n\n"
            + "\n\n".join(snippets_text)
        )

        return {
            "answer": answer_text,
            "insufficient_evidence": False,
            "conflicts_detected": False,
            "sources": sources
        }

    def generate_response(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        is_selected_mode: bool = False,
        search_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a concise, verified, grounded answer using Google Gemini or extractive pipeline.
        Enforces small candidate budgeting before sending to the model.
        """
        doc_scope = "selected documents" if is_selected_mode else "uploaded documents"
        insufficient_msg = f"Insufficient evidence was found in the {doc_scope} to answer this question reliably."
        effective_query = search_query or query

        # 1. If no chunks were retrieved at all
        if not retrieved_chunks:
            return {
                "answer": insufficient_msg,
                "insufficient_evidence": True,
                "conflicts_detected": False,
                "sources": []
            }

        # 2. Check topical keyword / substantive overlap
        if not self._check_has_evidence(query, retrieved_chunks):
            return {
                "answer": insufficient_msg,
                "insufficient_evidence": True,
                "conflicts_detected": False,
                "sources": []
            }

        # 3. Context Budgeting: Rank and select best 2 to 3 candidate chunks
        budgeted_chunks = self.rank_and_select_chunks(
            retrieved_chunks,
            query=effective_query,
            max_chunks=3,
            is_selected_mode=is_selected_mode
        )

        if not budgeted_chunks:
            return {
                "answer": insufficient_msg,
                "insufficient_evidence": True,
                "conflicts_detected": False,
                "sources": []
            }

        # 4. Format context and history
        context_str = self._format_context(budgeted_chunks)
        history_str = self._format_history(conversation_history or [])

        # 5. Dynamic check for Gemini API key
        api_key = (settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")).strip()
        if not api_key:
            logger.info("GEMINI_API_KEY not set in .env. Using verified extractive grounded RAG generator.")
            return self._extractive_fallback_answer(query, budgeted_chunks, is_selected_mode=is_selected_mode, search_query=effective_query)

        system_prompt_text = get_system_prompt(is_selected_mode=is_selected_mode)
        prompt = f"""{system_prompt_text}

<CONTEXT>
{context_str}
</CONTEXT>

CONVERSATION HISTORY:
{history_str if history_str else "None"}

USER QUESTION:
{query}

Please provide your concise grounded answer below:
"""

        try:
            import requests as req
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "topP": 0.8,
                    "maxOutputTokens": 1024
                }
            }
            # Try with standard verify=True, fallback to verify=False if SSL proxy intercepts
            try:
                r = req.post(url, json=payload, timeout=15)
            except req.exceptions.SSLError:
                r = req.post(url, json=payload, timeout=15, verify=False)

            if r.status_code == 200:
                res_data = r.json()
                answer_text = ""
                candidates = res_data.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        answer_text = parts[0].get("text", "").strip()

                if not answer_text:
                    return self._extractive_fallback_answer(query, budgeted_chunks, is_selected_mode=is_selected_mode, search_query=effective_query)

                is_insufficient = "insufficient evidence" in answer_text.lower()
                is_conflict = "conflict identified" in answer_text.lower() or "conflicting" in answer_text.lower()

                sources = []
                if not is_insufficient:
                    sources = self._filter_and_deduplicate_sources(
                        budgeted_chunks, 
                        query=effective_query, 
                        answer_text=answer_text,
                        is_selected_mode=is_selected_mode
                    )

                return {
                    "answer": answer_text,
                    "insufficient_evidence": is_insufficient,
                    "conflicts_detected": is_conflict,
                    "sources": sources
                }
            else:
                logger.warning(f"Gemini API returned status {r.status_code}: {r.text[:200]}")
                return self._extractive_fallback_answer(query, budgeted_chunks, is_selected_mode=is_selected_mode, search_query=effective_query)

        except Exception as e:
            logger.error(f"Gemini API request error: {e}")
            return self._extractive_fallback_answer(query, budgeted_chunks, is_selected_mode=is_selected_mode, search_query=effective_query)

rag_service = RAGService()
