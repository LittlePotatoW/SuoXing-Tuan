#ifndef _SERVO_H_
#define _SERVO_H_

typedef enum
{
	SERVO_MIDDLE = 0,
	SERVO_LEFT_LIMIT,
	SERVO_RIGHT_LIMIT,
}servo_limit;

struct SERVO_PARAM
{
	uint8_t pwm;
	uint8_t left_limit;
	uint8_t middle;
	uint8_t right_limit;
};

void Servo_Init(void);
void Arc_Servo_Reset(void);
void Arc_ServoPwm_Set(uint16_t value);
void Arc_ServoPwm_TurnLeft(uint8_t unit_pwm);
void Arc_ServoPwm_TurnRight(uint8_t unit_pwm);
void Robot_Arm_Reset(void);
void RobotArm_RaiseHand(uint8_t unit_pwm);
void RobotArm_DropHand(uint8_t unit_pwm);
void RobotArm_StretchHand(uint8_t unit_pwm);
void RobotArm_ShrinkHand(uint8_t unit_pwm);
void RobotArm_ShakeHand(uint8_t unit_pwm);
void RobotArm_LetHand(uint8_t unit_pwm);
void RobotArm_PtzLeft(uint8_t unit_pwm);
void RobotArm_PtzRight(uint8_t unit_pwm);

/*******************************************/
void Servo_Gpio_Init(void);
void Servo_Time_Init(void);
void Robot_Arm_Gpio_Init(void);

void Robot_LeftPwm_Set(uint16_t value);
void Robot_UpPwm_Set(uint16_t value);
void Robot_RightPwm_Set(uint16_t value);
void Robot_PtzPwm_Set(uint16_t value);
#endif

