"""
Ollama LLM 클라이언트
- Ollama API를 통한 LLM 추론
"""

import httpx
import os
from typing import Optional, List, Dict, Any
import json


class OllamaClient:
    """Ollama API 클라이언트"""
    
    def __init__(
        self,
        host: str = None,
        port: int = 11434,
        model: str = "gemma2:2b"
    ):
        """
        Ollama 클라이언트 초기화
        
        Args:
            host: Ollama 서버 호스트
            port: Ollama 서버 포트
            model: 사용할 모델명 (기본: gemma2:2b - 한국어 지원 우수)
        """
        self.host = host or os.getenv("OLLAMA_HOST", "ollama-service")
        self.port = port
        self.model = model
        self.base_url = f"http://{self.host}:{self.port}"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트 (선택)
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
        
        Returns:
            생성된 텍스트
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> str:
        """
        채팅 형식 생성
        
        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}]
            temperature: 생성 온도
            max_tokens: 최대 토큰 수
        
        Returns:
            생성된 응답
        """
        url = f"{self.base_url}/api/chat"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
    
    async def check_health(self) -> bool:
        """Ollama 서버 상태 확인"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
    
    async def list_models(self) -> List[str]:
        """사용 가능한 모델 목록"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            return []
    
    async def pull_model(self, model_name: str = None) -> bool:
        """
        모델 다운로드
        
        Args:
            model_name: 다운로드할 모델명 (기본: 설정된 모델)
        
        Returns:
            성공 여부
        """
        model = model_name or self.model
        url = f"{self.base_url}/api/pull"
        
        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                response = await client.post(
                    url,
                    json={"name": model, "stream": False}
                )
                return response.status_code == 200
        except Exception as e:
            print(f"모델 다운로드 실패: {e}")
            return False


# 싱글톤 인스턴스
_ollama_client = None


def get_ollama_client() -> OllamaClient:
    """Ollama 클라이언트 싱글톤 인스턴스 반환"""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client
