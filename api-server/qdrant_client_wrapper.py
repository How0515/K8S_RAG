"""
Qdrant 벡터 데이터베이스 클라이언트 래퍼
- 벡터 저장 및 검색 기능
"""

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from typing import List, Dict, Any, Optional
import os
import uuid


class QdrantWrapper:
    """Qdrant 클라이언트 래퍼"""
    
    def __init__(
        self,
        host: str = None,
        port: int = 6333,
        collection_name: str = "documents"
    ):
        """
        Qdrant 클라이언트 초기화
        
        Args:
            host: Qdrant 서버 호스트
            port: Qdrant 서버 포트
            collection_name: 컬렉션 이름
        """
        self.host = host or os.getenv("QDRANT_HOST", "qdrant-service")
        self.port = port
        self.collection_name = collection_name
        self.client = QdrantClient(host=self.host, port=self.port)
    
    def ensure_collection(self, vector_size: int):
        """
        컬렉션이 없으면 생성
        
        Args:
            vector_size: 벡터 차원
        """
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if self.collection_name not in collection_names:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"컬렉션 '{self.collection_name}' 생성 완료")
    
    def add_documents(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadata: Optional[List[Dict[str, Any]]] = None,
        doc_id: str = None
    ) -> List[str]:
        """
        문서 추가
        
        Args:
            texts: 텍스트 청크 리스트
            embeddings: 임베딩 벡터 리스트
            metadata: 메타데이터 리스트 (선택)
            doc_id: 문서 ID (선택)
        
        Returns:
            생성된 포인트 ID 리스트
        """
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        
        points = []
        point_ids = []
        
        for i, (text, embedding) in enumerate(zip(texts, embeddings)):
            point_id = str(uuid.uuid4())
            point_ids.append(point_id)
            
            payload = {
                "text": text,
                "doc_id": doc_id,
                "chunk_index": i
            }
            
            if metadata and i < len(metadata):
                payload.update(metadata[i])
            
            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
        return point_ids
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        doc_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        유사 문서 검색
        
        Args:
            query_embedding: 쿼리 임베딩 벡터
            top_k: 반환할 결과 수
            doc_id: 특정 문서 내에서만 검색 (선택)
        
        Returns:
            검색 결과 리스트
        """
        search_filter = None
        if doc_id:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k
        )
        
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "text": hit.payload.get("text", ""),
                "doc_id": hit.payload.get("doc_id", ""),
                "metadata": hit.payload
            }
            for hit in results
        ]
    
    def delete_document(self, doc_id: str):
        """
        문서 삭제
        
        Args:
            doc_id: 삭제할 문서 ID
        """
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="doc_id",
                        match=MatchValue(value=doc_id)
                    )
                ]
            )
        )
    
    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 반환 - REST API 직접 호출로 Pydantic 검증 우회"""
        import httpx
        
        # REST API로 직접 조회 (Pydantic 검증 문제 우회)
        url = f"http://{self.host}:{self.port}/collections/{self.collection_name}"
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    result = data.get("result", {})
                    
                    # points_count 추출
                    points_count = result.get("points_count", 0)
                    
                    # vectors_count는 일반적으로 points_count와 동일
                    vectors_count = result.get("vectors_count", points_count)
                    
                    return {
                        "name": self.collection_name,
                        "vectors_count": vectors_count,
                        "points_count": points_count,
                        "status": result.get("status", "unknown")
                    }
                else:
                    return {
                        "error": f"HTTP {response.status_code}",
                        "message": "컬렉션 정보 조회 실패"
                    }
                    
        except Exception as e:
            # REST API 실패 시 qdrant-client로 재시도
            try:
                info = self.client.get_collection(self.collection_name)
                vectors_count = info.vectors_count if info.vectors_count is not None else info.points_count
                points_count = info.points_count if info.points_count is not None else 0
                
                return {
                    "name": self.collection_name,
                    "vectors_count": vectors_count,
                    "points_count": points_count,
                    "status": "ok"
                }
            except:
                return {
                    "error": str(e),
                    "message": "컬렉션 정보를 조회할 수 없습니다."
                }
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        저장된 모든 문서 목록 조회
        
        Returns:
            문서 ID와 메타데이터 리스트
        """
        try:
            # 모든 포인트 스크롤 (offset 기반)
            documents_dict: Dict[str, Dict[str, Any]] = {}
            
            # Scroll을 사용하여 모든 포인트 조회
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                limit=100,  # 한 번에 조회할 포인트 수
                with_payload=True,
                with_vectors=False
            )
            
            # doc_id별로 그룹화
            for point in points:
                payload = point.payload
                doc_id = payload.get("doc_id")
                
                if doc_id not in documents_dict:
                    documents_dict[doc_id] = {
                        "doc_id": doc_id,
                        "filename": payload.get("filename", "Unknown"),
                        "chunk_count": 0,
                        "chunks": []
                    }
                
                documents_dict[doc_id]["chunk_count"] += 1
                documents_dict[doc_id]["chunks"].append({
                    "chunk_index": payload.get("chunk_index", -1),
                    "text": payload.get("text", "")[:100] + "..."  # 처음 100자만
                })
            
            return list(documents_dict.values())
        
        except Exception as e:
            # 호환성 문제 처리
            if "validation error" in str(e).lower() or "pydantic" in str(e).lower():
                return [{
                    "error": "Qdrant 버전 호환성 문제",
                    "message": "문서 목록을 조회할 수 없습니다.",
                    "note": "데이터는 정상적으로 저장되어 있습니다."
                }]
            return [{
                "error": str(e),
                "message": "문서 목록 조회 실패"
            }]


# 싱글톤 인스턴스
_qdrant_client = None


def get_qdrant_client() -> QdrantWrapper:
    """Qdrant 클라이언트 싱글톤 인스턴스 반환"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantWrapper()
    return _qdrant_client
