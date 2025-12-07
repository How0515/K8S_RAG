"""
LangGraph 기반 RAG 파이프라인
- PDF 처리 → 임베딩 → 저장
- 질문 → 검색 → 생성 → 답변
"""

from typing import TypedDict, List, Optional, Annotated
from langgraph.graph import StateGraph, END
import operator

from embedding_model import get_embedding_model
from qdrant_client_wrapper import get_qdrant_client
from ollama_client import get_ollama_client
from pdf_processor import extract_text_from_pdf, chunk_text


# RAG 상태 정의
class RAGState(TypedDict):
    """RAG 파이프라인 상태"""
    query: str                          # 사용자 질문
    doc_id: Optional[str]               # 문서 ID (특정 문서 검색 시)
    retrieved_contexts: List[str]       # 검색된 컨텍스트
    response: str                       # 최종 응답
    error: Optional[str]                # 에러 메시지


class DocumentState(TypedDict):
    """문서 처리 상태"""
    pdf_bytes: bytes                    # PDF 바이트
    filename: str                       # 파일명
    text: str                           # 추출된 텍스트
    chunks: List[str]                   # 청크 리스트
    embeddings: List[List[float]]       # 임베딩 리스트
    doc_id: str                         # 문서 ID
    error: Optional[str]                # 에러 메시지


# ===== 문서 처리 노드 =====

def extract_text_node(state: DocumentState) -> DocumentState:
    """PDF에서 텍스트 추출"""
    try:
        text = extract_text_from_pdf(state["pdf_bytes"])
        state["text"] = text
        print(f"텍스트 추출 완료: {len(text)} 문자")
    except Exception as e:
        state["error"] = f"텍스트 추출 실패: {str(e)}"
    return state


def chunk_text_node(state: DocumentState) -> DocumentState:
    """텍스트 청킹"""
    if state.get("error"):
        return state
    
    try:
        chunks = chunk_text(state["text"], chunk_size=500, overlap=50)
        state["chunks"] = chunks
        print(f"청킹 완료: {len(chunks)} 청크")
    except Exception as e:
        state["error"] = f"청킹 실패: {str(e)}"
    return state


def embed_chunks_node(state: DocumentState) -> DocumentState:
    """청크 임베딩"""
    if state.get("error"):
        return state
    
    try:
        embedding_model = get_embedding_model()
        embeddings = embedding_model.embed(state["chunks"])
        state["embeddings"] = embeddings
        print(f"임베딩 완료: {len(embeddings)} 벡터")
    except Exception as e:
        state["error"] = f"임베딩 실패: {str(e)}"
    return state


def store_vectors_node(state: DocumentState) -> DocumentState:
    """벡터 저장"""
    if state.get("error"):
        return state
    
    try:
        qdrant = get_qdrant_client()
        embedding_model = get_embedding_model()
        
        # 컬렉션 확인/생성
        qdrant.ensure_collection(embedding_model.dimension)
        
        # 문서 저장
        import uuid
        doc_id = str(uuid.uuid4())
        
        metadata = [{"filename": state["filename"]} for _ in state["chunks"]]
        
        qdrant.add_documents(
            texts=state["chunks"],
            embeddings=state["embeddings"],
            metadata=metadata,
            doc_id=doc_id
        )
        
        state["doc_id"] = doc_id
        print(f"저장 완료: doc_id={doc_id}")
    except Exception as e:
        state["error"] = f"저장 실패: {str(e)}"
    return state


# ===== RAG 질의응답 노드 =====

def retrieve_node(state: RAGState) -> RAGState:
    """관련 문서 검색"""
    try:
        embedding_model = get_embedding_model()
        qdrant = get_qdrant_client()
        
        # 쿼리 임베딩
        query_embedding = embedding_model.embed_single(state["query"])
        
        # 검색
        results = qdrant.search(
            query_embedding=query_embedding,
            top_k=3,
            doc_id=state.get("doc_id")
        )
        
        contexts = [r["text"] for r in results]
        state["retrieved_contexts"] = contexts
        print(f"검색 완료: {len(contexts)} 문서")
    except Exception as e:
        state["error"] = f"검색 실패: {str(e)}"
        state["retrieved_contexts"] = []
    return state


async def generate_node(state: RAGState) -> RAGState:
    """답변 생성"""
    if state.get("error"):
        state["response"] = "검색 중 오류가 발생했습니다."
        return state
    
    try:
        ollama = get_ollama_client()
        
        # 컨텍스트 조합
        context = "\n\n---\n\n".join(state["retrieved_contexts"])
        
        # 프롬프트 생성
        system_prompt = """당신은 주어진 문서를 바탕으로 질문에 답변하는 AI 어시스턴트입니다.
반드시 제공된 컨텍스트 내용만을 기반으로 답변하세요.
컨텍스트에 없는 정보는 "해당 정보를 찾을 수 없습니다"라고 답변하세요.
한국어로 답변하세요."""
        
        prompt = f"""[컨텍스트]
{context}

[질문]
{state["query"]}

[답변]"""
        
        # 생성
        response = await ollama.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        state["response"] = response
        print("답변 생성 완료")
    except Exception as e:
        state["error"] = str(e)
        state["response"] = f"답변 생성 중 오류가 발생했습니다: {str(e)}"
    return state


# ===== 그래프 빌더 =====

def build_document_pipeline():
    """문서 처리 파이프라인 생성"""
    workflow = StateGraph(DocumentState)
    
    # 노드 추가
    workflow.add_node("extract", extract_text_node)
    workflow.add_node("chunk", chunk_text_node)
    workflow.add_node("embed", embed_chunks_node)
    workflow.add_node("store", store_vectors_node)
    
    # 엣지 연결
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "chunk")
    workflow.add_edge("chunk", "embed")
    workflow.add_edge("embed", "store")
    workflow.add_edge("store", END)
    
    return workflow.compile()


def build_rag_pipeline():
    """RAG 질의응답 파이프라인 생성 (동기 버전)"""
    workflow = StateGraph(RAGState)
    
    # 노드 추가
    workflow.add_node("retrieve", retrieve_node)
    
    # 엣지 연결
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", END)
    
    return workflow.compile()


# 파이프라인 인스턴스
_document_pipeline = None
_rag_pipeline = None


def get_document_pipeline():
    """문서 처리 파이프라인 반환"""
    global _document_pipeline
    if _document_pipeline is None:
        _document_pipeline = build_document_pipeline()
    return _document_pipeline


def get_rag_pipeline():
    """RAG 파이프라인 반환"""
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = build_rag_pipeline()
    return _rag_pipeline
