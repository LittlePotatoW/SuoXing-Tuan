# android_remote/ — 途安遥控 Android APP

**Kotlin / Android Studio** 原生 Android 应用，通过 WiFi 连接小车，进行遥控操作。

## 构建

1. 生成 Gradle Wrapper（如需）：`gradle wrapper`（Gradle 文件不入 git）
2. Android Studio 打开本目录，同步依赖
3. `Build → Build APK` 生成安装包

## 三方依赖

| 依赖 | 说明 |
|------|------|
| Gradle Wrapper | `gradlew` / `gradle/wrapper/` — 运行 `gradle wrapper` 生成 |
| Kotlin / Compose / OkHttp 等 | 由 `gradle/libs.versions.toml` 声明，Gradle 自动下载 |

## 架构

```
APP ──WiFi──→ 小车 (ESP8266 / Nano)
```

发送控制指令（前进、转向、机械臂等），接收小车状态回传。
