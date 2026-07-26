# stm32_chassis_control/ — 小车底盘 & 机械臂控制固件

**STM32F103** (Keil MDK) 阿克曼底盘 + 机械臂控制固件，支持 PS2 手柄遥控和 ESP8266 WiFi 通信。

## 三方依赖 (不入 git, 需自行下载)

| 依赖 | 目录 | 来源 |
|------|------|------|
| STM32F10x 标准外设库 | `Library/` | [ST SW-STM32054](https://www.st.com/en/embedded-software/stsw-stm32054.html) |
| CMSIS Core + 启动文件 | `Start/` | STM32F10x StdPeriph 包内 `Libraries/CMSIS/` |
| 正点原子 系统代码 | `System/sys/` `System/Delay.*` | [正点原子 Mini STM32 例程](http://www.openedv.com/) |

下载后将对应文件放入上述目录，工程即可编译。

## 硬件模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 电机驱动 | `Hardware/Motor.c/h` | PWM 电机控制 |
| 编码器 | `Hardware/encoder.c/h` | 轮速里程计采集 |
| PID 控制 | `Hardware/compute_pid.c/h` | 速度闭环 |
| PS2 手柄 | `Hardware/ps2.c/h` | 2.4G 无线遥控接收 |
| 舵机 | `Hardware/Servo.c/h` | 机械臂关节控制 |
| 底盘 | `Hardware/Vehicle_Chassis.c/h` | 阿克曼运动学解算 |
| WiFi | `Hardware/ESP8266.c/h` | 网络通信 |
| 传感器 | `Hardware/Sensor.c/h` | 外接传感器读取 |

## 编译

1. 按上方表格补齐三方依赖到对应目录
2. Keil MDK-ARM 中新建工程，芯片选 STM32F103C8 / STM32F103RC
3. 将 `Hardware/`、`User/`、`System/Timer.c/h` 加入工程
4. 编译下载
