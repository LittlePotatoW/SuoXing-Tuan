# Frontend — Electron + Vue 3 桌面应用

## 这个文件夹是干啥的？

这里是你实际看到的桌面软件界面，负责：
- 显示工业相机的实时画面
- 在图片上画框标注缺陷位置
- 用 WebGL/WebGPU 渲染三维模型，可以旋转缩放
- 显示硬件状态监控面板（CPU、GPU、相机连接状态）
- 支持加载本地数据包离线回放（不用连后端也能看）

## 目录说明

| 目录 | 干啥的 |
|------|--------|
| `electron/` | Electron 主进程——管理窗口、系统托盘、和操作系统的交互 |
| `src/` | Vue 3 渲染进程——你看到的界面都在这里 |

`src/` 里面按照 Vue 3 的惯例组织：
- `components/` — 放 UI 组件（按钮、面板等）
- `composables/` — 放可复用的逻辑（比如 API 请求封装）
- `stores/` — 放全局状态（Pinia 状态管理）
- 等等（开发时再具体建）

## 技术栈

| 技术 | 用途 | 官方文档 |
|------|------|----------|
| **TypeScript** | 带类型检查的 JavaScript | https://www.typescriptlang.org/zh/docs/ |
| **Vue 3** | 前端 UI 框架 | https://cn.vuejs.org/guide/ |
| **Vite** | 构建工具（开发服务器飞快） | https://cn.vitejs.dev/guide/ |
| **Electron** | 把网页打包成桌面应用 | https://www.electronjs.org/zh/docs/latest/ |
| **Pinia** | Vue 3 官方状态管理 | https://pinia.vuejs.org/zh/ |
| **Vue Router** | 前端路由（页面跳转） | https://router.vuejs.org/zh/ |
| **Three.js** | 三维渲染库（WebGL 封装） | https://threejs.org/docs/ |


## 怎么学？（推荐学习路线）

1. **HTML/CSS/JS 基础** — 如果没写过前端，先过一遍
   - 教程：https://developer.mozilla.org/zh-CN/docs/Learn

2. **TypeScript 入门** — JS + 类型，写大项目更稳
   - 教程：https://www.typescriptlang.org/zh/docs/handbook/tsconfig-json.html
   - 先看"基础类型"和"接口"两章就够用

3. **Vue 3 官方教程** — 花一天跟着做一遍
   - 教程：https://cn.vuejs.org/tutorial/
   - 重点看：组件、响应式数据、computed、组合式 API

4. **Vite + Vue 3 脚手架** — 自己搭个项目试试
   - 教程：https://cn.vitejs.dev/guide/#scaffolding-your-first-vite-project

5. **Electron 入门** — 把你的 Vue 网页变成桌面应用
   - 教程：https://www.electronjs.org/zh/docs/latest/tutorial/
   - 推荐用 electron-vite 脚手架：https://electron-vite.org/

6. **Three.js** — 三维渲染（用到再学）
   - 教程：https://threejs.org/manual/#zh/

## 怎么跑起来？

```bash
cd frontend
npm install                   # 装依赖
npm run dev                   # 启动开发服务器（浏览器访问）
npm run electron:dev          # 启动 Electron 桌面窗口
```

## 参考设计

前端用了 **Electron + Vue 3** 的组合：
- Electron 负责"桌面壳子"（窗口、菜单、托盘、本地文件读写）
- Vue 3 负责"壳子里面的界面"
- 两者通过 IPC（进程间通信）安全交互

为什么选 Electron 而不是纯网页？
- 需要访问本地文件系统（加载数据包）
- 需要稳定的大屏展示（不依赖浏览器）
- 可以调用系统级 API（比如 USB 设备检测）

界面布局参考了典型的"工业检测上位机"设计：左侧图像面板 + 右侧检测结果 + 底部硬件状态栏，可拖拽调整大小。
