# K8S RAG: Kubernetes 기반 문서 검색 생성 시스템

<div align="center">

![K8S RAG](https://img.shields.io/badge/K8S-RAG-blue?style=flat-square)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green?style=flat-square)
![Kubernetes](https://img.shields.io/badge/Kubernetes-1.24+-orange?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)

**온-프레미스 기반 엔터프라이즈급 문서 AI 시스템**

[빠른 시작](#-빠른-시작) • [아키텍처](#-시스템-아키텍처) • [API 문서](#-api-엔드포인트) • [배포](#-배포) • [문제해결](#-문제-해결)

</div>

---

## 📌 개요

**K8S RAG**는 PDF 문서를 벡터화하여 의미론적 유사도 기반으로 검색하고, 
LLM을 통해 정확한 답변을 생성하는 Kubernetes 기반 시스템입니다.

### 🎯 핵심 기능

- 📄 **PDF 자동 처리**: 텍스트 추출, 청킹, 임베딩 생성
- 🔍 **의미론적 검색**: 384차원 벡터 기반 유사도 검색
- 🤖 **자동 답변 생성**: Gemma2 LLM을 통한 자연스러운 응답
- 🐳 **컨테이너 기반**: Docker & Kubernetes로 쉬운 배포
- 🔒 **프라이빗 AI**: 온-프레미스 배포로 완전한 데이터 보호
- ⚡ **고성능**: 평균 6초 내 RAG 완료

---

## 🚀 빠른 시작

### 필수 요구사항

```bash
# 시스템 요구사항
- Docker 20.10+
- Kubernetes 1.24+ (minikube 지원)
- 메모리: 최소 8GB (권장 16GB)
- 디스크: 최소 20GB (Ollama 모델 5GB + Qdrant)
```

### 1️⃣ 저장소 클론

```bash
git clone https://github.com/How0515/K8S_RAG.git
cd K8S_RAG
```

### 2️⃣ Kubernetes 배포

```bash
# minikube 시작 (아직 실행 중이 아닌 경우)
minikube start --memory=8192 --cpus=4

# 이미지 빌드
docker build -t api-server:latest ./api-server/

# Kubernetes 리소스 배포
kubectl apply -f k8s/

# Pod 상태 확인
kubectl get pods -n rag-namespace -w
```

### 3️⃣ API 포트 포워딩

```bash
# 터미널 1: API Server 포트 포워딩
kubectl port-forward -n rag-namespace svc/api-server-service 8000:8000

# 터미널 2: Qdrant 포트 포워딩 (선택사항)
kubectl port-forward -n rag-namespace svc/qdrant-service 6333:6333

# 터미널 3: Ollama 포트 포워딩 (선택사항)
kubectl port-forward -n rag-namespace svc/ollama-service 11434:11434
```

### 4️⃣ 시스템 테스트

```bash
# 헬스 체크
curl http://localhost:8000/health

# 응답 예시
{
  "status": "healthy",
  "qdrant": true,
  "ollama": true,
  "embedding_model": true
}
```

---

## 🏗️ 시스템 아키텍처

### 전체 구조

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│        (StreamLit Dashboard / REST API / Web Browser)            │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                             │
│                   (Namespace: rag-namespace)                     │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐   │
│  │  API Server      │  │    Qdrant        │  │   Ollama    │   │
│  │  (FastAPI)       │  │ (Vector DB)      │  │  (LLM)      │   │
│  │  Port: 8000      │  │  Port: 6333      │  │ Port: 11434 │   │
│  └──────────────────┘  └──────────────────┘  └─────────────┘   │
│         ↓                     ↓                     ↓            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │     Persistent Storage (hostPath)                         │ │
│  │  /var/lib/qdrant  /var/lib/ollama                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 핵심 컴포넌트

| 컴포넌트 | 역할 | 포트 | 메모리 |
|---------|------|------|--------|
| **API Server** | 요청 처리, 파이프라인 관리 | 8000 | 200-300MB |
| **Qdrant** | 벡터 저장 및 검색 (384-dim) | 6333 | 250-400MB |
| **Ollama** | LLM 추론 (Gemma2:2b) | 11434 | 2.5GB |

---

## 📡 API 엔드포인트

### 1. 문서 업로드

```bash
POST /upload
Content-Type: multipart/form-data

# 요청
curl -X POST http://localhost:8000/upload \
  -F "file=@document.pdf"

# 응답
{
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "chunks_count": 50,
  "message": "문서 'document.pdf'이 성공적으로 업로드되었습니다."
}
```

**설명:**
- PDF 파일을 업로드하여 벡터화
- 텍스트 추출 → 청킹 (500자/50자 오버랩) → 임베딩 생성 → Qdrant 저장
- 소요시간: ~1-3초

---

### 2. RAG 질의응답

```bash
POST /query
Content-Type: application/json

# 요청
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Kubernetes Pod이란?",
    "doc_id": "optional-filter"
  }'

# 응답
{
  "query": "Kubernetes Pod이란?",
  "response": "Pod은 Kubernetes 클러스터에서 배포할 수 있는 가장 작은 단위입니다...",
  "contexts": [
    "관련 문서 청크 1",
    "관련 문서 청크 2",
    "관련 문서 청크 3"
  ]
}
```

**설명:**
- 질문을 벡터화 → Qdrant에서 Top-3 유사 문서 검색 → LLM으로 답변 생성
- 소요시간: ~6-12초

---

### 3. 저장된 문서 조회

```bash
GET /documents

# 응답
{
  "name": "documents",
  "vectors_count": 336,
  "points_count": 336
}
```

---

### 4. 문서 ID 리스트 조회

```bash
GET /documents/list

# 응답
{
  "total_documents": 2,
  "documents": [
    {
      "doc_id": "550e8400-e29b-41d4-a716",
      "filename": "kubernetes-guide.pdf",
      "chunks": 50
    },
    {
      "doc_id": "660e8400-e29b-41d4-a717",
      "filename": "api-reference.pdf",
      "chunks": 35
    }
  ]
}
```

---

### 5. 문서 삭제

```bash
DELETE /documents/{doc_id}

# 요청
curl -X DELETE http://localhost:8000/documents/550e8400-e29b-41d4-a716

# 응답
{
  "message": "문서 550e8400-e29b-41d4-a716가 삭제되었습니다."
}
```

---

### 6. 헬스 체크

```bash
GET /health

# 응답
{
  "status": "healthy",
  "qdrant": true,
  "ollama": true,
  "embedding_model": true
}
```

---

### 7. 사용 가능한 모델 조회

```bash
GET /models

# 응답
{
  "models": [
    "gemma2:2b"
  ]
}
```

---

## 📁 프로젝트 구조

```
K8S_RAG/
├── api-server/                    # FastAPI 애플리케이션
│   ├── main.py                   # FastAPI 앱 및 엔드포인트
│   ├── pdf_processor.py          # PDF 처리 로직
│   ├── embedding_model.py        # 임베딩 모델 관리
│   ├── qdrant_client_wrapper.py  # Qdrant 클라이언트
│   ├── ollama_client.py          # Ollama 클라이언트
│   ├── rag_pipeline.py           # RAG 파이프라인
│   ├── requirements.txt          # Python 의존성
│   └── Dockerfile               # Docker 이미지 정의
│
├── k8s/                          # Kubernetes 매니페스트
│   ├── namespace.yaml           # rag-namespace 생성
│   ├── configmap.yaml           # 설정 맵
│   ├── api-server-deployment.yaml
│   ├── qdrant-deployment.yaml
│   └── ollama-deployment.yaml
│
├── deploy.ps1                    # Windows 배포 스크립트
├── cleanup.ps1                   # 정리 스크립트
├── .gitignore                   # Git 무시 파일
└── README.md                    # 본 문서
```

---

## 🔧 데이터 흐름

### 📤 문서 업로드 과정

```
1. PDF 파일 업로드 (client → API Server)
   ↓
2. 파일 검증 및 텍스트 추출 (PyPDF2)
   ↓
3. 텍스트 청킹 (500자 단위, 50자 오버랩)
   ↓
4. 임베딩 생성 (Sentence-Transformers, 384-dim)
   ↓
5. Qdrant 벡터 DB에 저장
   ↓
6. 응답 반환 (doc_id, chunks_count)

⏱️ 전체 소요시간: ~1-3초
```

### 🔍 질의응답 과정

```
1. 사용자 질문 입력 (client → API Server)
   ↓
2. 질문 벡터화 (Sentence-Transformers)
   ↓
3. Qdrant에서 유사도 기반 Top-3 검색
   ↓
4. 검색 결과를 컨텍스트로 구성
   ↓
5. 프롬프트 생성 (System + Context + Query)
   ↓
6. Ollama (Gemma2:2b)로 답변 생성
   ↓
7. 답변 및 관련 문서 반환

⏱️ 전체 소요시간: ~6-12초 (대부분 LLM 추론)
```

---

## 🐳 배포

### Docker 이미지 빌드

```bash
cd api-server/
docker build -t api-server:latest .
```

### Kubernetes 배포

```bash
# 네임스페이스, 서비스, Pod 배포
kubectl apply -f k8s/

# 배포 상태 확인
kubectl get all -n rag-namespace

# 로그 확인
kubectl logs -n rag-namespace -l app=api-server -f
```

### 데이터 영속성

시스템은 호스트의 다음 경로에 데이터를 저장합니다:

```
/var/lib/qdrant/     → Qdrant 벡터 데이터베이스
/var/lib/ollama/     → Ollama 모델 파일 (5GB)
```

**hostPath 볼륨 사용 이유:**
- ✅ minikube 환경에서 로컬 스토리지 액세스
- ✅ Pod 재시작 후에도 데이터 유지
- ✅ 빠른 I/O 성능

---

## 📊 성능 지표

### 처리 시간

| 작업 | 소요시간 | 메모 |
|------|---------|------|
| PDF 텍스트 추출 | 100-500ms | 파일 크기 의존 |
| 텍스트 청킹 | 10-50ms | 메모리 기반 |
| 임베딩 생성 | 500ms-2s | CPU 기반 |
| Qdrant 검색 | 50-200ms | 벡터 수 의존 |
| LLM 답변 생성 | 5-10s | GPU 기반 |
| **전체 RAG** | **6-13초** | 평균 |

### 리소스 사용량

**API Server:**
```
Idle:    CPU 5-10%,   Memory 100-150MB
Active:  CPU 80-95%,  Memory 200-300MB
```

**Qdrant:**
```
Idle:    CPU 2-5%,    Memory 200-300MB
Search:  CPU 30-50%,  Memory 250-400MB
Storage: ~100MB per 336 vectors
```

**Ollama:**
```
Idle:        CPU 5-10%,    Memory 2.5GB
Generation:  CPU 90-95%,   VRAM 2-3GB
Storage:     ~5GB (Gemma2:2b 모델)
```

---

## 🛠️ 기술 스택

| 계층 | 기술 | 버전 | 용도 |
|------|------|------|------|
| **API** | FastAPI | 0.109.0 | REST 서버 |
| **데이터 검증** | Pydantic | 2.10.5 | 타입 안전성 |
| **임베딩** | Sentence-Transformers | 2.7.0 | 벡터 생성 |
| **벡터 DB** | Qdrant | 1.11.1 | 유사도 검색 |
| **LLM** | Ollama | latest | 답변 생성 |
| **모델** | Gemma2:2b | 2b | 경량 언어 모델 |
| **LLM 오케스트레이션** | LangGraph | 0.0.26 | 파이프라인 관리 |
| **PDF 처리** | PyPDF2 | latest | 텍스트 추출 |
| **컨테이너** | Docker | 20.10+ | 이미지화 |
| **오케스트레이션** | Kubernetes | 1.24+ | Pod 관리 |

---

## 🔐 보안 및 프라이버시

### 온-프레미스 배포의 장점

- ✅ **데이터 보호**: 모든 데이터가 내부 시스템에만 저장
- ✅ **규정 준수**: GDPR, CCPA 등 규정 준수 용이
- ✅ **비용 절감**: 외부 API 호출 없음
- ✅ **완전 제어**: 시스템의 모든 측면 제어 가능

### 권장 보안 조치

```bash
# 1. RBAC 설정 (역할 기반 접근 제어)
kubectl apply -f k8s/rbac.yaml

# 2. 네트워크 정책 설정
kubectl apply -f k8s/network-policy.yaml

# 3. Pod 보안 정책
kubectl apply -f k8s/psp.yaml

# 4. Secret 관리 (민감 정보)
kubectl create secret generic api-keys \
  --from-literal=db-password=<password> \
  -n rag-namespace
```

---

## 📈 확장성

### 현재 상태
```
문서: 15개
벡터: 336개
응답시간: ~6초
```

### 수평 확장 시나리오

```
10배 확장 (150개 문서):
├─ 벡터: 3,360개
├─ 응답시간: ~7-8초
└─ 변경: 기존 설정 유지 가능

100배 확장 (1,500개 문서):
├─ 벡터: 33,600개
├─ 응답시간: ~10-15초
└─ 변경: Kubernetes Pod 복제, 로드 밸런싱

1,000배 확장 (15,000개 문서):
├─ 벡터: 336,000개
├─ 응답시간: ~15-30초
└─ 변경: Qdrant 샤딩, 다중 노드 클러스터
```

---

## 🐛 문제 해결

### API 서버 연결 불가

```bash
# Pod 상태 확인
kubectl get pods -n rag-namespace

# Pod 상세 정보 확인
kubectl describe pod api-server-0 -n rag-namespace

# 로그 확인
kubectl logs api-server-0 -n rag-namespace

# 포트 포워딩 재시작
kubectl port-forward -n rag-namespace svc/api-server-service 8000:8000
```

### 검색 결과 없음

```bash
# 저장된 문서 확인
curl http://localhost:8000/documents/list

# Qdrant 직접 접근
kubectl port-forward -n rag-namespace svc/qdrant-service 6333:6333
curl http://localhost:6333/health
```

### 응답이 너무 느림

```bash
# Pod 리소스 사용량 확인
kubectl top pods -n rag-namespace

# Node 리소스 확인
kubectl top nodes

# Ollama 상태 확인
kubectl logs ollama-0 -n rag-namespace -f
```

### 저장소 부족

```bash
# 호스트 디스크 확인
df -h /var/lib/

# Qdrant 데이터 크기 확인
du -sh /var/lib/qdrant/

# 오래된 문서 삭제
curl -X DELETE http://localhost:8000/documents/{doc_id}
```

---

## 📚 사용 예시

### 1. Python 클라이언트

```python
import requests
import json

API_URL = "http://localhost:8000"

# 문서 업로드
with open("guide.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{API_URL}/upload", files=files)
    doc_data = response.json()
    print(f"업로드 완료: {doc_data['doc_id']}")

# 질의응답
query_data = {
    "query": "이 문서에서 주요 내용은?",
    "doc_id": doc_data["doc_id"]
}
response = requests.post(f"{API_URL}/query", json=query_data)
result = response.json()
print(f"답변: {result['response']}")
```

### 2. cURL 예시

```bash
# 여러 문서 일괄 업로드
for file in *.pdf; do
  curl -X POST http://localhost:8000/upload -F "file=@$file"
done

# 모든 문서 조회
curl http://localhost:8000/documents/list | jq .

# 특정 질문으로 검색
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "주요 기능은?"}'
```

---

## 🤝 기여 가이드

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 라이선스

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 지원

### 문서
- [API 문서](./api-server/main.py) - Python 코드 주석 참고
- [Kubernetes 설정](./k8s/) - YAML 매니페스트 확인

### 이슈 및 질문
GitHub Issues에서 버그 리포트 및 기능 요청을 받습니다.

### 개발자 연락
프로젝트 관리자: [How0515](https://github.com/How0515)

---

## 🎯 로드맵

- [ ] StreamLit 대시보드 개선
- [ ] K8S 대시보드 추가
- [ ] GPU 지원 추가
- [ ] 다중 모델 지원
- [ ] 실시간 답변 스트리밍
- [ ] 문서 버전 관리
- [ ] 사용자 권한 관리

---

<div align="center">

**⭐ 이 프로젝트가 유용하다면 Star를 눌러주세요! ⭐**

Made with ❤️ by [How0515](https://github.com/How0515)

</div>
