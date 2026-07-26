#include "compute_pid.h"
#include "math.h"
/**
  * @brief  增量式PID
  * @param  actual_val:实际值
  *	@note 	无
  * @retval 通过PID计算后的输出
  */
int Increment_PID_CloseLoop(PID *pid, int actual_val, int target_val)
{
	float Proportional, Integral, Derivative;
	
	/*计算目标值与实际值的误差*/
	pid->err = target_val - actual_val;
	
	Proportional = pid->Kp * (pid->err - pid->err_pre);
	
	Integral = pid->Ki * pid->err;
//	Integral = Integral > 1000? 1000 : Integral;
//	Integral = Integral < -1000? -1000 : Integral;	
	
	Derivative = pid->Kd * (pid->err - 2 * pid->err_pre + pid->err_last);
	
	/*PID算法实现*/
	pid->output = pid->output_last + Proportional + Integral + Derivative;
	pid->output = pid->output > 1000? 1000 : pid->output;
	pid->output = pid->output < -1000? -1000 : pid->output;
	
	pid->output_last = pid->output;
	pid->err_last = pid->err_pre;
	pid->err_pre = pid->err;
	
	/*返回当前实际值*/
	return pid->output;
}
