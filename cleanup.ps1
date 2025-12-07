# 정리 스크립트 (PowerShell)
# K8S RAG 시스템의 모든 리소스를 삭제합니다

Write-Host "=== K8S RAG 시스템 정리 ===" -ForegroundColor Yellow

# 확인
$confirm = Read-Host "모든 리소스를 삭제하시겠습니까? (y/n)"
if ($confirm -ne "y") {
    Write-Host "취소되었습니다." -ForegroundColor Red
    exit
}

# 리소스 삭제
Write-Host "`n리소스 삭제 중..." -ForegroundColor Yellow

kubectl delete -f k8s/api-server-deployment.yaml --ignore-not-found
kubectl delete -f k8s/ollama-deployment.yaml --ignore-not-found
kubectl delete -f k8s/qdrant-deployment.yaml --ignore-not-found
kubectl delete -f k8s/configmap.yaml --ignore-not-found
kubectl delete -f k8s/namespace.yaml --ignore-not-found

Write-Host "`n=== 정리 완료 ===" -ForegroundColor Green
