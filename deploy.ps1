# 배포 스크립트 (PowerShell)
# K8S RAG 시스템을 순서대로 배포합니다

Write-Host "=== K8S RAG 시스템 배포 시작 ===" -ForegroundColor Green

# 네임스페이스 생성
Write-Host "`n[1/5] 네임스페이스 생성..." -ForegroundColor Yellow
kubectl apply -f k8s/namespace.yaml

# ConfigMap 배포
Write-Host "`n[2/5] ConfigMap 배포..." -ForegroundColor Yellow
kubectl apply -f k8s/configmap.yaml

# Qdrant 배포
Write-Host "`n[3/5] Qdrant 배포..." -ForegroundColor Yellow
kubectl apply -f k8s/qdrant-deployment.yaml

# Qdrant 준비 대기
Write-Host "Qdrant Pod 준비 대기 중..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=qdrant -n rag-system --timeout=120s

# Ollama 배포
Write-Host "`n[4/5] Ollama 배포..." -ForegroundColor Yellow
kubectl apply -f k8s/ollama-deployment.yaml

# Ollama 준비 대기 (모델 다운로드로 시간이 오래 걸림)
Write-Host "Ollama Pod 준비 대기 중 (모델 다운로드에 시간이 걸릴 수 있습니다)..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=ollama -n rag-system --timeout=600s

# API Server 배포
Write-Host "`n[5/5] API Server 배포..." -ForegroundColor Yellow
kubectl apply -f k8s/api-server-deployment.yaml

# API Server 준비 대기
Write-Host "API Server Pod 준비 대기 중..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=rag-api-server -n rag-system --timeout=180s

# 상태 확인
Write-Host "`n=== 배포 완료 ===" -ForegroundColor Green
Write-Host "`n현재 Pod 상태:" -ForegroundColor Yellow
kubectl get pods -n rag-system

Write-Host "`n서비스 상태:" -ForegroundColor Yellow
kubectl get svc -n rag-system

Write-Host "`n=== 접속 정보 ===" -ForegroundColor Green
Write-Host "API 문서: http://localhost:30080/docs" -ForegroundColor Cyan
Write-Host "헬스체크: http://localhost:30080/health" -ForegroundColor Cyan
