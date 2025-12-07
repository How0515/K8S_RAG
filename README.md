# K8S RAG System

Kubernetes 기반 RAG (Retrieval-Augmented Generation) 시스템

## 📋 프로젝트 개요

PDF 문서를 업로드하면 벡터 데이터베이스에 저장하고, 해당 문서를 바탕으로 질문에 답변하는 AI 챗봇 시스템입니다.

### 시스템 구성

| Pod | 이미지 | 역할 |
|-----|--------|------|
| RAG API Server | 커스텀 빌드 | FastAPI + LangGraph 기반 RAG 파이프라인 |
| Qdrant | qdrant/qdrant | 벡터 데이터베이스 |
| Ollama | ollama/ollama | LLM 추론 서버 |

### 아키텍처

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   RAG API        │────▶│   Qdrant         │     │   Ollama         │
│   (FastAPI)      │     │   (Vector DB)    │     │   (LLM)          │
│   Port: 8000     │     │   Port: 6333     │     │   Port: 11434    │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                                                   ▲
        │                                                   │
        └───────────────────────────────────────────────────┘
                        (질문 → 답변 생성)
```

## 🚀 빠른 시작

### 1. 사전 요구사항

- Docker Desktop (Kubernetes 활성화)
- kubectl 설치
- Docker Hub 계정

### 2. Docker 이미지 빌드 및 푸시

```powershell
# Docker Hub 로그인
docker login

# API Server 이미지 빌드
cd api-server
docker build -t <your-dockerhub-username>/rag-api-server:latest .

# Docker Hub에 푸시
docker push <your-dockerhub-username>/rag-api-server:latest
```

### 3. K8s YAML 파일 수정

`k8s/api-server-deployment.yaml` 파일에서 이미지 경로 수정:

```yaml
image: <your-dockerhub-username>/rag-api-server:latest
```

### 4. Kubernetes 배포

```powershell
# 네임스페이스 생성
kubectl apply -f k8s/namespace.yaml

# ConfigMap 배포
kubectl apply -f k8s/configmap.yaml

# Qdrant 배포
kubectl apply -f k8s/qdrant-deployment.yaml

# Ollama 배포 (모델 다운로드에 시간이 걸립니다)
kubectl apply -f k8s/ollama-deployment.yaml

# API Server 배포
kubectl apply -f k8s/api-server-deployment.yaml
```

### 5. 배포 확인

```powershell
# Pod 상태 확인
kubectl get pods -n rag-system

# 서비스 확인
kubectl get svc -n rag-system

# 로그 확인
kubectl logs -f deployment/rag-api-server -n rag-system
```

### 6. API 접근

NodePort로 설정되어 있어 다음 URL로 접근 가능:

- API 문서: http://localhost:30080/docs
- 헬스체크: http://localhost:30080/health

## 📁 프로젝트 구조

```
K8S_RAG/
├── api-server/
│   ├── Dockerfile              # API 서버 Docker 이미지
│   ├── requirements.txt        # Python 의존성
│   ├── main.py                 # FastAPI 메인
│   ├── pdf_processor.py        # PDF 처리
│   ├── embedding_model.py      # 로컬 임베딩
│   ├── qdrant_client_wrapper.py # Qdrant 클라이언트
│   ├── ollama_client.py        # Ollama 클라이언트
│   └── rag_pipeline.py         # LangGraph RAG 파이프라인
├── k8s/
│   ├── namespace.yaml          # 네임스페이스
│   ├── configmap.yaml          # 설정
│   ├── qdrant-deployment.yaml  # Qdrant 배포
│   ├── ollama-deployment.yaml  # Ollama 배포
│   └── api-server-deployment.yaml # API 서버 배포
├── 학번.txt                     # Docker Hub URL
└── README.md                   # 이 파일
```

## 🔌 API 엔드포인트

### PDF 업로드
```bash
POST /upload
Content-Type: multipart/form-data

# 예시 (curl)
curl -X POST "http://localhost:30080/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### 질문하기
```bash
POST /query
Content-Type: application/json

{
  "query": "문서에서 주요 내용이 무엇인가요?",
  "doc_id": "optional-document-id"
}
```

### 헬스체크
```bash
GET /health
```

### 문서 목록
```bash
GET /documents
```

## 🛠️ 기술 스택

- **API Server**: FastAPI, LangGraph, Python 3.11
- **Vector DB**: Qdrant
- **LLM**: Ollama (gemma2:2b)
- **임베딩**: sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Container**: Docker, Kubernetes

## 📝 Pod 간 통신 흐름

1. **PDF 업로드 시**
   - 사용자 → API Server: PDF 파일 전송
   - API Server 내부: 텍스트 추출 및 청킹
   - API Server 내부: 임베딩 생성
   - API Server → Qdrant: 벡터 저장

2. **질문 시**
   - 사용자 → API Server: 질문 전송
   - API Server 내부: 질문 임베딩
   - API Server → Qdrant: 유사 문서 검색
   - API Server → Ollama: 컨텍스트 + 질문 전달
   - Ollama → API Server: 생성된 답변
   - API Server → 사용자: 최종 답변

## ⚠️ 주의사항

- Ollama는 처음 시작 시 모델 다운로드에 시간이 걸립니다 (gemma2:2b ~1.5GB)
- GPU가 없는 환경에서는 LLM 응답이 느릴 수 있습니다
- 임베딩 모델도 처음 로드 시 다운로드됩니다 (~420MB)

## 📄 라이선스

MIT License
