import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.hybrid_retriever import HybridRetriever

logger = logging.getLogger("smartdocs.rag_chain")

SYSTEM_RAG_PROMPT = """You are SmartDocs AI, an expert enterprise document intelligence assistant.
Your task is to answer the user's questions truthfully and accurately, strictly grounded in the retrieved document context provided below.

Guidelines:
1. ONLY use information directly stated or clearly implied by the context.
2. If the context does not contain sufficient information to answer the question, state: "Based on the provided documents, I could not find information regarding [topic]." Do not guess or hallucinate.
3. Cite your sources inline using the format: [Doc: <filename>, Page: <page_number>].
4. Format your response cleanly using GitHub-flavored Markdown (bullet points, bold headers, tables where appropriate).
5. Maintain a professional, clear, and objective tone.

RETRIEVED DOCUMENT CONTEXT:
---------------------
{context}
---------------------
"""

REFORMULATION_PROMPT = """Given the chat history and the latest user question, rephrase the question into a standalone search query that contains all necessary entities and context for retrieval. Do NOT answer the question, only output the rephrased search query.

Chat History:
{chat_history}

Latest Question: {question}
Standalone Search Query:"""

class RAGChainService:
    """
    End-to-End Context-Aware RAG Pipeline:
    - Multi-turn query rewriting / coreference resolution
    - Hybrid / MMR retrieval
    - Context formatting with strict provenance
    - Streaming & non-streaming response generation
    - Citation extraction
    """

    def __init__(self, db: Session):
        self.db = db
        self.retriever = HybridRetriever(db)
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.llm_model = settings.LLM_MODEL
        self._gemini_client = None
        self._openai_client = None

        # 1. Try Google GenAI client first (Google AI Studio)
        if self.gemini_api_key and not self.gemini_api_key.startswith("your_") and not self.gemini_api_key.startswith("mock"):
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info(f"Initialized Google GenAI RAG Chain with model {self.llm_model}")
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI client for RAG chain: {e}")

        # 2. Try OpenAI client fallback
        if not self._gemini_client and self.openai_api_key and not self.openai_api_key.startswith("your_") and not self.openai_api_key.startswith("mock"):
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_api_key)
                logger.info(f"Initialized OpenAI RAG Chain with model {self.llm_model}")
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client for RAG chain: {e}")

    def reformulate_query(self, question: str, history: List[Dict[str, str]]) -> str:
        """
        Reformulates conversational follow-up questions (e.g. 'What about its pricing?')
        into a standalone keyword/dense query using chat history.
        """
        if not history or len(history) <= 1:
            return question

        # If neither client is configured, perform simple heuristic entity linking
        if not self._gemini_client and not self._openai_client:
            last_user_msg = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
            if last_user_msg and any(pronoun in question.lower() for pronoun in ["it", "its", "they", "this", "that"]):
                return f"{last_user_msg} {question}"
            return question

        formatted_history = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-4:]])
        prompt = REFORMULATION_PROMPT.format(chat_history=formatted_history, question=question)

        # Google GenAI reformulation
        if self._gemini_client:
            try:
                from google.genai import types
                resp = self._gemini_client.models.generate_content(
                    model=self.llm_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        max_output_tokens=100
                    )
                )
                reformulated = resp.text.strip() if resp.text else question
                return reformulated if reformulated else question
            except Exception as e:
                logger.warning(f"Google GenAI query reformulation failed: {e}. Using original question.")
                return question

        # OpenAI reformulation fallback
        if self._openai_client:
            try:
                resp = self._openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                    max_tokens=100
                )
                reformulated = resp.choices[0].message.content.strip()
                return reformulated if reformulated else question
            except Exception as e:
                logger.warning(f"OpenAI query reformulation failed: {e}. Using original question.")
                return question

        return question

    def format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Formats retrieved chunks with provenance headers for LLM prompt."""
        if not chunks:
            return "No relevant documents found."

        formatted_blocks = []
        for i, chunk in enumerate(chunks):
            doc_name = chunk.get("document_filename", "Unknown Document")
            page = chunk.get("page_number", 1)
            score = chunk.get("similarity", chunk.get("rrf_score", "N/A"))
            block = (
                f"[Source {i+1}: {doc_name} | Page {page} | Score: {score}]\n"
                f"{chunk.get('content', '')}\n"
            )
            formatted_blocks.append(block)

        return "\n\n".join(formatted_blocks)

    def _fallback_generate(self, question: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Offline fallback response generator when OpenAI API key is unavailable.
        Extracts key relevant sentences from top chunks and constructs a coherent cited summary.
        """
        if not chunks:
            return (
                "Based on the currently indexed documents, no relevant context was found for your query. "
                "Please upload documents or refine your search keywords."
            )

        citations = []
        extracted_points = []
        q_words = set(question.lower().split())

        for c in chunks[:3]:
            doc_name = c.get("document_filename", "Document")
            page = c.get("page_number", 1)
            content = c.get("content", "")
            
            # Find best matching sentence
            sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 15]
            best_sentence = ""
            best_overlap = 0

            for sent in sentences:
                overlap = len(set(sent.lower().split()) & q_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_sentence = sent

            if not best_sentence and sentences:
                best_sentence = sentences[0]

            if best_sentence:
                extracted_points.append(f"- {best_sentence}. [Doc: {doc_name}, Page: {page}]")
                citations.append(f"[Doc: {doc_name}, Page: {page}]")

        summary_body = "\n".join(extracted_points) if extracted_points else "- Information found in retrieved sections."
        return (
            f"### Document Findings\n\n"
            f"Here are the relevant insights retrieved from your indexed documents regarding **\"{question}\"**:\n\n"
            f"{summary_body}\n\n"
            f"> *Note: Google AI Studio / Gemini API key is not currently configured. Showing deterministic extractive context from the top retrieved chunks.*"
        )

    def generate_response(
        self,
        question: str,
        history: List[Dict[str, str]] = None,
        retrieval_strategy: str = None,
        top_k: int = None,
        similarity_threshold: float = None,
        mmr_lambda: float = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synchronous / Standard non-streaming RAG response generation.
        """
        history = history or []
        
        # 1. Query reformulation
        search_query = self.reformulate_query(question, history)

        # 2. Retrieval with tuning parameters
        retrieval_res = self.retriever.retrieve(
            query=search_query,
            strategy=retrieval_strategy,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            mmr_lambda=mmr_lambda,
            document_id=document_id
        )

        retrieved_chunks = retrieval_res["chunks"]
        retrieval_meta = retrieval_res["metadata"]
        retrieval_meta["search_query"] = search_query

        # 3. Format Context
        context_str = self.format_context(retrieved_chunks)

        # 4. Generate Answer via LLM
        answer = ""
        # Option A: Google GenAI (Google AI Studio)
        if self._gemini_client and retrieved_chunks:
            try:
                from google.genai import types
                history_prompt = []
                for h in history[-4:]:
                    role = "User" if h.get("role") == "user" else "Assistant"
                    history_prompt.append(f"{role}: {h.get('content', '')}")

                user_content = (
                    f"Conversation History:\n{chr(10).join(history_prompt)}\n\nCurrent Question: {question}"
                    if history_prompt else question
                )

                resp = self._gemini_client.models.generate_content(
                    model=self.llm_model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_RAG_PROMPT.format(context=context_str),
                        temperature=0.1,
                        max_output_tokens=1500
                    )
                )
                answer = resp.text or ""
            except Exception as e:
                logger.error(f"Google GenAI completion error: {e}. Falling back to extractive answer.")
                answer = self._fallback_generate(question, retrieved_chunks)

        # Option B: OpenAI fallback
        elif self._openai_client and retrieved_chunks:
            try:
                system_msg = SYSTEM_RAG_PROMPT.format(context=context_str)
                messages = [{"role": "system", "content": system_msg}]

                for h in history[-4:]:
                    messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})

                messages.append({"role": "user", "content": question})

                resp = self._openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000
                )
                answer = resp.choices[0].message.content
            except Exception as e:
                logger.error(f"OpenAI completion error: {e}. Falling back to extractive answer.")
                answer = self._fallback_generate(question, retrieved_chunks)

        # Option C: Offline extractive fallback
        else:
            answer = self._fallback_generate(question, retrieved_chunks)

        return {
            "answer": answer,
            "sources": retrieved_chunks,
            "retrieval_metadata": retrieval_meta
        }

    async def generate_response_stream(
        self,
        question: str,
        history: List[Dict[str, str]] = None,
        retrieval_strategy: str = None,
        top_k: int = None,
        similarity_threshold: float = None,
        mmr_lambda: float = None,
        document_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streaming response generator via Server-Sent Events (SSE).
        Yields chunk tokens in real-time, then finishes with sources and metadata event.
        """
        history = history or []
        search_query = self.reformulate_query(question, history)

        retrieval_res = self.retriever.retrieve(
            query=search_query,
            strategy=retrieval_strategy,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            mmr_lambda=mmr_lambda,
            document_id=document_id
        )

        retrieved_chunks = retrieval_res["chunks"]
        retrieval_meta = retrieval_res["metadata"]
        retrieval_meta["search_query"] = search_query

        # Send initial metadata event
        yield f"event: metadata\ndata: {json.dumps({'retrieval_metadata': retrieval_meta, 'sources': retrieved_chunks})}\n\n"

        context_str = self.format_context(retrieved_chunks)

        # Option A: Google GenAI streaming (Google AI Studio)
        if self._gemini_client and retrieved_chunks:
            try:
                from google.genai import types
                history_prompt = []
                for h in history[-4:]:
                    role = "User" if h.get("role") == "user" else "Assistant"
                    history_prompt.append(f"{role}: {h.get('content', '')}")

                user_content = (
                    f"Conversation History:\n{chr(10).join(history_prompt)}\n\nCurrent Question: {question}"
                    if history_prompt else question
                )

                stream = self._gemini_client.models.generate_content_stream(
                    model=self.llm_model,
                    contents=user_content,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_RAG_PROMPT.format(context=context_str),
                        temperature=0.1,
                        max_output_tokens=1500
                    )
                )

                for chunk in stream:
                    delta = chunk.text or ""
                    if delta:
                        yield f"event: delta\ndata: {json.dumps({'content': delta})}\n\n"

            except Exception as e:
                logger.error(f"Google GenAI streaming error: {e}")
                fallback = self._fallback_generate(question, retrieved_chunks)
                yield f"event: delta\ndata: {json.dumps({'content': fallback})}\n\n"

        # Option B: OpenAI streaming fallback
        elif self._openai_client and retrieved_chunks:
            try:
                system_msg = SYSTEM_RAG_PROMPT.format(context=context_str)
                messages = [{"role": "system", "content": system_msg}]
                for h in history[-4:]:
                    messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
                messages.append({"role": "user", "content": question})

                stream = self._openai_client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=1000,
                    stream=True
                )

                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if delta:
                        yield f"event: delta\ndata: {json.dumps({'content': delta})}\n\n"

            except Exception as e:
                logger.error(f"OpenAI streaming error: {e}")
                fallback = self._fallback_generate(question, retrieved_chunks)
                yield f"event: delta\ndata: {json.dumps({'content': fallback})}\n\n"

        # Option C: Offline extractive fallback
        else:
            fallback = self._fallback_generate(question, retrieved_chunks)
            words = fallback.split(" ")
            for w in words:
                yield f"event: delta\ndata: {json.dumps({'content': w + ' '})}\n\n"

        yield "event: done\ndata: {}\n\n"
