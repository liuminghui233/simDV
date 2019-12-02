# -*- coding: UTF-8 -*-

import socket
from threading import Thread
from utils import *
import copy

# 从命令行参数中解析监听端口和邻居节点信息表
port, neighbors = parse_argv()

# 根据邻居节点信息表初始化路由表
my_ip = '10.30.3.101'  # 本机IP
router_table = initrt(neighbors, my_ip)

# 输出初始路由表
showrt(router_table, 'Init')

# 创建socket
router = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 监听端口
router.bind((my_ip, int(port)))


# 监听终端输入并处理链路变化信息
def parse_user_input():
    global router_table, neighbors, router
    while True:
        cmd = input()
        if cmd:
            argv = cmd.split(' ')  # 按照空格分割，得到参数列表

            # 根据argv[0]判断链路改变类型，触发不同事件并按格式生成通知信息
            if argv[0] == 'linkchange':
                router_table, neighbors = linkchange(router_table, neighbors, argv[1], int(argv[2]), float(argv[3]))
                send_msg = '[linkchange]' + argv[3]
            elif argv[0] == 'linkdown':
                router_table, neighbors = linkdown(router_table, neighbors, argv[1], int(argv[2]))
                send_msg = '[linkdown]'
            elif argv[0] == 'linkup':
                router_table, neighbors = linkup(router_table, neighbors, argv[1], int(argv[2]), float(argv[3]))
                send_msg = '[linkup]' + argv[3]
            else:  # 若为无效消息，则发送空消息，这样接收端会自动过滤掉
                send_msg = ''

            addr = (argv[1], int(argv[2]))  # 发送地址
            router.sendto(send_msg.encode(), addr)  # 发送链路改变消息
            print ('Send link msg to ', addr)
            print('send_msg:' + send_msg)


# 定时向邻居节点发送路由表
def broadcast_costs(router, poinsoned_flag=False):
    global router_table, neighbors
    if poinsoned_flag:  # 若使用逆向毒化技术
        # 对于每一个邻居，发送毒化后的路由表
        for neighbor in neighbors.keys():
            _router_table = copy.deepcopy(router_table)  # 拷贝路由表

            # 毒化路由表
            for rtiem in _router_table.keys():
                if _router_table[rtiem][1] == neighbor and rtiem != neighbor:
                    _router_table[rtiem] = (rtiem, neighbor, float("inf"))

            # 发送毒化后的路由表
            addr = (neighbors[neighbor][0], neighbors[neighbor][1])  # 发送地址
            send_json = json.dumps(_router_table).encode('utf-8')  # 将路由表打包成json格式
            router.sendto(send_json, addr)  # 发送信息
            print ('Send router_table to ', addr)
            showrt(_router_table, 'Send')  # 显示发送的路由表

    else:  # 若不使用逆向毒化技术
        for neighbor in neighbors.keys():
            # 对于每一个邻居，直接发送自己的路由表
            addr = (neighbors[neighbor][0], neighbors[neighbor][1])  # 发送地址
            send_json = json.dumps(router_table).encode('utf-8')  # 将路由表打包成json格式
            router.sendto(send_json, addr)  # 发送信息
            print ('Send router_table to ', addr)
            showrt(router_table, 'Send')  # 显示发送的路由表


# 接收并处理邻居节点发来的信息
def update_costs(router):
    global router_table, neighbors
    while True:
        _data, addr = router.recvfrom(1024)  # 接收消息
        data = _data.decode('utf-8')
        if data:  # 收到的消息不为空
            if data[0] == '[':  # 收到链路改变信息
                print ('Recv link msg from ', addr)
                msg_type, msg = data_analysis(data)  # 解析信息
                # 按照不同的类型，进行不同的处理
                if msg_type == 'linkchange':
                    router_table, neighbors = linkchange(
                        router_table, neighbors, addr[0], addr[1], float(msg))
                if msg_type == 'linkdown':
                    router_table, neighbors = linkdown(
                        router_table, neighbors, addr[0], addr[1])
                if msg_type == 'linkup':
                    router_table, neighbors = linkup(
                        router_table, neighbors, addr[0], addr[1], float(msg))
            else:  # 收到路由信息
                rec_rt = json.loads(data)  # 将收到路由的信息转为字典格式
                print ('Recv router_table from ', addr)
                showrt(rec_rt, 'Recv')  # 显示收到的路由表
                converge_flag = True  # 是否收敛标志
                for rec_rtiem in rec_rt.keys():  # 对于收到的路由表中的每一项
                    if rec_rtiem not in router_table.keys():  # 出现新的目的地址，则加入路由表
                        router_table[rec_rtiem] = (
                            rec_rtiem,
                            addr[0],
                            rec_rt[rec_rtiem][2] + neighbors[addr[0]][2])
                        converge_flag = False  # 路由表有变化则置收敛标志为False
                    else:  # 已经存在的目的地址
                        if router_table[rec_rtiem][1] == addr[0]:  # 若下一跳相同，有变化则更新路由表
                            if rec_rt[rec_rtiem][2] + neighbors[addr[0]][2] \
                                    != router_table[rec_rtiem][2]:
                                router_table[rec_rtiem] = (
                                    rec_rtiem,
                                    addr[0],
                                    rec_rt[rec_rtiem][2] + neighbors[addr[0]][2])
                                converge_flag = False  # 路由表有变化则置收敛标志为False
                        else:  # 若下一跳不同，则比较距离决定是否更新
                            if rec_rt[rec_rtiem][2] + neighbors[addr[0]][2] \
                                    < router_table[rec_rtiem][2]:
                                router_table[rec_rtiem] = (
                                    rec_rtiem,
                                    addr[0],
                                    rec_rt[rec_rtiem][2] + neighbors[addr[0]][2])
                                converge_flag = False  # 路由表有变化则置收敛标志为False
                showrt(router_table, 'Converge') if converge_flag else showrt(router_table, 'Update')


# 绑定三个线程
Thread(target=parse_user_input).start()
RepeatTimer(interval=30, target=broadcast_costs, socket=router).start()
Thread(target=update_costs, args=(router,)).start()
