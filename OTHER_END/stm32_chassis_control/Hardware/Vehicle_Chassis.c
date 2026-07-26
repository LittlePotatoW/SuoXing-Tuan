#include "stm32f10x.h"                  // Device header
#include "Vehicle_chassis.h"
#include "Encoder.h"
#include "compute_pid.h"
#include "Motor.h"
#include "Usart.h"

#define  EC_MAX		115    //电机最快转速检测到的编码器脉冲数（周期为25ms）

PID Motor1_pid = {10.5f, 0.52f, 0, 0, 0, 0, 0, 0};
PID Motor2_pid = {10.5f, 0.52f, 0, 0, 0, 0, 0, 0};

//4个编码器目标值变量
int target_EC1 = 0, target_EC2 = 0;

void Vehicle_Chassis_Init()
{
	Usart1_Init();
	Motor_Init();
	Encoder_Init();
	Vehicle_Motor1_TargetEC_Set(0);
	Vehicle_Motor2_TargetEC_Set(0);
}

void Vehicle_Motor1_TargetEC_Set(int target_val)
{
	//编码器目标值限幅
	target_val = target_val > EC_MAX?  EC_MAX : target_val;
	target_val = target_val < -EC_MAX?  -EC_MAX : target_val;
	
	target_EC1 = target_val;
}

void Vehicle_Motor2_TargetEC_Set(int target_val)
{
	//编码器目标值限幅
	target_val = target_val > EC_MAX?  EC_MAX : target_val;
	target_val = target_val < -EC_MAX?  -EC_MAX : target_val;
	
	target_EC2 = target_val;
}

/************************************************************/
void Vehicle_Chassis_Run()
{
	int EC1 = 0, EC2 = 0;
	int M1_Pwm = 0, M2_Pwm = 0;
	Encoder_Updata();
	EC1 = Encoder1_Count_Get();
	EC2 = Encoder2_Count_Get();
  //  printf("%d,%d\n", 80,EC1);
	M1_Pwm = Increment_PID_CloseLoop(&Motor1_pid,EC1,target_EC1);
	M2_Pwm = Increment_PID_CloseLoop(&Motor2_pid,EC2,target_EC2);

	M1_Pwm >= 0? Motor1_SetSpeed(0,M1_Pwm):Motor1_SetSpeed(1,0-M1_Pwm);
	M2_Pwm >= 0? Motor2_SetSpeed(1,M2_Pwm):Motor2_SetSpeed(0,0-M2_Pwm);

}

