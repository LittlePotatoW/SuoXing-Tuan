Astra Pro 深度相机 — 小车端 WS 帧推送服务
=============================================

所需二进制文件 (因体积较大不入 git, 需自行下载):
  OpenNI2 运行时驱动 (OpenNI2.dll + Drivers/orbbec.dll):
    → 从奥比中光官方下载 "Astra Pro 上位机软件":
      https://www.orbbec.com/developers/astra-pro/
      解压后将 OpenNI2.dll、OpenNI.ini、OpenNI2/Drivers/ 放入本目录的 OpenNI2/ 下
  Windows 传感器驱动 (SensorDriver_V4.3.0.17.exe):
    → 同上链接, 在 上位机软件/Window 驱动/ 中获取
    → 或从奥比中光官网技术支持页面下载

文件:
  astra_vehicle_server.py      主服务 (深度采集 + WS推送)
  viewer.html                  可视化测试页面
  requirements.txt             Python 依赖清单
  OpenNI2/                     OpenNI2 运行时驱动 (需自行下载放入)
  SensorDriver_V4.3.0.17.exe  Windows 传感器驱动安装包 (需自行下载)

首次使用:
  1. 安装传感器驱动: 双击运行 SensorDriver_V4.3.0.17.exe
  2. 安装 Python 依赖: pip install -r requirements.txt
  3. 连接 Astra Pro 相机, 确保 OrbbecViewer.exe 未占用
  4. 启动: python astra_vehicle_server.py

前端连接: ws://<本机IP>:8002
可视化:   双击 viewer.html

协议:
  帧格式: {"type":"frame","timestamp":...,"image":"<base64 JPEG>","depth_map":"<base64 PNG>"}
  端口:   8002 (WebSocket)

配置:
  所有可调参数集中在 astra_vehicle_server.py 顶部配置区,
  包含网络、相机、性能、超时等约 40 个参数。
