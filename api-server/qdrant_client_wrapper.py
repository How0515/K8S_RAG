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
        """컬렉션 정보 반환"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count
            }
        except Exception as e:
            # Pydantic 검증 오류 무시 - Qdrant와 qdrant-client 버전 호환성 문제
            if "validation error" in str(e).lower() or "pydantic" in str(e).lower():
                try:
                    # 기본 정보만 반환
                    return {
                        "name": self.collection_name,
                        "vectors_count": 0,
                        "points_count": 0,
                        "note": "Qdrant 버전 호환성 경고 - 기본값 반환"
                    }
                except:
                    return {"error": "컬렉션 정보를 조회할 수 없습니다."}
            return {"error": str(e)}


# 싱글톤 인스턴스
_qdrant_client = None


def get_qdrant_client() -> QdrantWrapper:
    """Qdrant 클라이언트 싱글톤 인스턴스 반환"""
    global _qdrant_client
    if _qdrant_client is None:
        _qdrant_client = QdrantWrapper()
    return _qdrant_client
