# TranspondServer C++ 实现

## 技术栈

C++17 + cpp-httplib (HTTP/WebSocket) + nlohmann/json (JSON)

## 文件架构

```
Transpond_Server/
├── CMakeLists.txt          # CMake 构建 (FetchContent 自动下载依赖)
├── .gitignore              # 忽略 /build
├── DESIGN.md / API.md      # 文档
├── store.h                 # 数据模型 + 环形缓冲区模板 (header-only)
├── handlers.h              # Handler 声明 + AppState
├── handlers.cpp            # HTTP 处理器实现 (6 个 handler)
└── main.cpp                # 入口 + CLI + 路由注册 + WebSocket
```

## 构建

```bash
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
./transpond-server --port 8001 --max-loc 2000 --max-sensor 200
```

产物: `build/transpond-server` (~200KB 单文件, 无运行时依赖)
