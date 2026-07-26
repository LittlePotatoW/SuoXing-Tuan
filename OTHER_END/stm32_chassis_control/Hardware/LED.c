#include "stm32f10x.h"
#include "Delay.h"

void LED_Init()
{
	GPIO_InitTypeDef GPIO_InitStructure;
	
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOD,ENABLE);
	
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_2;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
	GPIO_Init(GPIOD,&GPIO_InitStructure);
}

void LED_OFF()
{
	//GPIO_WriteBit(GPIOA,GPIO_Pin_8,Bit_RESET);	
	GPIO_ResetBits(GPIOD,GPIO_Pin_2);
}

void LED_ON()
{
	//GPIO_WriteBit(GPIOA,GPIO_Pin_8,Bit_SET);	
	GPIO_SetBits(GPIOD,GPIO_Pin_2);
}


void LED_Turn()
{
	if(GPIO_ReadOutputDataBit(GPIOD,GPIO_Pin_2)==0)
	{
		GPIO_WriteBit(GPIOD,GPIO_Pin_2,Bit_SET);
	}
	else
	{
		GPIO_WriteBit(GPIOD,GPIO_Pin_2,Bit_RESET);
	}
}
