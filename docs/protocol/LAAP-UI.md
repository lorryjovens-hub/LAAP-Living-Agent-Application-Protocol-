# LAAP-UI v1.0 — 渲染协议

## 概述
LAAP-UI 定义了数字生命体的跨端渲染标准。采用声明式布局模型。

## 核心概念
- **LayoutTree**: 组件树结构
- **Component**: 基础UI组件 (Text/Button/Progress/Chart等)
- **RenderCommand**: 差分更新指令
- **ThemeDefinition**: 主题定义

## 组件类型
Container, Text, Image, Button, Input, Progress, Chart, List, Form, Table, Modal, StatusBar, Panel, TabView, Tree

## 渲染流程
1. 构建 LayoutTree
2. 计算 Diff (新旧布局)
3. 生成 RenderCommand 序列
4. 按平台执行渲染
