# K8s 部署指南

## 前提
- Kubernetes 1.20+
- kubectl 已配置

## 部署步骤
```bash
kubectl apply -f k8s/laap-configmap.yaml
kubectl apply -f k8s/laap-deployment.yaml
kubectl apply -f k8s/laap-service.yaml
kubectl apply -f k8s/laap-hpa.yaml
```

## 配置
通过 ConfigMap 管理 LAAP 配置。
