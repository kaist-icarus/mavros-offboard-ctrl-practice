#! /usr/bin/env python

import rospy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import State
from mavros_msgs.srv import CommandBool, CommandBoolRequest, SetMode, SetModeRequest

current_state = State()

def state_cb(msg):
    global current_state
    current_state = msg


if __name__ == "__main__":
    rospy.init_node("offb_node_py")

    state_sub = rospy.Subscriber("mavros/state", State, callback = state_cb)

    local_pos_pub = rospy.Publisher("mavros/setpoint_position/local", PoseStamped, queue_size=10)

    rospy.wait_for_service("/mavros/cmd/arming")
    arming_client = rospy.ServiceProxy("mavros/cmd/arming", CommandBool)

    rospy.wait_for_service("/mavros/set_mode")
    set_mode_client = rospy.ServiceProxy("mavros/set_mode", SetMode)


    # Setpoint publishing MUST be faster than 2Hz
    rate = rospy.Rate(20)

    # Wait for Flight Controller connection
    while(not rospy.is_shutdown() and not current_state.connected):
        rate.sleep()

    set_point_list = []
    N_setpoint = 4 # num of set points
    pos_list = [(0,0), (0,1), (1,0), (1,1)]
    for i in range(N_setpoint):
        pose = PoseStamped()

        pose.pose.position.x = pos_list[i][0]
        pose.pose.position.y = pos_list[i][1]
        pose.pose.position.z = 5

        set_point_list.append(pose);

    # Send a few setpoints before starting

    pub_pose = set_point_list[0]
    

    for i in range(100):
        if(rospy.is_shutdown()):
            break

        local_pos_pub.publish(pub_pose)
        rate.sleep()

    offb_set_mode = SetModeRequest()
    offb_set_mode.custom_mode = 'OFFBOARD'

    arm_cmd = CommandBoolRequest()
    arm_cmd.value = True

    last_req = rospy.Time.now()
    pos_last_pose_set = rospy.Time.now()

    cnt = 0
    while(not rospy.is_shutdown()):
        if(current_state.mode != "OFFBOARD" and (rospy.Time.now() - last_req) > rospy.Duration(5.0)):
            if(set_mode_client.call(offb_set_mode).mode_sent == True):
                rospy.loginfo("OFFBOARD enabled")

            last_req = rospy.Time.now()
        else:
            if(not current_state.armed and (rospy.Time.now() - last_req) > rospy.Duration(5.0)):
                if(arming_client.call(arm_cmd).success == True):
                    rospy.loginfo("Vehicle armed")

                last_req = rospy.Time.now()

        local_pos_pub.publish(pub_pose)

        if (rospy.Time.now() - pos_last_pose_set > rospy.Duration(3.0)): # set setpoint once in 2 sec
            pos_last_pose_set = rospy.Time.now()

            cnt = (cnt + 1) % N_setpoint
            pub_pose = set_point_list[cnt]
            
            # if pose.pose.position.z <= 100: # if current altitude is less than 100
            #     pose.pose.position.z = pose.pose.position.z + 1 
            # else:
            #     pose.pose.position.z = pose.pose.position.z - 1
                

        rate.sleep()