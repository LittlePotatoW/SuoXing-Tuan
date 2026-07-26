#ifndef _USART_H_
#define _USART_H_

#include <stdio.h>

/* 逐字符命令检测: USART ISR 遇到 \r 立即置位 */
#define CMD_MAX 32
extern volatile uint8_t cmd_ready;
extern char     cmd_buf[CMD_MAX];

void Usart1_Init(void);
void Usart1_SendByte(uint8_t Byte);
void Usart1_SendArray(uint8_t *Array,uint16_t Length);
void Usart1_SendString(char *String);
void Usart1_SendNum(uint32_t Number, uint8_t Length);
#endif
