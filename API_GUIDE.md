# K8S RAG API 사용 가이드

## 📌 개요

K8S RAG 시스템은 PDF 문서를 벡터 데이터베이스에 저장하고, 그 문서를 기반으로 AI가 질문에 답변하는 시스템입니다.

**주요 구성:**
- **API 서버**: FastAPI (포트 8000/30080)
- **벡터 DB**: Qdrant (포트 6333)
- **LLM**: Ollama (포트 11434)
- **임베딩 모델**: Sentence-Transformers (다국어 지원)

---

## 🌐 API 엔드포인트

### 1️⃣ 루트 엔드포인트
```
GET /
```

**설명**: API 서버 정보 및 문서 링크 반환

**응답 예시**:
```json
{
  "message": "K8S RAG API Server",
  "docs": "/docs",
  "health": "/health"
}
```

---

### 2️⃣ 헬스 체크
```
GET /health
```

**설명**: 모든 서비스(Qdrant, Ollama, 임베딩 모델) 상태 확인

**응답 형식**:
```json
{
  "status": "healthy|degraded",
  "qdrant": true/false,
  "ollama": true/false,
  "embedding_model": true/false
}
```

**응답 예시**:
```json
{
  "status": "healthy",
  "qdrant": true,
  "ollama": true,
  "embedding_model": true
}
```

---

### 3️⃣ PDF 업로드
```
POST /upload
```

**설명**: PDF 파일을 업로드하여 벡터 데이터베이스에 저장

**요청 방식**: multipart/form-data

**파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `file` | File | 업로드할 PDF 파일 (필수) |

**응답 형식**:
```json
{
  "doc_id": "uuid-string",
  "filename": "document.pdf",
  "chunks_count": 15,
  "message": "문서 'document.pdf'이 성공적으로 업로드되었습니다."
}
```

**처리 과정**:
1. PDF에서 텍스트 추출 (pypdf 사용)
2. 텍스트를 500자 크기로 청킹 (50자 오버랩)
3. 각 청크를 임베딩 벡터로 변환 (384차원)
4. Qdrant에 저장

**curl 예시**:
```bash
curl -X POST \
  -F "file=@document.pdf" \
  http://localhost:8000/upload
```

**Python 예시**:
```python
import requests

with open('document.pdf', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/upload', files=files)
    result = response.json()
    doc_id = result['doc_id']
    print(f"업로드된 문서 ID: {doc_id}")
```

---

### 4️⃣ RAG 질의응답
```
POST /query
```

**설명**: 업로드된 문서를 기반으로 질문에 답변

**요청 본문 (JSON)**:
```json
{
  "query": "문서의 주요 내용이 무엇입니까?",
  "doc_id": "uuid-string (선택사항)"
}
```

**파라미터 설명**:
| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `query` | string | ✅ | 사용자의 질문 |
| `doc_id` | string | ❌ | 특정 문서 내에서만 검색 (미지정 시 전체 문서 검색) |

**응답 형식**:
```json
{
  "query": "문서의 주요 내용이 무엇입니까?",
  "response": "AI가 생성한 답변...",
  "contexts": [
    "검색된 관련 문서 청크 1",
    "검색된 관련 문서 청크 2",
    "검색된 관련 문서 청크 3"
  ]
}
```

**처리 과정**:
1. 질문을 임베딩 벡터로 변환
2. Qdrant에서 유사한 문서 청크 검색 (상위 3개)
3. 검색된 청크를 컨텍스트로 Ollama에 전달
4. LLM이 컨텍스트 기반으로 답변 생성

**curl 예시**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "이 문서의 주제는?"}' \
  http://localhost:8000/query
```

**특정 문서에서만 검색**:
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "이 문서의 주제는?", "doc_id": "12345-67890"}' \
  http://localhost:8000/query
```

**Python 예시**:
```python
import requests
import json

response = requests.post(
    'http://localhost:8000/query',
    json={
        'query': '이 문서의 주요 내용이 무엇인가?',
        'doc_id': '12345-67890'  # 선택사항
    }
)

result = response.json()
print("질문:", result['query'])
print("답변:", result['response'])
print("\n참고 문서:")
for i, context in enumerate(result['contexts'], 1):
    print(f"{i}. {context[:100]}...")
```

---

### 5️⃣ 저장된 문서 조회
```
GET /documents
```

**설명**: 벡터 데이터베이스에 저장된 문서 정보 조회

**응답 형식**:
```json
{
  "name": "documents",
  "vectors_count": 45,
  "points_count": 45
}
```

**curl 예시**:
```bash
curl http://localhost:8000/documents
```

---

### 6️⃣ 문서 삭제
```
DELETE /documents/{doc_id}
```

**설명**: 특정 문서를 벡터 데이터베이스에서 삭제

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `doc_id` | string | 삭제할 문서의 UUID |

**응답 형식**:
```json
{
  "message": "문서 12345-67890이 삭제되었습니다."
}
```

**curl 예시**:
```bash
curl -X DELETE http://localhost:8000/documents/12345-67890
```

---

### 7️⃣ 사용 가능한 모델 조회
```
GET /models
```

**설명**: Ollama에서 사용 가능한 LLM 모델 목록 조회

**응답 형식**:
```json
{
  "models": ["gemma2:2b", "llama2:7b"]
}
```

**curl 예시**:
```bash
curl http://localhost:8000/models
```

---

## 🔧 설정 및 환경 변수

### 임베딩 모델
- **이름**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **차원**: 384
- **용도**: 다국어 텍스트 임베딩

### LLM 모델
- **기본 모델**: `gemma2:2b`
- **포트**: Ollama 11434
- **특징**: 한국어 지원 우수, 경량

### 텍스트 청킹 설정
- **청크 크기**: 500자
- **오버랩**: 50자

### 검색 설정
- **반환 결과**: 상위 3개 문서
- **유사도 측정**: 코사인 유사도

### 생성 설정
- **온도 (Temperature)**: 0.3 (낮을수록 일관성 있음)
- **최대 토큰**: 1024

---

## 📊 처리 흐름 다이어그램

### PDF 업로드 흐름
```
┌─────────────┐
│ PDF 파일    │
└──────┬──────┘
       ↓
┌──────────────────┐
│ 텍스트 추출       │ (pypdf)
└──────┬───────────┘
       ↓
┌──────────────────────┐
│ 텍스트 청킹          │ (500자 단위)
└──────┬───────────────┘
       ↓
┌──────────────────────────┐
│ 임베딩 변환              │ (384차원)
└──────┬───────────────────┘
       ↓
┌──────────────────────────────┐
│ Qdrant에 저장               │
│ (doc_id로 그룹화)          │
└──────────────────────────────┘
```

### 질의응답 흐름
```
┌──────────────────┐
│ 사용자 질문      │
└──────┬───────────┘
       ↓
┌──────────────────────────┐
│ 질문 임베딩 변환         │
└──────┬───────────────────┘
       ↓
┌─────────────────────────────┐
│ Qdrant 검색                 │
│ (상위 3개 청크 반환)        │
└──────┬──────────────────────┘
       ↓
┌────────────────────────────┐
│ 컨텍스트 조합              │
└──────┬─────────────────────┘
       ↓
┌─────────────────────────────┐
│ Ollama LLM에 프롬프트 전송   │
│ (컨텍스트 + 질문)          │
└──────┬──────────────────────┘
       ↓
┌──────────────────────────┐
│ AI 답변 생성             │
└──────┬───────────────────┘
       ↓
┌──────────────────────────┐
│ 응답 반환                │
│ (답변 + 참고 문서)      │
└──────────────────────────┘
```

---

## 🚀 사용 예시

### 전체 워크플로우 (Python)

```python
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def upload_document(pdf_path):
    """PDF 문서 업로드"""
    print("📤 문서 업로드 중...")
    with open(pdf_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/upload", files=files)
    
    result = response.json()
    print(f"✅ 업로드 완료")
    print(f"   문서 ID: {result['doc_id']}")
    print(f"   파일명: {result['filename']}")
    print(f"   청크 수: {result['chunks_count']}")
    return result['doc_id']

def query_document(question, doc_id=None):
    """문서 기반 질의응답"""
    print(f"\n❓ 질문: {question}")
    
    payload = {'query': question}
    if doc_id:
        payload['doc_id'] = doc_id
    
    response = requests.post(f"{BASE_URL}/query", json=payload)
    result = response.json()
    
    print(f"✨ 답변: {result['response']}")
    print(f"\n📚 참고 문서 ({len(result['contexts'])}개):")
    for i, context in enumerate(result['contexts'], 1):
        print(f"   {i}. {context[:80]}...")

def check_health():
    """시스템 상태 확인"""
    response = requests.get(f"{BASE_URL}/health")
    status = response.json()
    
    print("🏥 시스템 상태:")
    print(f"   전체: {status['status']}")
    print(f"   Qdrant: {'✅' if status['qdrant'] else '❌'}")
    print(f"   Ollama: {'✅' if status['ollama'] else '❌'}")
    print(f"   임베딩: {'✅' if status['embedding_model'] else '❌'}")

# 사용 예시
if __name__ == "__main__":
    # 1. 시스템 상태 확인
    check_health()
    
    # 2. 문서 업로드
    doc_id = upload_document("sample.pdf")
    
    # 3. 질의응답
    query_document("이 문서의 주제는?", doc_id)
    query_document("주요 내용을 요약해주세요", doc_id)
    query_document("언제 작성되었나요?", doc_id)
```

### curl을 이용한 전체 예시

```bash
# 1. 시스템 상태 확인
curl http://localhost:8000/health | jq .

# 2. 문서 업로드
DOC_RESPONSE=$(curl -X POST -F "file=@document.pdf" http://localhost:8000/upload)
DOC_ID=$(echo $DOC_RESPONSE | jq -r '.doc_id')
echo "업로드된 문서 ID: $DOC_ID"

# 3. 질의응답
curl -X POST \
  -H "Content-Type: application/json" \
  -d "{\"query\": \"이 문서의 주제는?\", \"doc_id\": \"$DOC_ID\"}" \
  http://localhost:8000/query | jq .

# 4. 저장된 문서 조회
curl http://localhost:8000/documents | jq .

# 5. 문서 삭제
curl -X DELETE http://localhost:8000/documents/$DOC_ID
```

---

## ⚠️ 에러 처리

### 일반적인 에러

| 상태 코드 | 설명 | 해결 방법 |
|----------|------|---------|
| 400 | PDF 파일 아님 | `.pdf` 확장자 파일만 업로드 |
| 400 | 텍스트 추출 불가 | 텍스트 기반 PDF 확인 |
| 400 | 질문 입력 없음 | query 필드에 질문 입력 |
| 500 | 서비스 에러 | Qdrant/Ollama 상태 확인 |

### 헬스 체크로 진단

```bash
# 시스템 상태 확인
curl http://localhost:8000/health

# 응답이 "degraded"이면 각 서비스 확인
# - Qdrant: http://qdrant-service:6333/health
# - Ollama: http://ollama-service:11434/api/tags
```

---

## 📝 API 문서 (Swagger UI)

서버 실행 후 다음 URL에서 대화형 API 문서 확인 가능:

```
http://localhost:8000/docs
```

또는 ReDoc 형식:

```
http://localhost:8000/redoc
```

---

## 🔒 보안 주의사항

- API는 현재 CORS가 모두 열려있음 (개발 전용)
- 프로덕션 환경에서는 CORS 제한 필요
- 대용량 파일 업로드 시 메모리 주의
- 민감한 정보를 포함한 PDF는 신중히 취급

---

## 📈 성능 팁

1. **청킹 최적화**: 청크 크기를 조정하여 검색 성능 개선
2. **임베딩 캐싱**: 같은 텍스트의 임베딩 재사용
3. **배치 처리**: 여러 문서 한번에 업로드 전에 큐 시스템 고려
4. **모델 선택**: 더 작은 LLM 모델 사용 시 응답 속도 향상

---

## 🆘 트러블슈팅

### Q: "관련 문서를 찾을 수 없습니다" 메시지
**A**: 먼저 문서를 업로드했는지 확인. `/documents` 엔드포인트로 저장된 문서 확인

### Q: Ollama 모델이 로드되지 않음
**A**: `ollama pull gemma2:2b` 명령으로 모델 다운로드 필요 (수 GB 용량)

### Q: 응답이 느림
**A**: Ollama 모델 크기를 확인하고 필요시 더 작은 모델로 변경

### Q: PDF 텍스트 추출이 안됨
**A**: 스캔된 이미지 PDF의 경우 OCR 필요 (현재 미지원)
