#include "stm32f10x.h"

void Buzzer_Init()
{
	GPIO_InitTypeDef GPIO_InitStructure;
	
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC,ENABLE);
	
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_12;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
	GPIO_Init(GPIOC,&GPIO_InitStructure);
}

void Buzzer_OFF()
{	
	GPIO_SetBits(GPIOC,GPIO_Pin_12);
}

void Buzzer_ON()
{
	GPIO_ResetBits(GPIOC,GPIO_Pin_12);
}

