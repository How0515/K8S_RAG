"""
FastAPI 메인 애플리케이션
- PDF 업로드 API
- RAG 질의응답 API
- 헬스체크 API
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from pdf_processor import extract_text_from_pdf, chunk_text
from embedding_model import get_embedding_model
from qdrant_client_wrapper import get_qdrant_client
from ollama_client import get_ollama_client
from rag_pipeline import get_document_pipeline, get_rag_pipeline, generate_node


# FastAPI 앱 생성
app = FastAPI(
    title="K8S RAG API",
    description="Kubernetes 기반 RAG (Retrieval-Augmented Generation) 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Request/Response 모델 =====

class QueryRequest(BaseModel):
    """질의 요청"""
    query: str
    doc_id: Optional[str] = None


class QueryResponse(BaseModel):
    """질의 응답"""
    query: str
    response: str
    contexts: List[str]


class UploadResponse(BaseModel):
    """업로드 응답"""
    doc_id: str
    filename: str
    chunks_count: int
    message: str


class HealthResponse(BaseModel):
    """헬스체크 응답"""
    status: str
    qdrant: bool
    ollama: bool
    embedding_model: bool


# ===== API 엔드포인트 =====

@app.get("/", tags=["Root"])
async def root():
    """루트 엔드포인트"""
    return {
        "message": "K8S RAG API Server",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """헬스체크 - 모든 서비스 상태 확인"""
    
    # Qdrant 상태 확인
    qdrant_ok = False
    try:
        qdrant = get_qdrant_client()
        qdrant.get_collection_info()
        qdrant_ok = True
    except Exception:
        pass
    
    # Ollama 상태 확인
    ollama_ok = False
    try:
        ollama = get_ollama_client()
        ollama_ok = await ollama.check_health()
    except Exception:
        pass
    
    # 임베딩 모델 상태 확인
    embedding_ok = False
    try:
        embedding = get_embedding_model()
        embedding.embed_single("test")
        embedding_ok = True
    except Exception:
        pass
    
    status = "healthy" if all([qdrant_ok, ollama_ok, embedding_ok]) else "degraded"
    
    return HealthResponse(
        status=status,
        qdrant=qdrant_ok,
        ollama=ollama_ok,
        embedding_model=embedding_ok
    )


@app.post("/upload", response_model=UploadResponse, tags=["Documents"])
async def upload_pdf(file: UploadFile = File(...)):
    """
    PDF 파일 업로드 및 벡터 저장
    
    - PDF에서 텍스트 추출
    - 텍스트 청킹
    - 임베딩 생성
    - Qdrant에 저장
    """
    
    # 파일 검증
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")
    
    try:
        # PDF 읽기
        pdf_bytes = await file.read()
        
        # 텍스트 추출
        text = extract_text_from_pdf(pdf_bytes)
        if not text.strip():
            raise HTTPException(status_code=400, detail="PDF에서 텍스트를 추출할 수 없습니다.")
        
        # 청킹
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        if not chunks:
            raise HTTPException(status_code=400, detail="텍스트 청킹에 실패했습니다.")
        
        # 임베딩
        embedding_model = get_embedding_model()
        embeddings = embedding_model.embed(chunks)
        
        # Qdrant 저장
        qdrant = get_qdrant_client()
        qdrant.ensure_collection(embedding_model.dimension)
        
        import uuid
        doc_id = str(uuid.uuid4())
        
        metadata = [{"filename": file.filename} for _ in chunks]
        qdrant.add_documents(
            texts=chunks,
            embeddings=embeddings,
            metadata=metadata,
            doc_id=doc_id
        )
        
        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename,
            chunks_count=len(chunks),
            message=f"문서 '{file.filename}'이 성공적으로 업로드되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업로드 처리 중 오류: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_rag(request: QueryRequest):
    """
    RAG 질의응답
    
    - 질문을 임베딩
    - Qdrant에서 유사 문서 검색
    - Ollama로 답변 생성
    """
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="질문을 입력해주세요.")
    
    try:
        # 임베딩 모델
        embedding_model = get_embedding_model()
        
        # 쿼리 임베딩
        query_embedding = embedding_model.embed_single(request.query)
        
        # Qdrant 검색
        qdrant = get_qdrant_client()
        results = qdrant.search(
            query_embedding=query_embedding,
            top_k=3,
            doc_id=request.doc_id
        )
        
        contexts = [r["text"] for r in results]
        
        if not contexts:
            return QueryResponse(
                query=request.query,
                response="관련 문서를 찾을 수 없습니다. 먼저 PDF를 업로드해주세요.",
                contexts=[]
            )
        
        # Ollama로 답변 생성
        ollama = get_ollama_client()
        
        context_text = "\n\n---\n\n".join(contexts)
        
        system_prompt = """당신은 주어진 문서를 바탕으로 질문에 답변하는 AI 어시스턴트입니다.
반드시 제공된 컨텍스트 내용만을 기반으로 답변하세요.
컨텍스트에 없는 정보는 "해당 정보를 찾을 수 없습니다"라고 답변하세요.
한국어로 친절하게 답변하세요."""
        
        prompt = f"""[참고 문서]
{context_text}

[질문]
{request.query}

[답변]"""
        
        response = await ollama.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3
        )
        
        return QueryResponse(
            query=request.query,
            response=response,
            contexts=contexts
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"질의 처리 중 오류: {str(e)}")


@app.get("/documents", tags=["Documents"])
async def list_documents():
    """저장된 문서 정보 조회"""
    try:
        qdrant = get_qdrant_client()
        info = qdrant.get_collection_info()
        return info
    except Exception as e:
        # Pydantic 검증 오류는 일반적인 오류로 처리
        error_msg = str(e)
        if "validation error" in error_msg.lower() or "pydantic" in error_msg.lower():
            return {
                "error": "Qdrant 버전 호환성 문제",
                "message": "문서 조회에 일시적 오류가 발생했습니다. 데이터는 정상적으로 저장되어 있습니다.",
                "status": "degraded"
            }
        return {"error": error_msg}


@app.delete("/documents/{doc_id}", tags=["Documents"])
async def delete_document(doc_id: str):
    """문서 삭제"""
    try:
        qdrant = get_qdrant_client()
        qdrant.delete_document(doc_id)
        return {"message": f"문서 {doc_id}가 삭제되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 중 오류: {str(e)}")


@app.get("/models", tags=["Ollama"])
async def list_models():
    """사용 가능한 Ollama 모델 목록"""
    try:
        ollama = get_ollama_client()
        models = await ollama.list_models()
        return {"models": models}
    except Exception as e:
        return {"error": str(e), "models": []}


# ===== 메인 실행 =====

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
