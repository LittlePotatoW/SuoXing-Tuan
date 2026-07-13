#pragma once
#include <memory>
#include <nlohmann/json.hpp>
#include "room.h"

using json = nlohmann::json;

void handle_phone_msg(std::shared_ptr<Room> room, const std::string& peer_id,
                      const json& msg);
void handle_robot_msg(std::shared_ptr<Room> room, const json& msg);

void on_phone_connect(std::shared_ptr<Room> room, const std::string& peer_id,
                      const std::string& room_id);
void on_robot_connect(const std::string& room_id);

void on_phone_disconnect(std::shared_ptr<Room> room, const std::string& peer_id);
void on_robot_disconnect(std::shared_ptr<Room> room);
