# K8S RAG 시스템 아키텍처 보고서

## 📋 개요

**K8S RAG (Retrieval-Augmented Generation)**는 Kubernetes 기반의 엔터프라이즈급 문서 기반 AI 시스템입니다.
사용자가 업로드한 PDF 문서를 벡터화하여 저장하고, 자연언어 질문에 대해 관련 문서를 검색한 후 
LLM(Large Language Model)을 통해 정확한 답변을 생성합니다.

### 핵심 기능
- ✅ PDF 문서 자동 처리 및 벡터화
- ✅ 의미론적 유사도 기반 검색
- ✅ LLM 기반 자연스러운 답변 생성
- ✅ Kubernetes 기반 확장 가능한 배포
- ✅ 온-프레미스 프라이빗 AI (API 없음)

---

## 🏗️ 시스템 아키텍처

### 전체 구조도

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  (StreamLit Dashboard / K8S Dashboard / REST API Client)         │
└─────────────────────────────────────────────────────────────────┘
                              ↓↑
┌─────────────────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                             │
│                   (Namespace: rag-namespace)                     │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐   │
│  │  API Server      │  │    Qdrant        │  │   Ollama    │   │
│  │  (FastAPI)       │  │ (Vector DB)      │  │  (LLM)      │   │
│  │                  │  │                  │  │             │   │
│  │  Port: 8000      │  │  Port: 6333      │  │ Port: 11434 │   │
│  │                  │  │                  │  │             │   │
│  │ /upload          │  │ 384-dim vectors  │  │ Gemma2:2b   │   │
│  │ /query           │  │ 336 vectors      │  │             │   │
│  │ /documents/list  │  │ COSINE distance  │  │ 2-4GB VRAM  │   │
│  │ /health          │  │                  │  │             │   │
│  └──────────────────┘  └──────────────────┘  └─────────────┘   │
│         ↓                     ↓                     ↓            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │           Persistent Storage (hostPath)                   │ │
│  │  /var/lib/qdrant → Qdrant DB                              │ │
│  │  /var/lib/ollama → Ollama Models                          │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 핵심 컴포넌트

### 1. API Server (FastAPI)

**역할**: RAG 파이프라인의 중앙 오케스트레이터

**주요 책임**:
- PDF 파일 수신 및 검증
- 텍스트 추출 및 청킹
- 임베딩 생성
- 벡터 저장소 관리
- 질의 처리 및 답변 생성
- 모니터링 및 헬스체크

**API 엔드포인트**:
```
POST   /upload              - PDF 업로드 및 벡터화
POST   /query               - RAG 질의응답
GET    /documents           - 컬렉션 정보 조회
GET    /documents/list      - 저장된 문서 ID 리스트
DELETE /documents/{doc_id}  - 문서 삭제
GET    /health              - 전체 시스템 헬스체크
GET    /models              - 사용 가능한 모델 목록
```

**주요 라이브러리**:
```
fastapi==0.109.0
pydantic==2.10.5
sentence-transformers==2.7.0
qdrant-client==1.11.1
langchain==0.1.20
langgraph==0.0.26
```

### 2. Qdrant (Vector Database)

**역할**: 고성능 벡터 검색 엔진

**특징**:
- 벡터 차원: 384 (Sentence-Transformers)
- 거리 메트릭: COSINE 유사도
- 현재 저장 데이터: 336 벡터 (15개 PDF × ~22청크)
- 실시간 검색: Top-K 유사도 기반 검색

**데이터 구조**:
```json
{
  "id": "vector-id",
  "vector": [0.245, 0.123, ..., 0.789],  // 384차원
  "payload": {
    "text": "청크된 문서 텍스트",
    "doc_id": "550e8400-e29b-41d4-a716",
    "filename": "document.pdf",
    "chunk_index": 0
  }
}
```

**저장소 경로**:
```
/var/lib/qdrant/
├── collections/documents/
│   ├── segments/
│   └── collection.json
└── snapshots/
```

### 3. Ollama (LLM Engine)

**역할**: 자연언어 이해 및 생성

**구성**:
- **모델**: Gemma2:2b (경량 언어 모델)
- **메모리**: 2-4GB VRAM
- **응답 시간**: 5-10초 (평균 문장 생성)
- **언어**: 한국어 및 영어 지원

**프롬프트 구조**:
```
System: 문서 기반 질답 AI 역할 지정
Context: 검색된 상위 3개 문서 청크
Query: 사용자 질문
```

---

## 📊 데이터 흐름

### 📤 문서 업로드 플로우

```
1. Client (PDF Upload)
         ↓
2. API Server Validation
    - 파일 형식 검증
    - MIME type 확인
         ↓
3. Text Extraction (PyPDF2)
    - PDF → Raw Text
    - 인코딩 정규화
         ↓
4. Text Chunking
    - 기본 크기: 500자
    - 오버랩: 50자
    - 결과: ~50개 청크
         ↓
5. Embedding Generation (Sentence-Transformers)
    - 각 청크를 384차원 벡터로 변환
    - 임베딩 시간: ~500ms-2초
         ↓
6. Vector Storage (Qdrant)
    - PointStruct 생성
    - 메타데이터 저장
    - 인덱싱
         ↓
7. Response to Client
    {
      "doc_id": "uuid",
      "filename": "document.pdf",
      "chunks_count": 50,
      "message": "업로드 성공"
    }

⏱️ 전체 소요시간: ~1.5-3초
```

### 🔍 질의응답 플로우

```
1. Client (Query)
    {
      "query": "Kubernetes Pod이란?",
      "doc_id": "optional"  // 특정 문서만 검색
    }
         ↓
2. Query Embedding
    - 질문을 384차원 벡터로 변환
    - 시간: ~500ms
         ↓
3. Vector Search (Qdrant)
    - 유사도 기반 Top-3 검색
    - COSINE 거리 메트릭
    - 시간: ~50-200ms
         ↓
4. Context Composition
    [참고 문서]
    검색된 청크 1
    ---
    검색된 청크 2
    ---
    검색된 청크 3
         ↓
5. Prompt Construction
    System: "당신은 문서 기반 QA 어시스턴트..."
    Context: (위의 청크들)
    Query: "Kubernetes Pod이란?"
         ↓
6. LLM Inference (Ollama)
    - Gemma2:2b 모델로 생성
    - Streaming 응답
    - 시간: ~5-10초
         ↓
7. Response to Client
    {
      "query": "Kubernetes Pod이란?",
      "response": "Pod은 Kubernetes에서...",
      "contexts": [청크1, 청크2, 청크3]
    }

⏱️ 전체 소요시간: ~6-12초
```

---

## 🚀 배포 구조 (Kubernetes)

### Namespace 및 리소스

```yaml
# 네임스페이스
apiVersion: v1
kind: Namespace
metadata:
  name: rag-namespace

---
# API Server Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: rag-namespace
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api-server
        image: api-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: QDRANT_HOST
          value: "qdrant-service"
        - name: QDRANT_PORT
          value: "6333"
        - name: OLLAMA_HOST
          value: "http://ollama-service:11434"

---
# Qdrant StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: rag-namespace
spec:
  serviceName: qdrant-service
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
        volumeMounts:
        - name: qdrant-data
          mountPath: /qdrant/storage
      volumes:
      - name: qdrant-data
        hostPath:
          path: /var/lib/qdrant
          type: DirectoryOrCreate

---
# Ollama StatefulSet
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ollama
  namespace: rag-namespace
spec:
  serviceName: ollama-service
  replicas: 1
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        ports:
        - containerPort: 11434
        volumeMounts:
        - name: ollama-data
          mountPath: /root/.ollama
      volumes:
      - name: ollama-data
        hostPath:
          path: /var/lib/ollama
          type: DirectoryOrCreate

---
# Services
apiVersion: v1
kind: Service
metadata:
  name: api-server-service
  namespace: rag-namespace
spec:
  type: ClusterIP
  selector:
    app: api-server
  ports:
  - port: 8000
    targetPort: 8000

---
apiVersion: v1
kind: Service
metadata:
  name: qdrant-service
  namespace: rag-namespace
spec:
  type: ClusterIP
  selector:
    app: qdrant
  ports:
  - port: 6333
    targetPort: 6333

---
apiVersion: v1
kind: Service
metadata:
  name: ollama-service
  namespace: rag-namespace
spec:
  type: ClusterIP
  selector:
    app: ollama
  ports:
  - port: 11434
    targetPort: 11434
```

### 서비스 통신 맵

```
API Server (8000)
    ├─ HTTP → Qdrant Service (6333)
    │          ├─ POST /collections
    │          ├─ PUT /collections/.../points
    │          └─ POST /collections/.../points/search
    │
    └─ HTTP → Ollama Service (11434)
               └─ POST /api/generate
```

---

## 💾 데이터 영속성

### hostPath 볼륨 구성

**왜 hostPath?**
- ✅ minikube 환경에서 로컬 스토리지 직접 액세스
- ✅ Pod 재시작 후에도 데이터 유지
- ✅ 빠른 I/O 성능
- ⚠️ 프로덕션에서는 PersistentVolumeClaim 권장

**저장 경로**:
```
Host Machine (minikube)
└─ /var/lib/
   ├─ qdrant/
   │  ├─ collections/documents/
   │  │  ├─ segments/
   │  │  └─ collection.json
   │  └─ snapshots/
   │
   └─ ollama/
      ├─ models/
      │  └─ gemma2-2b/ (5GB)
      └─ cache/
```

**데이터 크기**:
- Qdrant: ~100MB (336 벡터)
- Ollama Models: ~5GB (Gemma2:2b)
- 전체: ~5.1GB

---

## ⚙️ 기술 스택 요약

| 계층 | 기술 | 목적 | 버전 |
|------|------|------|------|
| **클라이언트** | StreamLit | 웹 UI 대시보드 | 1.28+ |
| **API** | FastAPI | REST 서버 | 0.109.0 |
| **데이터 검증** | Pydantic | 요청/응답 검증 | 2.10.5 |
| **임베딩** | Sentence-Transformers | 벡터 생성 | 2.7.0 |
| **벡터 DB** | Qdrant | 유사도 검색 | 1.11.1 |
| **LLM** | Ollama | 답변 생성 | latest |
| **모델** | Gemma2:2b | 경량 언어 모델 | 2b |
| **워크플로우** | LangGraph | 파이프라인 오케스트레이션 | 0.0.26 |
| **컨테이너** | Docker | 이미지화 | 20.10+ |
| **오케스트레이션** | Kubernetes | Pod 관리 | 1.24+ |

---

## 📈 성능 분석

### 처리 시간 분석

| 작업 | 소요시간 | 병목 | 최적화 |
|------|---------|------|--------|
| PDF 텍스트 추출 | 100-500ms | I/O | 병렬 처리 |
| 텍스트 청킹 | 10-50ms | CPU | 메모리 캐싱 |
| 임베딩 생성 | 500ms-2s | CPU | GPU 사용 |
| Qdrant 검색 | 50-200ms | I/O | 인덱싱 최적화 |
| LLM 답변 생성 | 5-10s | GPU | 모델 양자화 |
| **전체 RAG** | **6-13초** | LLM | - |

### 리소스 사용량

**API Server**:
```
Idle:  CPU 5-10%, Memory 100-150MB
Active: CPU 80-95%, Memory 200-300MB
```

**Qdrant**:
```
Idle:  CPU 2-5%, Memory 200-300MB
Search: CPU 30-50%, Memory 250-400MB
Disk: ~100MB per 336 vectors
```

**Ollama**:
```
Idle:  CPU 5-10%, Memory 2.5GB (모델 로드)
Generation: CPU 90-95%, VRAM 2-3GB
Disk: ~5GB (Gemma2:2b)
```

### 확장성 시나리오

```
현재 상태:
├─ 문서: 15개
├─ 벡터: 336개
└─ 응답시간: ~6초

2배 확장:
├─ 문서: 30개
├─ 벡터: 672개
└─ 응답시간: ~6-7초 (검색 약간 증가)

10배 확장:
├─ 문서: 150개
├─ 벡터: 3,360개
└─ 응답시간: ~7-8초
└─ 개선: Qdrant 인덱싱 최적화 필요 가능

100배 확장:
├─ 문서: 1,500개
├─ 벡터: 33,600개
└─ 응답시간: ~10-15초
└─ 개선: Kubernetes 멀티 Pod, Qdrant 샤딩
```

---

## 🛡️ 보안 및 프라이버시

### 온-프레미스 배포 이점
- ✅ 모든 데이터가 내부 시스템에만 저장
- ✅ 외부 API 의존성 없음
- ✅ 규정 준수 (GDPR, 개인정보보호)
- ✅ 완전한 데이터 제어

### 추천 보안 조치
```
1. RBAC 설정 (Kubernetes Role-Based Access Control)
2. 네트워크 정책 설정 (NetworkPolicy)
3. Pod 보안 정책 (Pod Security Policy)
4. Secret 관리 (민감한 설정값)
5. 정기적 백업 (hostPath 데이터)
```

---

## 🔄 모니터링 및 운영

### 헬스 체크 엔드포인트

```bash
# 전체 시스템 상태
curl http://api-server:8000/health

# 응답 예시
{
  "status": "healthy",
  "qdrant": true,
  "ollama": true,
  "embedding_model": true
}
```

### 로그 모니터링

```bash
# Pod 로그 확인
kubectl logs -n rag-namespace api-server-0
kubectl logs -n rag-namespace qdrant-0
kubectl logs -n rag-namespace ollama-0

# 실시간 로그 스트리밍
kubectl logs -n rag-namespace api-server-0 -f
```

### 리소스 모니터링

```bash
# Pod 리소스 사용량
kubectl top pods -n rag-namespace

# Pod 상태 확인
kubectl get pods -n rag-namespace -o wide

# 이벤트 확인
kubectl describe pod <pod-name> -n rag-namespace
```

---

## 📚 사용 사례

### 1. 교육 분야
```
입력: 강의 자료 PDF 업로드
처리: 강의 내용 벡터화 → 인덱싱
활용: 학생 질문에 강의 기반 자동 답변
효과: 학습 효율 증대, 강사 업무 감소
```

### 2. 기업 내부 시스템
```
입력: 정책서, 매뉴얼, 기술문서 업로드
처리: 조직 지식 벡터화 → 검색 인덱스
활용: 직원 질문에 정책 기반 자동 답변
효과: 온보딩 시간 단축, 컴플라이언스 강화
```

### 3. 의료 분야
```
입력: 임상 가이드라인, 의료 논문 업로드
처리: 의료 지식 벡터화 → 의미 검색
활용: 의사 질문에 증거 기반 정보 제공
효과: 진단 정확도 향상, 근거 기반 의료
```

### 4. 법률 분야
```
입력: 판례, 계약 템플릿, 법령 업로드
처리: 법률 문서 벡터화 → 사례 검색
활용: 변호사 질문에 관련 판례/법령 제시
효과: 법률 조사 시간 단축, 선례 발굴
```

---

## 🎯 결론

K8S RAG는 **3가지 핵심 기술**의 완벽한 통합입니다:

1. **의미론적 검색** (Sentence-Transformers + Qdrant)
   - 키워드가 아닌 의미 기반 검색
   - 높은 정확도와 빠른 응답시간

2. **자연언어 생성** (Ollama + Gemma2)
   - 문맥을 이해한 자연스러운 답변
   - 온-프레미스 배포로 프라이버시 보호

3. **확장 가능한 인프라** (Kubernetes)
   - 수평 확장으로 대규모 문서 처리
   - 자동 장애 복구 및 모니터링

이 아키텍처는 **엔터프라이즈급 AI 애플리케이션**의 기준을 제시하며,
조직의 방대한 문서 자산을 효율적으로 활용할 수 있는 솔루션입니다.

---

## 📞 부록

### 주요 명령어

```bash
# 시스템 배포
kubectl apply -f k8s/

# Pod 상태 확인
kubectl get pods -n rag-namespace

# 로그 확인
kubectl logs -n rag-namespace api-server-0

# API 테스트
curl -X POST http://localhost:8000/upload -F "file=@document.pdf"

# 문서 목록 확인
curl http://localhost:8000/documents/list

# 질의 테스트
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Kubernetes란?"}'
```

### 문제 해결

| 문제 | 원인 | 해결 |
|------|------|------|
| API 연결 실패 | 서비스 미실행 | `kubectl get svc -n rag-namespace` |
| 검색 결과 없음 | 문서 미업로드 | `/documents/list`로 확인 |
| 답변 응답 느림 | LLM 부하 | Pod 리소스 확인 |
| 저장소 부족 | hostPath 용량 초과 | `/var/lib/qdrant` 크기 확인 |

