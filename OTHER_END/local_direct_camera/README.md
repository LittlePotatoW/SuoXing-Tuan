# Astra Pro 本地直连相机包

USB 直连 Astra Pro 相机到电脑，启动帧采集服务，配合前端"本地直连"模式使用。

## 文件

| 文件 | 说明 |
|------|------|
| `astra_vehicle_server.py` | 帧采集 + WebSocket 推送 (127.0.0.1:8002) |
| `viewer.html` | 浏览器可视化预览 |
| `requirements.txt` | Python 依赖 |
| `OpenNI2/` | OpenNI2 运行时驱动 (需自行下载放入) |
| `SensorDriver_V4.3.0.17.exe` | Windows 传感器驱动安装包 (需自行下载) |

## 所需二进制文件

因体积较大不入 git，需从奥比中光官方下载：
- OpenNI2 运行时驱动 (OpenNI2.dll + Drivers/orbbec.dll)
  - 下载地址: https://www.orbbec.com/developers/astra-pro/
  - 解压"上位机软件"，将 OpenNI2.dll、OpenNI.ini、OpenNI2/Drivers/ 放入本目录的 OpenNI2/ 下
- Windows 传感器驱动 (SensorDriver_V4.3.0.17.exe)
  - 同上链接，在 上位机软件/Window 驱动/ 中获取

## 首次使用

1. 安装传感器驱动: 双击运行 `SensorDriver_V4.3.0.17.exe`
2. 安装 Python 依赖: `pip install -r requirements.txt`
3. 启动帧采集: `python astra_vehicle_server.py`
4. 前端切换到"本地直连"模式，点击连接

## 配置

所有可调参数集中在 `astra_vehicle_server.py` 顶部配置区。
