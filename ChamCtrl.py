# -*- coding: gbk-*-
"""
版权所有 (c) 2025 [吴宪]

本软件ChamCtrl（以下简称“软件”）为个人非商业用途开源发布。任何人均可免费使用、复制、修改和分发本软件，但仅限于个人非商业用途。
对于商业用途（包括但不限于嵌入商业产品、提供商业服务、营利分发等），必须事先获得作者的书面许可。

本软件按“现状”提供，不附带任何明示或暗示的担保，包括但不限于对适销性、特定用途适用性以及不侵权的保证。
在任何情况下，作者均不对因使用或无法使用本软件而产生的任何直接、间接、偶然、特殊或后续损害承担责任。

如需商业授权或有任何疑问，请联系：[dakongwuxian@gmail.com]
"""

import struct
import numpy
import numpy as np
import select
import glob
import math
import os
import configparser
import socket
import re
import datetime as dt
from datetime import timedelta,datetime
import threading
from time import sleep
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg)
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from matplotlib.ticker import MultipleLocator
from matplotlib.dates import DayLocator, MinuteLocator, DateFormatter, HourLocator


class Chamber:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.timeout = 5
        self.tcp_client = None
        self.connected = False # Initialize connected status

    def connect(self):
        if self.connected and self.tcp_client:
            try:
                # 简单地尝试发送一个空字节串以验证连接是否仍然有效
                # 更健壮的实现会使用Modbus诊断功能
                # 暂时保持此简单的连接状态验证
                self.tcp_client.send(b'') 
                return True
            except (socket.error, OSError):
                self.close() # 连接丢失，重置状态
                pass
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip, self.port))
            self.tcp_client = sock
            self.connected = True  # 更新连接状态
            print(f"Successfully connected to {self.ip}:{self.port}")
            return True
        except Exception as e:
            print(f"Connect fail: {e}")
            self.tcp_client = None
            self.connected = False  # 更新连接状态
            return False

    def close(self):
        if self.tcp_client:
            self.tcp_client.close()
            self.tcp_client = None
            self.connected = False
            print("Chamber connection closed.")

    '''def send_cmd(self, cmd, timeout=0.5):
        if not self.connect():
            return ""
        try:
            self.tcp_client.sendall((cmd + "\r\n").encode('utf-8'))
            ready, _, _ = select.select([self.tcp_client], [], [], timeout)
            if not ready:
                return ""  # 超时，没有应答
            return self.tcp_client.recv(512).decode()
        except Exception as e:
            print(f"Command fail: {e}")
            return ""'''

    def get_run_status(self):
        """
        使用 Modbus FC=03 读取运行状态。
        设备运行状态地址为400，16进制为00H C8H，长度为1个字。 [cite: 3]
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x00\xC8"
        read_length = b"\x00\x01"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Run Status Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # 解析响应数据部分
            if len(read_response) == 11:
                if read_response[:10] !=  b"\x00\x00\x00\x00\x00\x05\x01\x03\x02\x00":
                    return None
                value_byte = read_response[10:11]
                if value_byte in (b"\x00", b"\x01", b"\x02"):
                    status_value = int.from_bytes(value_byte, byteorder='big') 
                    print(f"Read run status: {status_value}")
                    return status_value                  
                else:
                    return None

    def set_run_status(self,target_status):
        write_header_1 = b"\x00\x00\x00\x00\x00"
        command_len = b"\x09"
        write_header_2 = b"\x01"
        command_code = b"\x10"
        reg_address = b"\x00\xC8"
        write_length = b"\x00\x01"
        write_bytes_num = b"\x02"
        target_status_byte = target_status.to_bytes(2, byteorder='big')

        command_to_send = write_header_1 + command_len + write_header_2 + command_code + reg_address + write_length + write_bytes_num + target_status_byte
        print('Send command:\n'+command_to_send.hex()+'\n')

        write_response = self._send_modbus_request(command_to_send)

        if write_response:
            # 解析响应数据部分
            if len(write_response) == 12:
                if write_response[:11] !=  b"\x00\x00\x00\x00\x00\x06\x01\x10\x00\xC8\x00":   # 00 00 00 00 00 06 01 10 00 C8 00 01
                    return False
                if write_response[11]!=target_status_byte[1]:
                    return False
                status_map = {
                        0: "STOP",
                        1: "RUN",
                        2: "PAUSE"
                }
                print(f"Set run status to {target_status}: {status_map.get(target_status, 'UNKNOWN')}.\n")
                messagebox.showinfo("Run Status Set Pass", f"Set {target_status}: {status_map.get(target_status, 'UNKNOWN')} Pass.")
                return True 
        print(f"Failed to set target_status.\n")
        messagebox.showerror("Run Status Set Fail", f"Set {target_status}: {status_map.get(target_status, 'UNKNOWN')} Fail.")
        return False

    def get_run_type(self):
        """
        使用 Modbus FC=03 读取运行状态。
        设备运行状态地址为400，16进制为00H C8H，长度为1个字。 [cite: 3]
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x00\xCA"
        read_length = b"\x00\x01"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Run Type Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # 解析响应数据部分
            if len(read_response) == 11:
                if read_response[:10] !=  b"\x00\x00\x00\x00\x00\x05\x01\x03\x02\x00":
                    return None
                value_byte = read_response[10:11]
                if value_byte in (b"\x00", b"\x01", b"\x02" ,b"\03"):
                    type_value = int.from_bytes(value_byte, byteorder='big') 
                    print(f"Read run status: {type_value}")
                    self.current_run_mode = type_value
                    return type_value             
                else:
                    return None

    def set_run_type(self,run_type):
        '''register address 404	00HCAH'''
        write_header_1 = b"\x00\x00\x00\x00\x00"
        command_len = b"\x09"
        write_header_2 = b"\x01"
        command_code = b"\x10"
        reg_address = b"\x00\xCA"
        write_length = b"\x00\x01"
        write_bytes_num = b"\x02"
        target_status_byte = run_type.to_bytes(2, byteorder='big')

        command_to_send = write_header_1 + command_len + write_header_2 + command_code + reg_address + write_length + write_bytes_num + target_status_byte
        print('Send command:\n'+command_to_send.hex()+'\n')

        write_response = self._send_modbus_request(command_to_send)

        if write_response:
            # 解析响应数据部分
            if len(write_response) == 12:
                if write_response !=  b"\x00\x00\x00\x00\x00\x06\x01\x10\x00\xCA\x00\x01":   # 00 00 00 00 00 06 01 10 00 CA 00 01
                    return False
                status_map = {
                        0: "Constant Temp",
                        1: "Viarable Temp",
                        2: "Constant Humidity",
                        3: "Viarable Humidity"
                }
                print(f"Set run type to {run_type}: {status_map.get(run_type, 'UNKNOWN')}.\n")
                if run_type !=0:
                    messagebox.showwarning("Run Type Set Pass", f"Set {run_type}: {status_map.get(run_type, 'UNKNOWN')} Pass.\nMust use Constant Mode if you want to use Wave Mode on this GUI.'")
                    self.current_run_mode = run_type
                else:
                    messagebox.showinfo("Run Type Set Pass", f"Set {run_type}: {status_map.get(run_type, 'UNKNOWN')} Pass.")
                    self.current_run_mode = run_type
                return True
        print(f"Failed to set target_status.\n")
        messagebox.showerror("Run Type Set Fail", f"Set {run_type}: {status_map.get(run_type, 'UNKNOWN')} Fail.")
        return False

    def hb4_to_float(b0, b1, b2, b3):
        j = b0
        t = (b1 << 16) + (b2 << 8) + b3

        if j == 0:
            return 0.0

        if (j & 0x80) == 0:
            i = 2.0
        else:
            i = -2.0

        j = j & 0x7F
        j = j * 2

        if (t & 0x800000) != 0:
            j += 1

        t = t | 0x800000

        while j > 0x80:
            i *= 2.0
            j -= 1

        while j < 0x80:
            i /= 2.0
            j += 1

        result = i * t / 0x800000
        return result

    def float_to_hb4(value):
        return struct.unpack('>4B', struct.pack('>f', value))

    def get_temp(self):
        """
        使用 Modbus FC=03 读取箱体温度。
        温度测量值地址为320，16进制为00H A0H，长度为2个字。 [cite: 4]
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x00\xA0"
        read_length = b"\x00\x02"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Temp Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # 解析响应数据部分
            if len(read_response) == 13:
                if read_response[:9] !=  b"\x00\x00\x00\x00\x00\x07\x01\x03\x04":  
                    return 'Error'
                value_byte = read_response[9:13] # 这个[9:13]只会取第 10 11 12 13字节，从9开始取到12，不包含13

                temp_float_value = Chamber.hb4_to_float(value_byte[0],value_byte[1],value_byte[2],value_byte[3]) 
                print(f"Read temp registers: {value_byte[0],value_byte[1],value_byte[2],value_byte[3]}")
                print(f"Read temp : {temp_float_value}")
                return temp_float_value               
            else:
                return None

    def get_target_temp(self):
        """
        使用 Modbus FC=03 读取箱体设定温度。
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x06\xCE"
        read_length = b"\x00\x02"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Target Temp Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # 解析响应数据部分
            if len(read_response) == 13:
                if read_response[:9] !=  b"\x00\x00\x00\x00\x00\x07\x01\x03\x04":  
                    return 'Error'
                value_byte = read_response[9:13] # 这个[9:13]只会取第 10 11 12 13字节，从9开始取到12，不包含13

                temp_float_value = Chamber.hb4_to_float(value_byte[0],value_byte[1],value_byte[2],value_byte[3]) 
                print(f"Read target temp register: {value_byte[0],value_byte[1],value_byte[2],value_byte[3]}")
                print(f"Read target temp : {temp_float_value}")
                return temp_float_value               
            else:
                return None

    def set_temp(self, temp_value):
        """
        使用 Modbus FC=10 设置箱体温度。
        设备温度给定值地址为3484，16进制为06H CEH，长度为2个字。 [cite: 5, 29]
        """
        write_header_1 = b"\x00\x00\x00\x00\x00"
        command_len = b"\x0B"
        write_header_2 = b"\x01"
        command_code = b"\x10"
        reg_address = b"\x06\xCE"
        write_length = b"\x00\x02"
        write_bytes_num = b"\x04"
        write_value = bytes(Chamber.float_to_hb4(temp_value))

        command_to_send = write_header_1 + command_len + write_header_2 + command_code + reg_address + write_length + write_bytes_num + write_value
        print('Set temp command\n'+command_to_send.hex()+'\n')

        write_response = Chamber._send_modbus_request(self,command_to_send)

        if write_response:
            # 解析响应数据部分
            if len(write_response) == 12:
                if write_response !=  b"\x00\x00\x00\x00\x00\x06\x01\x10\x06\xCE\x00\x02":   # 00 00 00 00 00 06 01 10 06 CE 00 02
                    return False
                print(f"Set temperature to {temp_value}°C.")
                return True 
        print(f"Failed to set temperature°C.")
        return False

        # --- Modbus 辅助函数 ---------------------------------------------------------------------
 
    def _send_modbus_request(self, request_adu, timeout=0.5):
        """发送 Modbus ADU 并接收响应。"""
        if not self.connect():
            return None
        try:
            self.tcp_client.sendall(request_adu)
            #self.tcp_client.sendall((request_adu+ "\r\n").encode('utf-8'))
            # 使用 select 等待数据，带超时
            ready, _, _ = select.select([self.tcp_client], [], [], timeout)
            if not ready:
                print("Modbus response timeout.")
                return None
            return self.tcp_client.recv(512)
        except Exception as e:
            print(f"Command fail: {e}")
            return ""

# 此段空白用以分开面板和函数 ---------------------------------------------------------------------------------------------------------------















# 此段空白用以分开面板和函数 ---------------------------------------------------------------------------------------------------------------

class ChamberGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Temperature Chamber Controller")
        self.geometry("850x700")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # 创建菜单栏
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # About 菜单
        self.about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="About", menu=self.about_menu)
        self.about_menu.add_command(label="Developed by Xian Wu", state="disabled")
        self.about_menu.add_command(label="dakongwuxian@gmail.com", state="disabled")
        self.about_menu.add_command(label="vesion 20250929", state="disabled")

        # 日志文件路径
        self.log_path = "ChamCtrlLog.txt"
        self.log_file = open(self.log_path, "a+", encoding="utf-8")

        # 1. 创建并放置 Matplotlib 图表
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        #self.ax.set_title("Temp Wave")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Temperature /°C")

        # 2. 设置 X 轴为 24 小时跨度，居中在当前时刻
        #now = dt.datetime.now()
        #self.ax.set_xlim(now - timedelta(hours=12), now + timedelta(hours=12))
        #self.ax.set_ylim(-50, 140)
        now = dt.datetime.now()
        self.ax.set_xlim(now - timedelta(hours=12), now + timedelta(hours=12))
        self.ax.set_ylim(-50, 140)

        # keep a persistent Line2D for the red preview, initially empty:
        self.preview_line, = self.ax.plot([], [], '-', lw=2, color='red', label='_wave_preview')

        # keep a persistent PathCollection for the blue scatter, initially empty:
        self.data_scatter = self.ax.scatter([], [], s=10, color='blue')

        # —— 禁用自动缩放，后续调用 scatter 不会改变 xlim/ylim —— 
        self.ax.set_autoscale_on(False)

        self._hour_locator = HourLocator(interval=1)
        self._minor_locator = MinuteLocator(byminute=range(0, 60, 10))
        self.ax.xaxis.set_minor_locator(self._minor_locator)
        self.ax.xaxis.set_minor_formatter(DateFormatter('%H:%M'))

        # 调用一次，配置 Locator 和 Grid
        self.setup_axis()

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        #self.update_minor_locator()

        # 绑定鼠标点击事件
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)

        # 绑定滚轮事件
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

        # 父容器，用来装 btn_frame 和 ctrl_frame
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # 按钮区域
        # 按钮 Frame（左侧）
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y,padx=(0,20))

        # Y 轴按钮
        ttk.Label(btn_frame, text="Y Axis：").grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="+", command=self.zoom_y_in).grid(row=0, column=1)
        ttk.Button(btn_frame, text="-", command=self.zoom_y_out).grid(row=0, column=2)
        ttk.Button(btn_frame, text="↑", command=self.pan_y_up).grid(row=0, column=3)
        ttk.Button(btn_frame, text="↓", command=self.pan_y_down).grid(row=0, column=4)

        # X 轴按钮
        ttk.Label(btn_frame, text="X Axis：").grid(row=1, column=0, padx=5)
        ttk.Button(btn_frame, text="+", command=self.zoom_x_in).grid(row=1, column=1)
        ttk.Button(btn_frame, text="-", command=self.zoom_x_out).grid(row=1, column=2)
        ttk.Button(btn_frame, text="←", command=self.pan_x_left).grid(row=1, column=3)
        ttk.Button(btn_frame, text="→", command=self.pan_x_right).grid(row=1, column=4)

        # 当前时间居中按钮
        ttk.Button(btn_frame, text="Current to Center", command=self.center_now).grid(row=2, column=0, columnspan=2)

        # 增加 Auto Center 复选框
        self.auto_center_var = tk.IntVar(value=1)  # 默认勾选
        ttk.Checkbutton(btn_frame, text="Auto Center", variable=self.auto_center_var, command=self.on_auto_center_toggle).grid(row=2, column=2, columnspan=2)

        # 增加 Auto Mark 复选框
        self.auto_mark_var = tk.IntVar(value=1)  # 默认勾选
        ttk.Checkbutton(btn_frame, text="Auto Mark", variable=self.auto_mark_var, command=self.on_auto_mark_toggle).grid(row=2, column=4, columnspan=2)

        # 记录到状态变量中
        self.auto_center = 1
        self.auto_mark = 1

        # 是否正在变温运行中的标志位
        self.cycle_running = False

        # 当前温箱运行的类型，0123依次为恒温、变温、恒湿、变湿
        self.current_run_mode = 0

        # 系统时间显示
        ttk.Label(btn_frame, text="Date：").grid(row=3, column=0, sticky="e")
        self.date_var = tk.StringVar(value="--")
        ttk.Label(btn_frame, textvariable=self.date_var).grid(row=3, column=1, sticky="w")
        ttk.Label(btn_frame, text="Time：").grid(row=3, column=2, sticky="e")
        self.time_var = tk.StringVar(value="--")
        ttk.Label(btn_frame, textvariable=self.time_var).grid(row=3, column=3, sticky="w")

        # 2. 其余 GUI 部件
        # 控制面板 Frame（右侧）
        ctrl_frame = ttk.Frame(top_frame)
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        right_row_0_frame = ttk.Frame(ctrl_frame)
        right_row_0_frame.grid(row=0, column=0,columnspan=3, sticky="w")

        # 温箱 IP 地址选择列表 
        self.ip_options = [
            "Chamber01:10.166.156.132",
            "Chamber02:10.166.156.135",
            "Chamber03:10.166.156.138",
            "Chamber04:10.166.156.141",
            "Chamber05:10.166.156.147",
            "Chamber06:10.166.156.173",
            "Chamber07:10.166.156.150",
            "Chamber08:10.166.156.153",
            "Chamber09:10.166.156.159",
            "Chamber10:10.166.156.162",
            "Chamber11:10.166.156.166",
            "Chamber12:10.166.157.6",
            "Chamber13:10.166.157.8",
            "Chamber14:10.166.157.14",
            "Chamber15:10.166.157.20",
            "Chamber16:10.166.157.22",
            "Chamber17:10.166.157.24",
            "Chamber18:10.166.157.25",
            "Chamber19:10.166.157.102",
        ]
        # IP选择
        ttk.Label(right_row_0_frame, text="IP:").grid(row=0, column=0, sticky="w")

        # Combobox 只读，下拉列表不可编辑 :contentReference[oaicite:2]{index=2}
        self.selected_ip = tk.StringVar()
        self.ip_combo = ttk.Combobox(
            right_row_0_frame,
            textvariable=self.selected_ip,
            values=self.ip_options,
            state="",
            width=23
        )
        self.ip_combo.grid(row=0, column=1, padx=5, sticky="w")
        # 默认选第一个
        self.ip_combo.current(0)

        # 温箱 port 选择列表 
        self.port_options = [
            "502",
            "503",
            "504",
            "505",
            "506",
        ]

        # port select
        ttk.Label(right_row_0_frame, text = "Port:").grid(row=0, column=2,sticky="w")

        # Combobox 只读，下拉列表不可编辑 :contentReference[oaicite:2]{index=2}
        self.selected_port = tk.StringVar()
        self.port_combo = ttk.Combobox(
            right_row_0_frame,
            textvariable=self.selected_port,
            values=self.port_options,
            state="",
            width=3
        )
        self.port_combo.grid(row=0, column=3, padx=5, sticky="w")
        # 默认选第一个
        self.port_combo.current(0)
        
        self.conn_btn = ttk.Button(right_row_0_frame, text="Connect", command=self.toggle_connection,width=10)
        self.conn_btn.grid(row=0, column=4, padx=(13,0))

        # 运行状态
        right_row_1_frame = ttk.Frame(ctrl_frame)
        right_row_1_frame.grid(row=1, column=0,columnspan=3, sticky="w")
        self.run_status_label = ttk.Label(right_row_1_frame, text="Status：")
        self.run_status_label.grid(row=0, column=0, padx=(0,0), sticky="w")

        self.status_var = tk.StringVar(value="disconnected")

        self.run_status_label_value = ttk.Label(right_row_1_frame, textvariable=self.status_var,width = 18)
        self.run_status_label_value.grid(row=0, column=1, padx=0, sticky="w")

        self.run_btn = ttk.Button(right_row_1_frame, text="RUN", command=lambda: self.chamber.set_run_status(1),width = 6)
        self.run_btn.grid(row=0, column=2, padx=(34,5), sticky="w")

        self.stop_btn = ttk.Button(right_row_1_frame, text="STOP", command=lambda: self.chamber.set_run_status(0),width = 6)
        self.stop_btn.grid(row=0, column=3, padx=5, sticky="w")

        self.pause_btn = ttk.Button(right_row_1_frame, text="PAUSE", command=lambda: self.chamber.set_run_status(2),width = 6)
        self.pause_btn.grid(row=0, column=4, padx=(5,0), sticky="w")

        # row 2
        right_row_2_frame = ttk.Frame(ctrl_frame)
        right_row_2_frame.grid(row=2, column=0,columnspan=3, sticky="w")
        # 当前温度
        ttk.Label(right_row_2_frame, text="Temperture ：").grid(row=0, column=0,padx=(0,5), sticky="w")
        self.temp_var = tk.StringVar(value="--")
        ttk.Label(right_row_2_frame, textvariable=self.temp_var,width = 9).grid(row=0, column=1,padx=(0,5), sticky="w")

        self.test_type_constant_btn = ttk.Button(right_row_2_frame, text="Constant Mode", command=lambda: self.chamber.set_run_type(0),width = 14)
        self.test_type_constant_btn.grid(row=0, column=3, padx=(0,5), sticky="w")

        self.test_type_viarable_btn = ttk.Button(right_row_2_frame, text="Viarable Mode", command=lambda: self.chamber.set_run_type(1),width = 14)
        self.test_type_viarable_btn.grid(row=0, column=4, padx=5, sticky="w")

        # 目标温度设置
        right_row_3_frame = ttk.Frame(ctrl_frame)
        right_row_3_frame.grid(row=3, column=0,columnspan=3, sticky="w")
        ttk.Label(right_row_3_frame, text="Target temp：").grid(row=0, column=0,padx=(0,5), sticky="w")
        self.target_temp_label_var = tk.StringVar(value="--")
        ttk.Label(right_row_3_frame, textvariable=self.target_temp_label_var,width = 10).grid(row=0, column=1,padx=(0,5), sticky="w")
        self.set_temp_var = tk.StringVar()
        ttk.Entry(right_row_3_frame, textvariable=self.set_temp_var, width=10).grid(row=0, column=2,padx=(46,5), sticky="w")
        ttk.Button(right_row_3_frame, text="Set", command=self.on_set_temp).grid(row=0, column=3, padx=5)



        # 多行文本框与按钮
        setting_frame = ttk.LabelFrame(self, text="Temp Wave Setting")
        setting_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        # 多行文本框（左侧，占据大部分宽度）
        self.wave_text = ScrolledText(setting_frame, width=50, height=6)
        self.wave_text.grid(row=0, column=0, padx=(5,10), pady=5, sticky="nsew")

        # 右侧按钮区域
        btn_wave_frame = ttk.Frame(setting_frame)
        btn_wave_frame.grid(row=0, column=1, padx=5, pady=5, sticky="n")
        btn_wave_frame.columnconfigure(0, weight=1)

        # “Wave Preview” 按钮
        self.wave_preview_btn = ttk.Button(btn_wave_frame, text="Wave Preview", command=self.wave_preview)
        self.wave_preview_btn.grid(row=0, column=0, sticky="ew")

        # “Temp Cycle Start” 按钮
        self.temp_cycle_start_btn = ttk.Button(btn_wave_frame, text="Wave Start", command=self.temp_cycle_start)
        self.temp_cycle_start_btn.grid(row=1, column=0, sticky="ew")

        # “Load Wave Setting” 按钮
        self.load_wave_btn = ttk.Button(btn_wave_frame,text="Load Wave",command=self.load_wave_setting)
        self.load_wave_btn.grid(row=2, column=0, sticky="ew")

        # “Save Wave Setting” 按钮
        self.save_wave_btn = ttk.Button(btn_wave_frame,text="Save Wave",command=self.save_wave_setting)
        self.save_wave_btn.grid(row=3, column=0, sticky="ew")


        # 使文本框与按钮区域在水平上拉伸
        setting_frame.columnconfigure(0, weight=1)
        setting_frame.columnconfigure(1, weight=0)

        # 3. 日志文件初始化
        # （在这里仅确保文件存在，由轮询中创建/写入管理）
        open(self.log_path, "a+", encoding="utf-8").close()
        # 用于记录写入同一个文件的次数，每1000次检查当前文件大小
        self.write_count = 0

        # 背景轮询控制
        self.chamber = None
        self._running = False
        self._poll_thread = None

        # 曲线散点变量
        self.wave_point_times = None
        self.wave_point_temps = None

        # 启动系统时间更新
        self.after(1000, self.update_datetime)
        # 启动初次曲线绘制
        self.plot_log_data()
        self.update_minor_locator()

        # Ini 文件路径
        self.ini_path = "ChamCtrlSetup.ini"
        self._load_last_ip()
        self._load_last_wave_text()

        # 窗口关闭钩子
        self.protocol("WM_DELETE_WINDOW", self.on_close)

# 此段空白用以分开面板和函数 ---------------------------------------------------------------------------------------------------------------















# 此段空白用以分开面板和函数 ---------------------------------------------------------------------------------------------------------------

    def on_auto_mark_toggle(self):
        self.auto_mark = self.auto_mark_var.get()

    def on_auto_center_toggle(self):
        self.auto_center = self.auto_center_var.get()

    def _load_last_ip(self):
        if not os.path.exists(self.ini_path):
            return
        config = configparser.ConfigParser()
        try:
            config.read(self.ini_path, encoding="utf-8")
            last_ip = config["DEFAULT"].get("last_ip", "").strip()
            if last_ip and last_ip in self.ip_options:
                idx = self.ip_options.index(last_ip)
                self.ip_combo.current(idx)
        except Exception:
            pass

    def _load_last_ip(self):
        if not os.path.exists(self.ini_path):
            return
        config = configparser.ConfigParser()
        try:
            config.read(self.ini_path, encoding="utf-8")
            last_ip = config["DEFAULT"].get("last_ip", "").strip()
            if last_ip and last_ip in self.ip_options:
                idx = self.ip_options.index(last_ip)
                self.ip_combo.current(idx)
        except Exception:
            pass

    def _load_last_wave_text(self):
        """启动时加载上次保存的波形设置文本"""
        if not os.path.exists(self.ini_path):
            return
        config = configparser.ConfigParser()
        try:
            config.read(self.ini_path, encoding="utf-8")
            wt = config["DEFAULT"].get("wave_text", "")
            if wt:
                # 填入多行文本框
                self.wave_text.delete("1.0", tk.END)
                self.wave_text.insert(tk.END, wt)
        except Exception:
            pass
        
    def load_wave_setting(self):
        """从 .txt 文件加载波形设置到多行文本框"""
        path = filedialog.askopenfilename(
            title="Load Wave Setting",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Cannot read file:\n{e}")
            return

        # 将读取的内容放入多行文本框
        self.wave_text.delete("1.0", tk.END)
        self.wave_text.insert(tk.END, content)

    def save_wave_setting(self):
        """将多行文本框内容保存到指定 .txt 文件"""
        path = filedialog.asksaveasfilename(
            title="Save Wave Setting",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            content = self.wave_text.get("1.0", tk.END)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot write file:\n{e}")
            return

        messagebox.showinfo("Saved", f"Wave setting saved to:\n{path}")

    def wave_preview(self):
        text = self.wave_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "No wave definition found")
            return

        # 1. 解析 start temp、loop count 和节点列表
        # 示例格式：(start temp 25C)-(loop count 10)-[(0,25C)-(55,80C)-…]
        m_start = re.search(r'start temp\s+(-?\d+)C', text)
        m_loop  = re.search(r'loop count\s+(\d+)', text)
        nodes   = re.findall(r'\((\d+),\s*(-?\d+)C\)', text)

        if not (m_start and m_loop and nodes):
            messagebox.showerror("Error", "Wave format invalid")
            return

        start_temp = int(m_start.group(1))
        loop_count = int(m_loop.group(1))
        # 转成 [(minutes, temp), ...]
        points = [(int(mins), int(tmp)) for mins, tmp in nodes]

        # 1. 计算第一段：当前温度到 start_temp
        now_dt    = dt.datetime.now()
        base_time = now_dt
        try:
            s = self.temp_var.get().strip()
            # 去掉度符号（支持“℃”和“°C”两种写法）
            s = s.rstrip("℃°C")  
            cur_temp = float(s)
        except (ValueError, TypeError):
            cur_temp = 25.0
        delta_temp = start_temp - cur_temp
        minutes0   = abs(delta_temp)
        t0_end     = base_time + dt.timedelta(minutes=minutes0)

        wave_times = [base_time]
        wave_temps = [cur_temp]
        # 如果要增加的点和前一个点相同，则不增加新的点
        if not (t0_end==wave_times[-1] and start_temp==wave_temps[-1]):
            wave_times.append(t0_end)
            wave_temps.append(start_temp)

        # 2. 循环段：严格用增量计算
        last_time = t0_end
        for _ in range(loop_count):
            # 这两个变量在每次新循环开始时都要重置
            segment_time = last_time

            for offset_minutes, temp in points:
                # 计算相对增量，避免直接用 offset_minutes 导致倒退
                delta = offset_minutes
                # 基于上一个真实时间点加上增量
                segment_time = segment_time + dt.timedelta(minutes=delta)
                        # 如果要增加的点和前一个点相同，则不增加新的点
                if not (segment_time==wave_times[-1] and temp==wave_temps[-1]):
                    wave_times.append(segment_time)
                    wave_temps.append(temp)

            # 循环结束后，last_time 更新为 segment_time
            last_time = segment_time

        # 6. 绘制红色折线
        # 先移除旧的 preview 线（如果有的话，标签为 "_wave_preview"）
        for ln in [l for l in self.ax.get_lines() if l.get_label() == "_wave_preview"]:
            ln.remove()

        # 绘新线
        (line,) = self.ax.plot(
            mdates.date2num(wave_times),
            wave_temps,
            '-',
            lw=2,
            color='red',
            label="_wave_preview"
        )
        # 确保网格、刻度不变
        self.canvas.draw_idle()

    def temp_cycle_start(self):
        """开始或停止温度循环"""
        if not self.chamber or not self.chamber.connected:  # 正确使用 connected 属性
            messagebox.showwarning("Not Connected", "Please connect chamber first!")
            return

        if self.cycle_running == False:
            # 切换状态
            if self.current_run_mode !=0:
                messagebox.showerror("Not in Constant Mode", "Please change mode first!")
                return
            self.cycle_running = True
            self.temp_cycle_start_btn.config(text="Wave Stop")

            # 1. 调用 wave_preview 生成红线
            self.wave_preview()

            # 2. 获取 _wave_preview 线的所有点
            preview_lines = [ln for ln in self.ax.get_lines() if ln.get_label() == "_wave_preview"]
            if not preview_lines:
                messagebox.showerror("Error", "Please input temp wave setting or load one!")
                return

            x_data = list(mdates.num2date(preview_lines[0].get_xdata()))
            y_data = list(preview_lines[0].get_ydata())

            # 3. 插值：在每对点之间插入 1 分钟间隔的点（温度线性插值）
            expanded_points = []
            for i in range(len(x_data) - 1):
                t1, t2 = x_data[i], x_data[i + 1]
                y1, y2 = y_data[i], y_data[i + 1]
                expanded_points.append((t1, y1))

                delta_min = int((t2 - t1).total_seconds() // 60)
                if delta_min > 1 and y1 != y2:
                    for m in range(1, delta_min):
                        interp_t = t1 + dt.timedelta(minutes=m)
                        interp_y = y1 + (y2 - y1) * (m / delta_min)
                        expanded_points.append((interp_t, interp_y))

            expanded_points.append((x_data[-1], y_data[-1]))

            # 存入属性供调度用
            self._cycle_points = expanded_points

            # 启动调度
            self._run_temp_cycle_loop()
        
        # 如果当前正在运行中，则停止运行，并修改标志位和按键
        else:
            # 停止循环
            self._stop_temp_cycle()
            self.cycle_running = False
            self.temp_cycle_start_btn.config(text="Wave Start")



    def _run_temp_cycle_loop(self):
        """每 5 秒检查是否有点匹配当前时间，若有则发送温度"""
        if not self.cycle_running:
            return

        if self.current_run_mode !=0:
            messagebox.showerror("Not in Constant Mode", "Running Stopped!")
            # 停止循环
            self._stop_temp_cycle()
            self.cycle_running = False
            self.temp_cycle_start_btn.config(text="Wave Start")
            return

        now = dt.datetime.now()
        now_key = (now.date(), now.hour, now.minute)

        to_send = []
        remain = []

        for t, temp in self._cycle_points:
            key = (t.date(), t.hour, t.minute)
            if key == now_key:
                to_send.append((t, temp))
            else:
                remain.append((t, temp))

        for t, temp in to_send:
            self.chamber.set_temp(temp)
            print(f"[Cycle] Sent temp: {temp} at {t.strftime('%H:%M')}")

        self._cycle_points = remain

        if not self._cycle_points:
            self._stop_temp_cycle()
            messagebox.showinfo("Temp Cycle", "Temp Cycle finished")
            return

        self.after(5000, self._run_temp_cycle_loop)


    def _stop_temp_cycle(self):
        """手动停止循环"""
        self.cycle_running = False
        self.temp_cycle_start_btn.config(text="Temp Cycle Start")
        self._cycle_points = []

    def center_now(self):
        self.center_now_without_draw()
        self.canvas.draw_idle()

    def center_now_without_draw(self):
        """将 X 轴中心移动到当前系统时间，保持跨度不变"""
        # 1. 取当前的 xlim（它们本身就是 Matplotlib 浮点天数）
        x0, x1 = self.ax.get_xlim()
        span = x1 - x0

        # 2. 获取当前时间对应的 Matplotlib 序数（浮点天数）
        now_dt = dt.datetime.now()
        now_num = mdates.date2num(now_dt)

        # 3. 重新设定 xlim，使当前时间居中
        new_left  = now_num - span / 2
        new_right = now_num + span / 2
        self.ax.set_xlim(new_left, new_right)

        # 4. 更新次刻度（如果有动态次刻度逻辑）
        self.update_minor_locator_without_draw()

    def mark_new_point(self):
        self.mark_new_point_without_draw()
        self.canvas.draw_idle()

    def mark_new_point_without_draw(self):

        # 1. 直接从 data_scatter 取最后一个点
        offsets = self.data_scatter.get_offsets()
        if len(offsets) == 0:
            return
        x_num, y_last = offsets[-1]
        # 同时需要一个 datetime 版本用于格式化文本
        x_last_dt = mdates.num2date(x_num)

        # 2. 移除上次 mark 产生的所有标记
        #    我们把上次的 circle/text 都缓存到 self._mark_artists 列表
        for art in getattr(self, '_mark_artists', []):
            art.remove()
        # 重置列表
        self._mark_artists = []

        # 3. 计算偏移（与 on_plot_click 保持一致）
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        dx = (x1 - x0) * 0.02
        dy = (y1 - y0) * 0.02

        # 4. 创建文本标签
        label = f"{x_last_dt.strftime('%H:%M:%S')}\n{y_last:.1f}℃"
        txt = self.ax.text(
            x_num + dx,
            y_last + dy,
            label,
            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
            verticalalignment='bottom',
            horizontalalignment='left'
        )
        txt.is_point_label = True
        self._mark_artists.append(txt)

        # 5. 创建黄色圆环
        #    半径设为 y 轴跨度的 5%
        radius = (y1 - y0) * 0.05
        #    由于横纵像素比不一定 1:1，用 display_ratio 做等比调整
        fig_w, fig_h = self.figure.get_figwidth(), self.figure.get_figheight()
        display_ratio = ( (x1 - x0) / fig_w ) / ( (y1 - y0) / fig_h )
        circ = Ellipse(
            (x_num, y_last),
            width=radius * display_ratio,
            height=radius,
            edgecolor='yellow',
            facecolor='none',
            linewidth=1.5
        )
        circ.is_highlight_circle = True
        self.ax.add_patch(circ)
        self._mark_artists.append(circ)

    def setup_axis(self):
        """初始化时调用一次：双层刻度与网格"""

        # —— Y 轴每 20°C —— 
        self.ax.yaxis.set_major_locator(MultipleLocator(20))

        # —— X 轴主刻度：每天 1 个，只显示月-日 —— 
        major_locator   = DayLocator()
        major_formatter = DateFormatter('%m-%d')
        self.ax.xaxis.set_major_locator(major_locator)
        self.ax.xaxis.set_major_formatter(major_formatter)

        # ―― X 轴次刻度：每 30 分钟 1 个，只显示时:分 ―― 
        minor_locator   = MinuteLocator(byminute=range(0, 60, 10))
        minor_formatter = DateFormatter('%H:%M')
        self.ax.xaxis.set_minor_locator(minor_locator)
        self.ax.xaxis.set_minor_formatter(minor_formatter)

        '''# ―― 动态次刻度 ――
        # 先给一个占位 formatter（后面 update_minor_locator 会设置 locator）  
        self.ax.xaxis.set_minor_formatter(DateFormatter('%H:%M'))
        # 然后马上用动态逻辑去选 locator  
        #self.update_minor_locator()'''

        # —— 网格：主/次刻度网格都画出来 —— 
        self.ax.grid(which='major', linestyle='--', alpha=0.5)
        self.ax.grid(which='minor', linestyle=':',  alpha=0.3)

        # —— 标签位置与偏移 —— 
        # 主（日期）放上面
        self.ax.xaxis.set_tick_params(which='major',
                                      labeltop=True, labelbottom=False, pad=10)
        # 次（时间）放下面
        self.ax.xaxis.set_tick_params(which='minor',
                                      labeltop=False, labelbottom=True, pad=5)
    
    def update_minor_locator(self):
        self.update_minor_locator_without_draw()
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()

    def update_minor_locator_without_draw(self):
        """
        根据当前 xlim 动态选择次刻度：
        - 如果跨度 < 1 天，仍用分钟刻度（10/20/30/60 分钟倍数）
        - 如果跨度 ≥ 1 天，改用小时刻度，间隔 = ceil(跨度天数 / 目标小时刻度数)
        目标次刻度数保持在 ~10 以内，保证不拥挤。
        """
        x0, x1 = self.ax.get_xlim()
        span_days = x1 - x0
        span_minutes = span_days * 24 * 60

        # 目标次刻度数
        target_ticks = 10

        if span_days < 1.0:
            # 跨度 < 1 天：继续用分钟倍数
            candidates = [240,120,60, 30, 20, 10,5,1]
            # 选出最接近 target_ticks 段数的分钟候选
            best = min(candidates,
                       key=lambda intr: abs(span_minutes / intr - target_ticks))
            # 如果间隔小于60分钟，则设置为分钟刻度
            if best<=60:
                self._minor_locator = MinuteLocator(byminute=range(0, 60, best))
            # 如果间隔为120或240，则设置为小时刻度
            else:
                self._minor_locator = HourLocator(interval=int(best/60))

            self.ax.xaxis.set_minor_locator(self._minor_locator)


        else:
            # 跨度 ≥ 1 天：用小时刻度
            # 计算跨度小时数
            span_hours = span_days * 24
            # 每隔多少小时一个刻度，使得到 ~target_ticks 段
            interval_hours = max(1, math.ceil(span_hours / target_ticks))
            self._minor_locator = HourLocator(interval=interval_hours)

            # 应用新的次刻度
            self.ax.xaxis.set_minor_locator(self._minor_locator)
            # 格式化标签：分钟刻度显示 HH:MM，小时刻度仅显示 HH
            fmt = '%H:%M' if span_days < 1.0 else '%H:%M'
            self.ax.xaxis.set_minor_formatter(mdates.DateFormatter(fmt))

    def on_plot_click(self, event):
        """处理鼠标点击事件"""
        if event.button != 1:  # 只处理左键点击
            return
        if event.inaxes != self.ax:  # 确保点击在绘图区域内
            return

        all_points = []
        # 获取所有线条上的点
        for line in self.ax.get_lines():
            xdata = mdates.num2date(line.get_xdata())  # 转换为datetime对象
            ydata = line.get_ydata()
            for x, y in zip(xdata, ydata):
                all_points.append((x, y))

        # 获取所有散点
        for collection in self.ax.collections:
            if isinstance(collection, matplotlib.collections.PathCollection):  # 确保是散点集合
                offsets = collection.get_offsets()
                for point in offsets:
                    x = mdates.num2date(point[0])  # 转换x坐标为datetime对象
                    y = point[1]
                    all_points.append((x, y))

        if not all_points:  # 如果没有点，直接返回
            return
        # 获取当前图表的时间范围和温度范围
        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        x_range = x_max - x_min  # 时间范围
        y_range = y_max - y_min  # 温度范围
        # 计算点击位置到所有点的距离
        click_time = mdates.num2date(event.xdata)
        min_dist = float('inf')
        nearest_point = None
        nearest_points = []

        for point in all_points:
            # 归一化时间差和温度差
            time_diff = abs((point[0] - click_time).total_seconds() / 60)
            temp_diff = abs(point[1] - event.ydata)
        
            # 将时间差和温度差都归一化到0-1范围内
            normalized_time_diff = time_diff / (x_range * 24 * 60)  # 转换为0-1范围
            normalized_temp_diff = temp_diff / y_range  # 转换为0-1范围
        
            # 使用归一化后的值计算距离
            dist = math.sqrt(normalized_time_diff**2 + normalized_temp_diff**2)
        
            if dist < min_dist:
                min_dist = dist
                nearest_points = [point]
            elif dist == min_dist:
                nearest_points.append(point)

        # 如果有多个最近点，选择时间最早的
        if nearest_points:
            nearest_point = min(nearest_points, key=lambda x: x[0])

        # 移除之前的标注和圆环（如果有）
        for txt in self.ax.texts:
            if hasattr(txt, 'is_point_label'):
                txt.remove()
    
        # 移除之前的圆环
        for circle in self.ax.patches:
            if hasattr(circle, 'is_highlight_circle'):
                circle.remove()

        # 添加新标注和圆环
        if nearest_point:
            # 添加文本标注
            label_text = f'{nearest_point[0].strftime("%H:%M:%S")} \n{nearest_point[1]:.1f}℃'
            # 计算标注位置的偏移量
            # 获取当前坐标轴的范围
            x_min, x_max = self.ax.get_xlim()
            y_min, y_max = self.ax.get_ylim()
            # 计算横纵比例
            x_range = x_max - x_min
            y_range = y_max - y_min
            # 计算偏移量（向右上方偏移）
            x_offset = x_range * 0.02  # x轴偏移2%
            y_offset = y_range * 0.02  # y轴偏移2%
        
            # 添加文本标注，位置在点的右上方
            text = self.ax.text(
                mdates.date2num(nearest_point[0]) + x_offset, 
                nearest_point[1] + y_offset,
                label_text,
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
                verticalalignment='bottom',
                horizontalalignment='left'
            )
            text.is_point_label = True

            # 计算坐标轴的实际比例
            fig_width = self.figure.get_figwidth()
            fig_height = self.figure.get_figheight()
        
            # 计算实际的显示比例
            display_ratio = (x_range / fig_width) / (y_range / fig_height)
        
            # 创建椭圆，根据显示比例调整横纵半径
            radius = (y_max - y_min) * 0.05  # 基础半径，可以根据需要调整
            ellipse = Ellipse(
                (mdates.date2num(nearest_point[0]), nearest_point[1]),
                width=radius * display_ratio,  # 横向半径
                height=radius,  # 纵向半径
                fill=False,
                color='orange',
                linewidth=0.5
            )
            ellipse.is_highlight_circle = True
            self.ax.add_patch(ellipse)
        
            self.canvas.draw_idle()

    def on_scroll(self, event):
        """鼠标滚轮缩放，中心在鼠标位置"""
        base_scale = 1.1
        # 确定是缩放 X 还是 Y
        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()
        xdata, ydata = event.xdata, event.ydata
        if xdata is None or ydata is None:
            return
        if event.button == 'up':
            scale_factor = 1 / base_scale
        elif event.button == 'down':
            scale_factor = base_scale
        else:
            return
        new_width  = (cur_xlim[1] - cur_xlim[0]) * scale_factor
        #new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
        relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
        #rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
        self.ax.set_xlim(xdata - new_width * (1 - relx),
                         xdata + new_width * (relx))
        # 滚轮仅对x轴生效
        #self.ax.set_ylim(ydata - new_height * (1 - rely), ydata + new_height * (rely))
        self.update_minor_locator()

    # ———— 缩放和平移函数 ————
    def zoom_y_in(self):
        y0, y1 = self.ax.get_ylim()
        dy = (y1 - y0) * 0.2
        self.ax.set_ylim(y0 + dy, y1 - dy)
        self.canvas.draw_idle()

    def zoom_y_out(self):
        y0, y1 = self.ax.get_ylim()
        dy = (y1 - y0) * 0.2
        self.ax.set_ylim(y0 - dy, y1 + dy)
        self.canvas.draw_idle()

    def pan_y_up(self):
        y0, y1 = self.ax.get_ylim()
        dy = (y1 - y0) * 0.1
        self.ax.set_ylim(y0 + dy, y1 + dy)
        self.canvas.draw_idle()

    def pan_y_down(self):
        y0, y1 = self.ax.get_ylim()
        dy = (y1 - y0) * 0.1
        self.ax.set_ylim(y0 - dy, y1 - dy)
        self.canvas.draw_idle()

    def zoom_x_in(self):
        x0, x1 = self.ax.get_xlim()
        dx = (x1 - x0) * 0.2
        self.ax.set_xlim(x0 + dx, x1 - dx)
        self.update_minor_locator()

    def zoom_x_out(self):
        x0, x1 = self.ax.get_xlim()
        dx = (x1 - x0) * 0.2
        self.ax.set_xlim(x0 - dx, x1 + dx)
        self.update_minor_locator()

    def pan_x_left(self):
        x0, x1 = self.ax.get_xlim()
        dx = (x1 - x0) * 0.1
        self.ax.set_xlim(x0 - dx, x1 - dx)
        self.update_minor_locator()

    def pan_x_right(self):
        x0, x1 = self.ax.get_xlim()
        dx = (x1 - x0) * 0.1
        self.ax.set_xlim(x0 + dx, x1 + dx)
        self.update_minor_locator()


    def plot_log_data(self):
        """只加载当前日志和上一个归档日志，绘制所有点，保留预览折线"""
        # 1. 找到所有日志文件，按修改时间排序
        pattern = os.path.join(os.getcwd(), "ChamCtrlLog*.txt")
        files = glob.glob(pattern)
        if not files:
            return
        files.sort(key=lambda f: os.path.getmtime(f))
        to_load = files[-2:] if len(files) >= 2 else files[-1:]

        # 3. 更新红色预览折线的数据（如果有的话）
        prev = None
        for ln in self.ax.get_lines():
            if ln.get_label() == "_wave_preview":
                prev = ln
                break
        if prev:
            # "prev" is the same as self.preview_line
            # but if you also programmatically change it elsewhere, just reset it here
            x, y = prev.get_xdata(), prev.get_ydata()
            self.preview_line.set_data(x, y)

        # 6. 读取日志数据并绘制蓝色散点
        times, temps = [], []
        for filepath in to_load:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) < 3:
                            continue
                        date_str, time_str = parts[2], parts[1]
                        try:
                            dt_obj = dt.datetime.strptime(f"{date_str} {time_str}","%Y-%m-%d %H:%M:%S")
                            temp = float(parts[0])
                        except ValueError:
                            continue
                        times.append(dt_obj)
                        temps.append(temp)
            except OSError:
                continue

        # ===== 时间过滤（仅保留最近 2 天内的数据）=====
        now = dt.datetime.now()
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0) - dt.timedelta(days=1)
        filtered = [(t, temp) for t, temp in zip(times, temps) if t >= cutoff]
        if not filtered:
            return
        times, temps = zip(*filtered)

        # ===== 动态抽样（最多 1000 个点）=====
        #max_points = 1000
        max_points = max(500, int(self.canvas.get_tk_widget().winfo_width() / 2))
        n = len(times)
        if n > max_points:
            idx = np.linspace(0, n - 1, max_points, dtype=int)
            times = [times[i] for i in idx]
            temps = [temps[i] for i in idx]

        #if times and temps:
            #self.ax.scatter(times, temps, s=10, color='blue')

        # 4. 更新蓝色散点的数据
        if times and temps:
            # Matplotlib wants Nx2 array of floats
            pts = [(mdates.date2num(t), temp) for t, temp in zip(times, temps)]
            self.data_scatter.set_offsets(pts)
        else:
            # no data → clear scatter
            #self.data_scatter.set_offsets([])
            self.data_scatter.set_offsets(np.empty((0, 2)))

        # 8. 若开启自动居中，则居中时间轴
        if self.auto_center == 1:
            self.center_now_without_draw()

        # 9. 若开启自动标记，则标记新出现的点
        if self.auto_mark == 1:
            self.mark_new_point_without_draw()

        # 7. 刷新画布
        self.canvas.draw_idle()

    def toggle_connection(self):
        """Connect/Disconnect 按钮回调，先从下拉框解析 IP"""
        # 如果还没连接，则尝试连接
        if not self.chamber:
            # 从选项中提取 IP（"ChamberXX:IP" → IP）
            selection = self.selected_ip.get()           # e.g. "Chamber06:10.166.156.173"
            port = int(self.selected_port.get())
            try:
                ip = selection.split(":", 1)[1]          # 拿到 "10.166.156.173"
            except IndexError:
                messagebox.showerror("Error", "Invalid selection")
                return
            # 尝试连接
            self.chamber = Chamber(ip,port)
            if self.chamber.connect():
                self.conn_btn.config(text="Disconnect")
                self._start_polling()
                if port!=502:
                    messagebox.showwarning("Attention!!!","Do not change any setting when you're not under port 502!\nDo not change any setting when you're not under port 502!\nDo not change any setting when you're not under port 502!\n\nContact the user and release 502 if you want to change the settings!\nContact the user and release 502 if you want to change the settings!\nContact the user and release 502 if you want to change the settings!")
            
            else:
                messagebox.showerror("Error", f"Could not connect to {ip}")
                self.chamber = None
        else:
            # 已连接时断开
            self._stop_polling()
            self.chamber.close()
            self.chamber = None
            self.conn_btn.config(text="Connect")
            self.status_var.set("disconnected")
            self.temp_var.set("--")


    def _start_polling(self):
        if not self._running:
            self._running = True
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

    def _stop_polling(self):
        self._running = False
        self._running = False
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2)  # 等待轮询线程结束，最多等待2秒

    def _poll_loop(self):
        if not self._running:
            return
        self.after(10000, self._poll_loop)
        # 1. 检查 chamber 是否有效 如果没有连接，退出
        if not self.chamber:
            return
        # 读取温箱状态
        status_code = self.chamber.get_run_status()
        if not self.chamber:
            return
        # 读取温箱温度
        temp_value = self.chamber.get_temp()
        target_temp_value = self.chamber.get_target_temp()
        run_mode_value = self.chamber.get_run_type()
        # 获取当前日期和时间
        now = dt.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        # 更新 UI
        self.after(0, lambda s=status_code, t=temp_value, tt=target_temp_value,rm=run_mode_value: self._update_ui(s, t,tt,rm))
        # 只要读到有效温度，就写入“温度 时间”，如果今天首次写入，则在末尾加上“ 日期”
        if temp_value is not None:
            # 日志滚动检查
            self.write_count += 1
            if self.write_count >= 1000:
                self._rollover_if_needed()
                self.write_count = 0

            # 每次都记录温度、时间和日期
            line = f"{temp_value:.2f} {time_str} {date_str}\n"
            self.log_file.write(line)
            self.log_file.flush()
            # 更新曲线：增量添加新点并重绘
            self.after(0, self.plot_log_data)


    def _rollover_if_needed(self):
        #当达到写入阈值后，检查文件大小并在 >10MB 时滚动日志
        try:
            self.log_file.flush()
            size = os.path.getsize(self.log_path)
        except OSError:
            size = 0
        # 如果超过 10 MB，执行滚动
        if size > 10 * 1024 * 1024:
            # 格式化时间戳
            ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            new_name = f"ChamCtrlLog-{ts}.txt"
            new_path = os.path.join(self.log_dir, new_name)
            # 关闭并重命名旧日志
            self.log_file.close()
            os.replace(self.log_path, new_path)
            # 打开新的日志文件
            self.log_file = open(self.log_path, "a+", encoding="utf-8")
            # 新文件第一次写入需包含日期
            #self.last_log_date = None
        # 重置写入计数
        self.write_count = 0

    def _update_ui(self, status_code, temp_value, target_temp_value, run_mode_value):
        # 更新运行状态
        text = ({0:"Constant Mode",1:"Viarable Mode",2:"Constant Humidity",3:"Viarable Humidity"}.get(run_mode_value, "error")+', '+{0:"Stop",1:"Run",2:"Pause"}.get(status_code, "error"))
        self.status_var.set(text)
        # 更新温度
        self.temp_var.set(f"{temp_value:.2f} °C" if temp_value is not None else "--")
        # 更新目标温度
        self.target_temp_label_var.set(f"{target_temp_value:.2f}" if target_temp_value is not None else "--")

    def on_set_temp(self):
        if not self.chamber:
            messagebox.showwarning("warning", "connect first")
            return
        try:
            t = float(self.set_temp_var.get())
        except ValueError:
            messagebox.showerror("error", "wrong temp number")
            return
        if self.chamber.set_temp(t):
            messagebox.showinfo("pass", f"temp set as {t} °C")
        else:
            messagebox.showerror("fail", "temp set fail")

    def update_datetime(self):
        now = dt.datetime.now()
        self.date_var.set(now.strftime("%Y-%m-%d"))
        self.time_var.set(now.strftime("%H:%M:%S"))
        self.after(1000, self.update_datetime)

    def on_close(self):
        """窗口关闭时，保存 IP 和波形设置文本，并退出"""
        config = configparser.ConfigParser()
        # 如果已有 ini，则先读取保留其它字段
        if os.path.exists(self.ini_path):
            try:
                config.read(self.ini_path, encoding="utf-8")
            except Exception:
                pass

        # 保存选中的 IP
        cur = self.selected_ip.get().strip()
        if cur:
            config["DEFAULT"]["last_ip"] = cur

        # 保存多行文本框内容
        wt = self.wave_text.get("1.0", tk.END).rstrip("\n")
        if wt:
            config["DEFAULT"]["wave_text"] = wt

        # 写回 ini 文件
        try:
            with open(self.ini_path, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            messagebox.showwarning("Warning", f"Failed to save settings:\n{e}")

        # 停止后台、关闭日志等原有逻辑
        self._stop_polling()
        if self.log_file:
            self.log_file.close()
        self.destroy()

if __name__ == "__main__":
    app = ChamberGUI()
    app.mainloop()

