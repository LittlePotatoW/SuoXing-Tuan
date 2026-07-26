#include "stm32f10x.h"
#include "Delay.h"
#include "Servo.h"
#include "LED.h"
#include "Vehicle_Chassis.h"
#include "Buzzer.h"
#include "Usart.h"
#include "ESP8266.h"
#include <string.h>

#define  SPEED       80
#define  SPEED_SLOW  20       // 检测模式: 约1转/秒
#define  RAMP        12
#define  RAMP_SLOW   4        // 检测模式软加速更平缓
#define  STEER_MID   150
#define  STEER_L     120
#define  STEER_R     190
#define  TRIM_MAX    20
#define  TIMEOUT     80

int16_t M1_Req, M2_Req;
int16_t M1_Actual, M2_Actual;
int16_t steer_base = STEER_MID;
int16_t steer_trim = 0;
uint8_t  Time;
uint8_t  detect_mode = 0;       // 0=正常, 1=检测(低速)
int16_t  speed_now = SPEED;     // 当前限速
int16_t  ramp_now  = RAMP;      // 当前软加速步长
uint16_t motor_to, steer_to;

/* 软加速: 每周期向目标逼近一步, 步长可变 */
static void ramp(int16_t *cur, int16_t tgt) {
	int16_t step = ramp_now;
	if      (*cur < tgt) { *cur += step; if (*cur > tgt) *cur = tgt; }
	else if (*cur > tgt) { *cur -= step; if (*cur < tgt) *cur = tgt; }
}

/* 舵机输出(含微调) */
static void steer_out(int16_t base) {
	steer_base = base;
	int16_t v = base + steer_trim;
	if      (v < STEER_L - TRIM_MAX) v = STEER_L - TRIM_MAX;
	else if (v > STEER_R + TRIM_MAX) v = STEER_R + TRIM_MAX;
	Arc_ServoPwm_Set(v);
}

int main(void)
{
	Delay_ms(100);
	Buzzer_Init();
	Buzzer_ON();  Delay_ms(200);
	Buzzer_OFF(); Delay_ms(100);

	__disable_irq();
	NVIC_PriorityGroupConfig(NVIC_PriorityGroup_2);
	LED_Init(); Servo_Init(); Vehicle_Chassis_Init();
	Arc_Servo_Reset(); Robot_Arm_Reset();
	ESP8266_Init();

	Buzzer_ON();  Delay_ms(100);
	Buzzer_OFF(); Delay_ms(100);
	Buzzer_ON();  Delay_ms(100);
	Buzzer_OFF();

	SysTick_Configuration(5);
	__enable_irq();
	LED_ON();

	while (1)
	{
		if (SysTick_Timer_Inquire())
		{
			Time++;

			/* ---- 命令处理 (拷贝到本地buf防ISR覆盖) ---- */
			if (cmd_ready)
			{
				char  buf[CMD_MAX];
				uint8_t i;

				cmd_ready = 0;
				LED_Turn();

				USART_ITConfig(USART1, USART_IT_RXNE, DISABLE);
				for (i = 0; i < CMD_MAX; i++) { buf[i] = cmd_buf[i]; if (cmd_buf[i] == '\0') break; }
				buf[CMD_MAX - 1] = '\0';
				USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);

				/* 油门: m0=停电机 */
				if      (strstr(buf, "m0"))         { M1_Req = 0;  M2_Req = 0; }
				else if (strstr(buf, "stop"))       { M1_Req = 0;  M2_Req = 0;  steer_out(STEER_MID); motor_to = TIMEOUT; steer_to = TIMEOUT; }
				else if (strstr(buf, "up"))         { M1_Req = -speed_now; M2_Req = speed_now;  motor_to = 0; }
				else if (strstr(buf, "down"))       { M1_Req = speed_now;  M2_Req = -speed_now; motor_to = 0; }

				/* 转向: s0=舵机回中 */
				if      (strstr(buf, "s0"))         { steer_out(STEER_MID); }
				else if (strstr(buf, "left"))       { steer_out(STEER_L); steer_to = 0; }
				else if (strstr(buf, "right"))      { steer_out(STEER_R); steer_to = 0; }

				/* 舵机微调 */
				if      (strstr(buf, "trim_l")) { steer_trim -= 2; if (steer_trim < -TRIM_MAX) steer_trim = -TRIM_MAX; steer_out(steer_base); }
				else if (strstr(buf, "trim_r")) { steer_trim += 2; if (steer_trim >  TRIM_MAX) steer_trim =  TRIM_MAX; steer_out(steer_base); }
				else if (strstr(buf, "trim_0")) { steer_trim = 0; steer_out(steer_base); }

				/* 检测模式切换 */
				if      (strstr(buf, "slow")) { detect_mode = 1; speed_now = SPEED_SLOW; ramp_now = RAMP_SLOW; }
				else if (strstr(buf, "fast")) { detect_mode = 0; speed_now = SPEED;      ramp_now = RAMP; }
			}

			/* 超时保护 */
			motor_to++; steer_to++;
			if (motor_to > TIMEOUT) { M1_Req = 0; M2_Req = 0; }
			if (steer_to > TIMEOUT) { steer_out(STEER_MID); }

			/* PID底盘控制 (10ms) */
			if ((Time + 1) % 2 == 0)
			{
				ramp(&M1_Actual, M1_Req);
				ramp(&M2_Actual, M2_Req);

				Vehicle_Motor1_TargetEC_Set(M1_Actual);
				Vehicle_Motor2_TargetEC_Set(M2_Actual);
				Vehicle_Chassis_Run();
			}

			if ((Time + 1) % 200 == 0) Time = 0;
		}
	}
}
