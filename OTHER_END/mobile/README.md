# mobile/ — 途安 App 移动端

基于 **uni-app (Vue 3 + TypeScript)** 的移动端应用，一套源码同时产出微信小程序和 Android APK。

## 目录说明

```
mobile/
├── README.md                  # 本文件
├── tuan-app/                  # uni-app 跨平台源码（开发在此修改）
│   ├── src/                   #   页面 / 组件 / 工具 / 状态管理
│   ├── package.json           #   构建脚本：npm run build:mp-weixin / build:app
│   ├── vite.config.ts         #   Vite + @dcloudio/vite-plugin-uni
│   └── tsconfig.json
├── mp-weixin/                 # 微信小程序构建产物（导入微信开发者工具即可运行）
│   ├── app.js / app.json / app.wxss
│   ├── pages/ / components/ / utils/
│   └── project.config.json
└── app-android/               # Android App 资源包（配合 HBuilderX 云打包生成 APK）
    ├── app-service.js / app-config.js
    ├── manifest.json
    └── pages/ / static/
```

## 开发流程

### 前置条件

```bash
cd mobile/tuan-app
npm install
```

### 日常开发

```
修改源码 (mobile/tuan-app/src/)
         │
         ├──→ npm run build:mp-weixin → 复制到 mp-weixin/  → 微信开发者工具预览
         │
         └──→ npm run build:app       → 复制到 app-android/ → HBuilderX 云打包 → APK
```

### 构建命令

| 命令 | 产出 |
|---|---|
| `npm run build:mp-weixin` | `dist/build/mp-weixin/` |
| `npm run build:app` | `dist/build/app/` |
| `npm run dev:mp-weixin` | 开发模式（热更新） |

### 同步构建产物

```bash
# 从 tuan-app 目录执行
rm -rf ../mp-weixin/* && cp -r dist/build/mp-weixin/* ../mp-weixin/
rm -rf ../app-android/* && cp -r dist/build/app/* ../app-android/
```

## 技术栈

| 层级 | 技术 |
|---|---|
| 框架 | uni-app 3.x (Vue 3 Composition API + TypeScript) |
| 构建 | Vite 5 + @dcloudio/vite-plugin-uni |
| 样式 | SCSS（全局变量系统 uni.scss） |
| 状态管理 | reactive() 模块级单例 |
| 通信 | WebSocket (JSON 协议) |
| 地图 | 腾讯地图（微信小程序原生 map 组件） |

## 对接后端

- **WebSocket**：`robotSocket.ts` 连接中转服务器，格式见 `docs/API参考/` 中的 ctrl/loc/tele 协议
- **REST API**：预留 `// TODO` 注释位置，需对接 FastAPI 后端（../backend/）

## UI 资源

`tuan-app/src/static/` 目录未纳入版本控制（包含 logo、图标、插图等 UI 素材）。
需要时从设计源文件补充，文件清单见 `tuan-app/src/pages/` 中各页面 `<image src="/static/...">` 引用。
