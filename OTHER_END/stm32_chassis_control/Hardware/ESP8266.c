#include "stm32f10x.h"
#include "LED.h"
#include "Usart.h"
#include "Delay.h"

/*
 * ESP8266 AT命令: AP模式 + TCP服务器
 * 兼容旧版AT固件: 用CWSAP替代CWSAP_DEF, 加密类型改为WPA2
 */
char dat1[]="AT+RST\r\n",\
     dat2[]="AT+CWMODE=2\r\n",\
     dat3[]="AT+CWSAP=\"ESP8266AP_test\",\"12345678\",1,4\r\n",\
     dat4[]="AT+CIPMUX=1\r\n",\
     dat5[]="AT+CIPSERVER=1,8080\r\n";

void ESP8266_Init()
{
	Usart1_SendString(dat1);
	Delay_ms(1000);        // AT+RST需要更长时间重启
	Usart1_SendString(dat2);
	Delay_ms(200);
	Usart1_SendString(dat3);
	Delay_ms(200);
	Usart1_SendString(dat4);
	Delay_ms(200);
	Usart1_SendString(dat5);
	Delay_ms(200);

	LED_ON();
}
