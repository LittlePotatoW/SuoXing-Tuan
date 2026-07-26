#include "stm32f10x.h"                  // Device header
#include "Motor.h"

#define MOTOR_DEAD	50
void Motor_Init()
{
	//tim2 初始化
	RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2,ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA,ENABLE);
	
	GPIO_InitTypeDef GPIO_InitStructure;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0|GPIO_Pin_1|GPIO_Pin_2|GPIO_Pin_3;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init(GPIOA,&GPIO_InitStructure);
	
	TIM_InternalClockConfig(TIM2);
	TIM_TimeBaseInitTypeDef TIM_TimeBaseInitStructure;
	TIM_TimeBaseInitStructure.TIM_ClockDivision = TIM_CKD_DIV1;
	TIM_TimeBaseInitStructure.TIM_CounterMode = TIM_CounterMode_Up;
	TIM_TimeBaseInitStructure.TIM_Period = 1000-1;
	TIM_TimeBaseInitStructure.TIM_Prescaler = 720-1;
	TIM_TimeBaseInitStructure.TIM_RepetitionCounter = 0;
	TIM_TimeBaseInit(TIM2,&TIM_TimeBaseInitStructure);
	
	TIM_OCInitTypeDef TIM_OCInitStructure;
	TIM_OCStructInit(&TIM_OCInitStructure);
	TIM_OCInitStructure.TIM_OCMode = TIM_OCMode_PWM1;
	TIM_OCInitStructure.TIM_OCPolarity = TIM_OCPolarity_High;
	TIM_OCInitStructure.TIM_OutputState = TIM_OutputState_Enable;
	TIM_OCInitStructure.TIM_Pulse =0;    //CCR
	TIM_OC1Init(TIM2,&TIM_OCInitStructure);
	TIM_OC2Init(TIM2,&TIM_OCInitStructure);
	TIM_OC3Init(TIM2,&TIM_OCInitStructure);
	TIM_OC4Init(TIM2,&TIM_OCInitStructure);
	
	TIM_Cmd(TIM2,ENABLE);
}

void Car_Stop()
{
	Motor1_SetSpeed(1,0);
	Motor2_SetSpeed(1,0);	
}

void Car_Forward(uint16_t Speed)
{
	Motor1_SetSpeed(1,Speed);
	Motor2_SetSpeed(1,Speed);

}

void Car_Backward(uint16_t Speed)
{
	Motor1_SetSpeed(0,Speed);
	Motor2_SetSpeed(0,Speed);
}

void Car_TurnLeft(uint16_t Speed)
{
	Motor1_SetSpeed(0,Speed);
	Motor2_SetSpeed(1,Speed);
}

void Car_TurnRight(uint16_t Speed)
{
	Motor1_SetSpeed(1,Speed);
	Motor2_SetSpeed(0,Speed);
}

void Car_TransLeft(uint16_t Speed)
{
	Motor1_SetSpeed(1,Speed);
	Motor2_SetSpeed(0,Speed);
}

void Car_TransRight(uint16_t Speed)
{
	Motor1_SetSpeed(0,Speed);
	Motor2_SetSpeed(1,Speed);
}

/*****************************************************/
//  PA0->TIM2_CH1->MOTOR1A->Backward
//  PA1->TIM2_CH2->MOTOR1B->Forward
//motor1 正转方向为视觉上的反转 即Dir = 0;
void Motor1_SetSpeed(uint8_t Dir, uint16_t Speed)
{
	if (Speed>=1000) Speed = 1000;
	if (Speed <= MOTOR_DEAD) Speed = 0;	
	if (Dir)
	{
		TIM_SetCompare2(TIM2,0);
		TIM_SetCompare1(TIM2,Speed);	
	}
	else if (!Dir)
	{
		TIM_SetCompare1(TIM2,0);
		TIM_SetCompare2(TIM2,Speed);
	}
}

//  PA2->TIM2_CH3->MOTOR2A->Backward
//  PA3->TIM2_CH4->MOTOR2B->Forward
// motor2 正转方向为视觉上的正转 即DIR = 1；
void Motor2_SetSpeed(uint8_t Dir, uint16_t Speed)
{
	if (Speed>=1000) Speed = 1000;
	if (Speed <= MOTOR_DEAD) Speed = 0;
	if (Dir)
	{
		TIM_SetCompare3(TIM2,0);
		TIM_SetCompare4(TIM2,Speed);		
	}
	else if (!Dir)
	{
		TIM_SetCompare4(TIM2,0);
		TIM_SetCompare3(TIM2,Speed);		
	}
}

