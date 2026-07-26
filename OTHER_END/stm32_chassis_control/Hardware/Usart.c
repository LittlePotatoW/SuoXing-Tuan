#include "stm32f10x.h"                  // Device header
#include "Usart.h"

#pragma import(__use_no_semihosting)

#include <stdio.h>

struct __FILE
{
	int handle;
};

FILE __stdout;
FILE __stdin;

int fputc(int ch, FILE *f)
{
	Usart1_SendByte(ch);
	return ch;
}

void _sys_exit(int x)
{
	x = x;
}

/* 逐字符命令检测 — 遇到 : 开始收集, 遇 \r 立即处理, 不等换行 */
#define CMD_MAX 32
volatile uint8_t cmd_ready = 0;    // 命令就绪, main 循环处理
char     cmd_buf[CMD_MAX];

void Usart1_Init()
{
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_USART1,ENABLE);
	RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA,ENABLE);

	//tx
	GPIO_InitTypeDef	GPIO_InitStructure;
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_9;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init(GPIOA,&GPIO_InitStructure);

	//rx
	GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
	GPIO_InitStructure.GPIO_Pin = GPIO_Pin_10;
	GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
	GPIO_Init(GPIOA,&GPIO_InitStructure);

	USART_InitTypeDef	USART_InitStructure;
	USART_InitStructure.USART_BaudRate = 115200;
	USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
	USART_InitStructure.USART_Mode = USART_Mode_Tx|USART_Mode_Rx;
	USART_InitStructure.USART_Parity = USART_Parity_No;
	USART_InitStructure.USART_StopBits = USART_StopBits_1;
	USART_InitStructure.USART_WordLength = USART_WordLength_8b;
	USART_Init(USART1,&USART_InitStructure);

	USART_ITConfig(USART1,USART_IT_RXNE,ENABLE);

	NVIC_InitTypeDef	NVIC_InitStructure;
	NVIC_InitStructure.NVIC_IRQChannel = USART1_IRQn;
	NVIC_InitStructure.NVIC_IRQChannelCmd = ENABLE;
	NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority =1;
	NVIC_InitStructure.NVIC_IRQChannelSubPriority =1;
	NVIC_Init(&NVIC_InitStructure);

	USART_Cmd(USART1,ENABLE);
}

void Usart1_SendByte(uint8_t Byte)
{
	USART_SendData(USART1,Byte);
	while(USART_GetFlagStatus(USART1,USART_FLAG_TXE) == RESET);
}

void Usart1_SendArray(uint8_t *Array,uint16_t Length)
{
	uint16_t i;
	for (i = 0; i < Length; i++)
	{
		Usart1_SendByte(Array[i]);
	}
}

void Usart1_SendString(char *String)
{
	uint8_t i;
	for(i = 0; String[i] != '\0';i++)
	{
		Usart1_SendByte(String[i]);
	}
}

uint32_t Usart1_Pow(uint32_t X, uint32_t Y)
{
	uint32_t Result = 1;
	while (Y--)
	{
		Result *= X;
	}
	return Result;
}

void Usart1_SendNum(uint32_t Number, uint8_t Length)
{
	uint8_t i;
	for (i = 0; i < Length; i++)
	{
		Usart1_SendByte(Number / Usart1_Pow(10, Length - i - 1) % 10 + '0');
	}
}

/*
 * 逐字符状态机: +IPD,0,N:cmd\r\n → 检测到 ':' 后收集命令, 遇 '\r' 立即就绪
 * 收到即处理, 不等待换行, 延迟 <1ms
 */
void USART1_IRQHandler()
{
	static uint8_t state = 0;    // 0=等待':', 1=收集命令
	static uint8_t idx  = 0;

	if (USART_GetFlagStatus(USART1, USART_FLAG_RXNE) == SET)
	{
		char c = USART_ReceiveData(USART1);

		if (state == 0) {
			if (c == ':') { state = 1; idx = 0; }
		} else {
			if (c == '\r' || idx >= CMD_MAX - 1) {
				cmd_buf[idx] = '\0';
				cmd_ready = 1;       // 通知 main 处理
				state = 0;
			} else if (c != '\n') {
				cmd_buf[idx++] = c;
			}
		}
		USART_ClearITPendingBit(USART1, USART_FLAG_RXNE);
	}
}
