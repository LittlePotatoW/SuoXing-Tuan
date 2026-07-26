#ifndef _VEHICLE_CHASSIS_H_
#define _VEHICLE_CHASSIS_H_

void Vehicle_Chassis_Init(void);
void Vehicle_Motor1_TargetEC_Set(int target_val);
void Vehicle_Motor2_TargetEC_Set(int target_val);
void Vehicle_Motor3_TargetEC_Set(int target_val);
void Vehicle_Motor4_TargetEC_Set(int target_val);
/******************************************/
void Vehicle_Chassis_Run(void);
void Vehicle_Chassis_Tim_Init(void);

#endif

