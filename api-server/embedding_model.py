"""
로컬 임베딩 모델 모듈
- sentence-transformers 기반 다국어 임베딩
- 경량 모델 사용 (약 420MB)
"""

from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np


class LocalEmbedding:
    """로컬 임베딩 모델 래퍼"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        """
        임베딩 모델 초기화
        
        Args:
            model_name: 사용할 모델명 (기본: 다국어 MiniLM)
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        텍스트 리스트를 임베딩 벡터로 변환
        
        Args:
            texts: 임베딩할 텍스트 리스트
        
        Returns:
            임베딩 벡터 리스트
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_single(self, text: str) -> List[float]:
        """
        단일 텍스트를 임베딩 벡터로 변환
        
        Args:
            text: 임베딩할 텍스트
        
        Returns:
            임베딩 벡터
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# 싱글톤 인스턴스
_embedding_model = None


def get_embedding_model() -> LocalEmbedding:
    """임베딩 모델 싱글톤 인스턴스 반환"""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = LocalEmbedding()
    return _embedding_model
