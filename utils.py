# -*- coding: UTF-8 -*-
import sys
import prettytable as pt
import time
from threading import Thread
import json


# 解析命令行参数，获取监听端口和邻居节点信息表
def parse_argv():
    s = sys.argv[1:]  # 命令行参数列表
    port = int(s.pop(0))  # 首个为监听端口（需转换为int型）
    neighbors = {}
    slen = int(len(s) / 3)
    for i in range(0, slen):  # 每相邻三个组成居节点信息表中一项
        neighbors[s[3 * i]] = (
            s[3 * i],
            int(s[3 * i + 1]),
            float(s[3 * i + 2]))
    return port, neighbors


# 根据邻居节点初始化路由表
def initrt(neighbors, my_ip):
    rt = {}
    rt[my_ip] = (my_ip, my_ip, 0)  # 到达本机IP直接交付，距离为0
    for neighbor in neighbors.keys():  # 到达邻居节点
        rt[neighbor] = (neighbor, neighbor, neighbors[neighbor][2])
    return rt


# 显示路由表
def showrt(rt, msg):
    tb = pt.PrettyTable()  # 创建PrettyTable类
    tb.field_names = ["Destination", "Next Hop", "Cost"]  # 创建表头
    _rt = sorted(rt)  # 按照目的地址从小到大排序
    for ritem in _rt:  # 路由表中的每一项
        tb.add_row(rt[ritem])

    # 根据路由表不同状态，显示不同颜色的路由表
    color = {'Update': '31', 'Converge': '32', 'Change': '33', 'Init': '34', 'Recv': '35', 'Send': '36'}
    print('\033[1;%s;40m' % color[msg])
    print("[%s] Router Table at " % msg, time.strftime('%Y.%m.%d %H:%M:%S ', time.localtime(time.time())))
    print(tb)
    print('\033[0m')


# 对消息进行分析，返回消息类型和消息有效部分
def data_analysis(data):
    _msg_type = data.split(']')  # 按照右中括号切分
    msg_type = _msg_type[0][1:]  # 左侧为消息类型（去除左中括号）
    msg = _msg_type[1]  # 左侧为消息内容
    return msg_type, msg


# 对链路距离改变做出反应
def linkchange(router_table, neighbors, host, port, cost):
    neighbors[host] = (host, port, cost)  # 更新邻居信息节点表中对应项的距离
    router_table[host] = (host, host, cost)  # 更新路由表中对应项
    showrt(router_table, 'Change')  # 显示改变后的路由表
    return router_table, neighbors


# 对链路断开做出反应
def linkdown(router_table, neighbors, host, port):
    router_table[host] = (host, host, float("inf"))  # 更新路由表中对应项距离为无穷大
    neighbors.pop(host)  # 删除邻居信息节点表中对应项
    showrt(router_table, 'Change')  # 显示改变后的路由表
    return router_table, neighbors


# 对新增链路做出反应
def linkup(router_table, neighbors, host, port, cost):
    neighbors[host] = (host, port, cost)  # 在邻居信息节点表新增一项
    router_table[host] = (host, host, cost)  # 更新路由表中对应项
    showrt(router_table, 'Change')  # 显示改变后的路由表
    return router_table, neighbors


class RepeatTimer(Thread):
    def __init__(self, interval, target, socket):
        Thread.__init__(self)
        self.interval = interval  # 发送间隔
        self.target = target
        self.socket = socket
        self.daemon = True
        self.stopped = False

    def run(self):
        while not self.stopped:
            time.sleep(self.interval)
            self.target(self.socket)
