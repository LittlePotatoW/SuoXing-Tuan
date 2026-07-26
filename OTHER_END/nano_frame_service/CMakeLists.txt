cmake_minimum_required(VERSION 3.0.2)
project(astra_data_collector)

find_package(catkin REQUIRED COMPONENTS
  rospy
  sensor_msgs
  cv_bridge
  message_filters
  std_msgs
)

catkin_package()

install(DIRECTORY launch scripts config
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
