# LAAP-SYNC v1.0 — 同步协议

## 概述
基于 CRDT 的跨端状态同步协议，支持离线操作和冲突自动解决。

## 核心数据结构
- **VersionVector**: 版本向量追踪
- **CRDTDocument**: 无冲突合并文档
- **SyncOp**: 同步操作单元

## 同步策略
1. LWW (Last-Write-Wins)
2. MVCC (多版本并发控制)
3. CRDT Merge
4. Custom Resolver
