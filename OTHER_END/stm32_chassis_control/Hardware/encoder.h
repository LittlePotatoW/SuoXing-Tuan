#ifndef _ENCODER_H_
#define _ENCODER_H_

#define COUNT_SIZE 4

struct ENCODER
{
	uint8_t A;
	uint8_t B;
	int32_t PulseCount;
	int32_t Avg_PulseCount;
	uint8_t pFIFO;
	int32_t Count_FIFO[COUNT_SIZE];
};

void Encoder_Init(void);
int32_t Encoder1_Count_Get(void);
int32_t Encoder2_Count_Get(void);
void Encoder_Updata(void);
/**************************************************/
void Encoder_Gpio_Init(void);
void Encoder1_Updata(void);
void Encoder2_Updata(void);
void Encoder_Count_FIFO_Init(void);
void Encoder1_Count_FIFO_Updata(int32_t value);
void Encoder2_Count_FIFO_Updata(int32_t value);
void Encoder1_AvgPulseCount_Updata(void);
void Encoder2_AvgPulseCount_Updata(void);
#endif

