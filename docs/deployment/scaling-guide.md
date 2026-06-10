# 弹性伸缩指南

## 水平伸缩 (HPA)
基于 CPU/内存/自定义指标自动扩缩容。

## 预测性伸缩
基于历史负载模式预测未来需求。

## 伸缩策略
- CPU > 70% → scale up
- Memory > 80% → scale up
- Request latency > 500ms → scale up
- Idle for 10min → scale down
