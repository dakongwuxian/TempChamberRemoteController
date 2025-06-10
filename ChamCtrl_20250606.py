# -*- coding: gbk-*-
"""
��Ȩ���� (c) 2025 [����]

�����ChamCtrl�����¼�ơ��������Ϊ���˷���ҵ��;��Դ�������κ��˾������ʹ�á����ơ��޸ĺͷַ���������������ڸ��˷���ҵ��;��
������ҵ��;��������������Ƕ����ҵ��Ʒ���ṩ��ҵ����Ӫ���ַ��ȣ����������Ȼ�����ߵ�������ɡ�

�����������״���ṩ���������κ���ʾ��ʾ�ĵ����������������ڶ������ԡ��ض���;�������Լ�����Ȩ�ı�֤��
���κ�����£����߾�������ʹ�û��޷�ʹ�ñ�������������κ�ֱ�ӡ���ӡ�żȻ�����������𺦳е����Ρ�

������ҵ��Ȩ�����κ����ʣ�����ϵ��[dakongwuxian@gmail.com]
"""

import struct
import numpy
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
    def __init__(self, ip):
        self.ip = ip
        self.timeout = 5
        self.tcp_client = None
        self.connected = False # Initialize connected status

    def connect(self):
        if self.connected and self.tcp_client:
            try:
                # �򵥵س��Է���һ�����ֽڴ�����֤�����Ƿ���Ȼ��Ч
                # ����׳��ʵ�ֻ�ʹ��Modbus��Ϲ���
                # ��ʱ���ִ˼򵥵�����״̬��֤
                self.tcp_client.send(b'') 
                return True
            except (socket.error, OSError):
                self.close() # ���Ӷ�ʧ������״̬
                pass
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.ip, 502))
            self.tcp_client = sock
            self.connected = True  # ��������״̬
            print(f"Successfully connected to {self.ip}:502")
            return True
        except Exception as e:
            print(f"Connect fail: {e}")
            self.tcp_client = None
            self.connected = False  # ��������״̬
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
                return ""  # ��ʱ��û��Ӧ��
            return self.tcp_client.recv(512).decode()
        except Exception as e:
            print(f"Command fail: {e}")
            return ""'''

    def get_run_status(self):
        """
        ʹ�� Modbus FC=03 ��ȡ����״̬��
        �豸����״̬��ַΪ400��16����Ϊ00H C8H������Ϊ1���֡� [cite: 3]
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x00\xC8"
        read_length = b"\x00\x01"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Run Status Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # ������Ӧ���ݲ���
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
            # ������Ӧ���ݲ���
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
        ʹ�� Modbus FC=03 ��ȡ����״̬��
        �豸����״̬��ַΪ400��16����Ϊ00H C8H������Ϊ1���֡� [cite: 3]
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x00\xCA"
        read_length = b"\x00\x01"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Run Type Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # ������Ӧ���ݲ���
            if len(read_response) == 11:
                if read_response[:10] !=  b"\x00\x00\x00\x00\x00\x05\x01\x03\x02\x00":
                    return None
                value_byte = read_response[10:11]
                if value_byte in (b"\x00", b"\x01", b"\x02"):
                    type_value = int.from_bytes(value_byte, byteorder='big') 
                    print(f"Read run status: {type_value}")
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
            # ������Ӧ���ݲ���
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
                messagebox.showinfo("Run Type Set Pass", f"Set {run_type}: {status_map.get(run_type, 'UNKNOWN')} Pass.")
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
        ʹ�� Modbus FC=03 ��ȡ�����¶ȡ�
        �¶Ȳ���ֵ��ַΪ320��16����Ϊ00H A0H������Ϊ2���֡� [cite: 4]
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x00\xA0"
        read_length = b"\x00\x02"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Temp Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # ������Ӧ���ݲ���
            if len(read_response) == 13:
                if read_response[:9] !=  b"\x00\x00\x00\x00\x00\x07\x01\x03\x04":  
                    return 'Error'
                value_byte = read_response[9:13] # ���[9:13]ֻ��ȡ�� 10 11 12 13�ֽڣ���9��ʼȡ��12��������13

                temp_float_value = Chamber.hb4_to_float(value_byte[0],value_byte[1],value_byte[2],value_byte[3]) 
                print(f"Read temp registers: {value_byte[0],value_byte[1],value_byte[2],value_byte[3]}")
                print(f"Read temp : {temp_float_value}")
                return temp_float_value               
            else:
                return None

    def get_target_temp(self):
        """
        ʹ�� Modbus FC=03 ��ȡ�����趨�¶ȡ�
        """
        read_header = b"\x00\x00\x00\x00\x00\x06\x01"
        command_code = b"\x03"
        reg_address = b"\x06\xCE"
        read_length = b"\x00\x02"

        command_to_send = read_header + command_code + reg_address + read_length
        print('Get Target Temp Send: '+command_to_send.hex())

        read_response = self._send_modbus_request(command_to_send)

        if read_response:
            # ������Ӧ���ݲ���
            if len(read_response) == 13:
                if read_response[:9] !=  b"\x00\x00\x00\x00\x00\x07\x01\x03\x04":  
                    return 'Error'
                value_byte = read_response[9:13] # ���[9:13]ֻ��ȡ�� 10 11 12 13�ֽڣ���9��ʼȡ��12��������13

                temp_float_value = Chamber.hb4_to_float(value_byte[0],value_byte[1],value_byte[2],value_byte[3]) 
                print(f"Read target temp register: {value_byte[0],value_byte[1],value_byte[2],value_byte[3]}")
                print(f"Read target temp : {temp_float_value}")
                return temp_float_value               
            else:
                return None

    def set_temp(self, temp_value):
        """
        ʹ�� Modbus FC=10 ���������¶ȡ�
        �豸�¶ȸ���ֵ��ַΪ3484��16����Ϊ06H CEH������Ϊ2���֡� [cite: 5, 29]
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
            # ������Ӧ���ݲ���
            if len(write_response) == 12:
                if write_response !=  b"\x00\x00\x00\x00\x00\x06\x01\x10\x06\xCE\x00\x02":   # 00 00 00 00 00 06 01 10 06 CE 00 02
                    return False
                print(f"Set temperature to {temp_value}��C.")
                return True 
        print(f"Failed to set temperature��C.")
        return False

        # --- Modbus �������� ---------------------------------------------------------------------
 
    def _send_modbus_request(self, request_adu, timeout=0.5):
        """���� Modbus ADU ��������Ӧ��"""
        if not self.connect():
            return None
        try:
            self.tcp_client.sendall(request_adu)
            #self.tcp_client.sendall((request_adu+ "\r\n").encode('utf-8'))
            # ʹ�� select �ȴ����ݣ�����ʱ
            ready, _, _ = select.select([self.tcp_client], [], [], timeout)
            if not ready:
                print("Modbus response timeout.")
                return None
            return self.tcp_client.recv(512)
        except Exception as e:
            print(f"Command fail: {e}")
            return ""

class ChamberGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Temperature Chamber Controller")
        self.geometry("850x700")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # �����˵���
        self.menu_bar = tk.Menu(self)
        self.config(menu=self.menu_bar)

        # About �˵�
        self.about_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="About", menu=self.about_menu)
        self.about_menu.add_command(label="Developed by Xian Wu", state="disabled")
        self.about_menu.add_command(label="dakongwuxian@gmail.com", state="disabled")
        self.about_menu.add_command(label="vesion 20250606", state="disabled")

        # ��־�ļ�·��
        self.log_path = "ChamCtrlLog.txt"
        self.log_file = open(self.log_path, "a+", encoding="utf-8")

        # 1. ���������� Matplotlib ͼ��
        self.figure = Figure(figsize=(8, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        #self.ax.set_title("Temp Wave")
        self.ax.set_xlabel("Time")
        self.ax.set_ylabel("Temperature /��C")

        # 2. ���� X ��Ϊ 24 Сʱ��ȣ������ڵ�ǰʱ��
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

        # ���� �����Զ����ţ��������� scatter ����ı� xlim/ylim ���� 
        self.ax.set_autoscale_on(False)

        self._hour_locator = HourLocator(interval=1)
        self._minor_locator = MinuteLocator(byminute=range(0, 60, 10))
        self.ax.xaxis.set_minor_locator(self._minor_locator)
        self.ax.xaxis.set_minor_formatter(DateFormatter('%H:%M'))

        # ����һ�Σ����� Locator �� Grid
        self.setup_axis()

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        #self.update_minor_locator()

        # ��������¼�
        self.canvas.mpl_connect('button_press_event', self.on_plot_click)

        # �󶨹����¼�
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

        # ������������װ btn_frame �� ctrl_frame
        top_frame = ttk.Frame(self)
        top_frame.pack(fill=tk.X, padx=10, pady=5)

        # ��ť����
        # ��ť Frame����ࣩ
        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y,padx=(0,20))

        # Y �ᰴť
        ttk.Label(btn_frame, text="Y Axis��").grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="+", command=self.zoom_y_in).grid(row=0, column=1)
        ttk.Button(btn_frame, text="-", command=self.zoom_y_out).grid(row=0, column=2)
        ttk.Button(btn_frame, text="��", command=self.pan_y_up).grid(row=0, column=3)
        ttk.Button(btn_frame, text="��", command=self.pan_y_down).grid(row=0, column=4)

        # X �ᰴť
        ttk.Label(btn_frame, text="X Axis��").grid(row=1, column=0, padx=5)
        ttk.Button(btn_frame, text="+", command=self.zoom_x_in).grid(row=1, column=1)
        ttk.Button(btn_frame, text="-", command=self.zoom_x_out).grid(row=1, column=2)
        ttk.Button(btn_frame, text="��", command=self.pan_x_left).grid(row=1, column=3)
        ttk.Button(btn_frame, text="��", command=self.pan_x_right).grid(row=1, column=4)

        # ��ǰʱ����а�ť
        ttk.Button(btn_frame, text="Current to Center", command=self.center_now).grid(row=2, column=0, columnspan=2)

        # ���� Auto Center ��ѡ��
        self.auto_center_var = tk.IntVar(value=1)  # Ĭ�Ϲ�ѡ
        ttk.Checkbutton(btn_frame, text="Auto Center", variable=self.auto_center_var, command=self.on_auto_center_toggle).grid(row=2, column=2, columnspan=2)

        # ���� Auto Mark ��ѡ��
        self.auto_mark_var = tk.IntVar(value=1)  # Ĭ�Ϲ�ѡ
        ttk.Checkbutton(btn_frame, text="Auto Mark", variable=self.auto_mark_var, command=self.on_auto_mark_toggle).grid(row=2, column=4, columnspan=2)

        # ��¼��״̬������
        self.auto_center = 1
        self.auto_mark = 1

        # �Ƿ����ڱ��������еı�־λ
        self.cycle_running = False

        # ϵͳʱ����ʾ
        ttk.Label(btn_frame, text="Date��").grid(row=3, column=0, sticky="e")
        self.date_var = tk.StringVar(value="--")
        ttk.Label(btn_frame, textvariable=self.date_var).grid(row=3, column=1, sticky="w")
        ttk.Label(btn_frame, text="Time��").grid(row=3, column=2, sticky="e")
        self.time_var = tk.StringVar(value="--")
        ttk.Label(btn_frame, textvariable=self.time_var).grid(row=3, column=3, sticky="w")

        # 2. ���� GUI ����
        # ������� Frame���Ҳࣩ
        ctrl_frame = ttk.Frame(top_frame)
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # ���� IP ��ַѡ���б� 
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
        # IPѡ��
        ttk.Label(ctrl_frame, text="Select Chamber:").grid(row=0, column=0, sticky="w")

        # Combobox ֻ���������б��ɱ༭ :contentReference[oaicite:2]{index=2}
        self.selected_ip = tk.StringVar()
        self.ip_combo = ttk.Combobox(
            ctrl_frame,
            textvariable=self.selected_ip,
            values=self.ip_options,
            state="",
            width=23
        )
        self.ip_combo.grid(row=0, column=1, padx=5, sticky="w")
        # Ĭ��ѡ��һ��
        self.ip_combo.current(0)

        self.conn_btn = ttk.Button(ctrl_frame, text="Connect", command=self.toggle_connection)
        self.conn_btn.grid(row=0, column=2, padx=5)

        # ����״̬
        right_row_1_frame = ttk.Frame(ctrl_frame)
        right_row_1_frame.grid(row=1, column=0,columnspan=3, sticky="w")
        self.run_status_label = ttk.Label(right_row_1_frame, text="Status��")
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
        # ��ǰ�¶�
        ttk.Label(right_row_2_frame, text="Temperture ��").grid(row=0, column=0,padx=(0,5), sticky="w")
        self.temp_var = tk.StringVar(value="--")
        ttk.Label(right_row_2_frame, textvariable=self.temp_var,width = 9).grid(row=0, column=1,padx=(0,5), sticky="w")

        self.test_type_constant_btn = ttk.Button(right_row_2_frame, text="Constant Mode", command=lambda: self.chamber.set_run_type(0),width = 14)
        self.test_type_constant_btn.grid(row=0, column=3, padx=(0,5), sticky="w")

        self.test_type_viarable_btn = ttk.Button(right_row_2_frame, text="Viarable Mode", command=lambda: self.chamber.set_run_type(1),width = 14)
        self.test_type_viarable_btn.grid(row=0, column=4, padx=5, sticky="w")

        # Ŀ���¶�����
        right_row_3_frame = ttk.Frame(ctrl_frame)
        right_row_3_frame.grid(row=3, column=0,columnspan=3, sticky="w")
        ttk.Label(right_row_3_frame, text="Target temp��").grid(row=0, column=0,padx=(0,5), sticky="w")
        self.target_temp_label_var = tk.StringVar(value="--")
        ttk.Label(right_row_3_frame, textvariable=self.target_temp_label_var,width = 10).grid(row=0, column=1,padx=(0,5), sticky="w")
        self.set_temp_var = tk.StringVar()
        ttk.Entry(right_row_3_frame, textvariable=self.set_temp_var, width=10).grid(row=0, column=2,padx=(46,5), sticky="w")
        ttk.Button(right_row_3_frame, text="Set", command=self.on_set_temp).grid(row=0, column=3, padx=5)



        # �����ı����밴ť
        setting_frame = ttk.LabelFrame(self, text="Temp Wave Setting")
        setting_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=5)

        # �����ı�����࣬ռ�ݴ󲿷ֿ�ȣ�
        self.wave_text = ScrolledText(setting_frame, width=50, height=6)
        self.wave_text.grid(row=0, column=0, padx=(5,10), pady=5, sticky="nsew")

        # �Ҳఴť����
        btn_wave_frame = ttk.Frame(setting_frame)
        btn_wave_frame.grid(row=0, column=1, padx=5, pady=5, sticky="n")
        btn_wave_frame.columnconfigure(0, weight=1)

        # ��Wave Preview�� ��ť
        self.wave_preview_btn = ttk.Button(btn_wave_frame, text="Wave Preview", command=self.wave_preview)
        self.wave_preview_btn.grid(row=0, column=0, sticky="ew")

        # ��Temp Cycle Start�� ��ť
        self.temp_cycle_start_btn = ttk.Button(btn_wave_frame, text="Wave Start", command=self.temp_cycle_start)
        self.temp_cycle_start_btn.grid(row=1, column=0, sticky="ew")

        # ��Load Wave Setting�� ��ť
        self.load_wave_btn = ttk.Button(btn_wave_frame,text="Load Wave",command=self.load_wave_setting)
        self.load_wave_btn.grid(row=2, column=0, sticky="ew")

        # ��Save Wave Setting�� ��ť
        self.save_wave_btn = ttk.Button(btn_wave_frame,text="Save Wave",command=self.save_wave_setting)
        self.save_wave_btn.grid(row=3, column=0, sticky="ew")


        # ʹ�ı����밴ť������ˮƽ������
        setting_frame.columnconfigure(0, weight=1)
        setting_frame.columnconfigure(1, weight=0)

        # 3. ��־�ļ���ʼ��
        # ���������ȷ���ļ����ڣ�����ѯ�д���/д�����
        open(self.log_path, "a+", encoding="utf-8").close()
        # ���ڼ�¼д��ͬһ���ļ��Ĵ�����ÿ1000�μ�鵱ǰ�ļ���С
        self.write_count = 0

        # ������ѯ����
        self.chamber = None
        self._running = False
        self._poll_thread = None

        # ����ɢ�����
        self.wave_point_times = None
        self.wave_point_temps = None

        # ����ϵͳʱ�����
        self.after(1000, self.update_datetime)
        # �����������߻���
        self.plot_log_data()
        self.update_minor_locator()

        # Ini �ļ�·��
        self.ini_path = "ChamCtrlSetup.ini"
        self._load_last_ip()
        self._load_last_wave_text()

        # ���ڹرչ���
        self.protocol("WM_DELETE_WINDOW", self.on_close)

# �˶οհ����Էֿ����ͺ��� ---------------------------------------------------------------------------------------------------------------















# �˶οհ����Էֿ����ͺ��� ---------------------------------------------------------------------------------------------------------------

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
        """����ʱ�����ϴα���Ĳ��������ı�"""
        if not os.path.exists(self.ini_path):
            return
        config = configparser.ConfigParser()
        try:
            config.read(self.ini_path, encoding="utf-8")
            wt = config["DEFAULT"].get("wave_text", "")
            if wt:
                # ��������ı���
                self.wave_text.delete("1.0", tk.END)
                self.wave_text.insert(tk.END, wt)
        except Exception:
            pass
        
    def load_wave_setting(self):
        """�� .txt �ļ����ز������õ������ı���"""
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

        # ����ȡ�����ݷ�������ı���
        self.wave_text.delete("1.0", tk.END)
        self.wave_text.insert(tk.END, content)

    def save_wave_setting(self):
        """�������ı������ݱ��浽ָ�� .txt �ļ�"""
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

        # 1. ���� start temp��loop count �ͽڵ��б�
        # ʾ����ʽ��(start temp 25C)-(loop count 10)-[(0,25C)-(55,80C)-��]
        m_start = re.search(r'start temp\s+(-?\d+)C', text)
        m_loop  = re.search(r'loop count\s+(\d+)', text)
        nodes   = re.findall(r'\((\d+),\s*(-?\d+)C\)', text)

        if not (m_start and m_loop and nodes):
            messagebox.showerror("Error", "Wave format invalid")
            return

        start_temp = int(m_start.group(1))
        loop_count = int(m_loop.group(1))
        # ת�� [(minutes, temp), ...]
        points = [(int(mins), int(tmp)) for mins, tmp in nodes]

        # 1. �����һ�Σ���ǰ�¶ȵ� start_temp
        now_dt    = dt.datetime.now()
        base_time = now_dt
        try:
            s = self.temp_var.get().strip()
            # ȥ���ȷ��ţ�֧�֡��桱�͡���C������д����
            s = s.rstrip("���C")  
            cur_temp = float(s)
        except (ValueError, TypeError):
            cur_temp = 25.0
        delta_temp = start_temp - cur_temp
        minutes0   = abs(delta_temp)
        t0_end     = base_time + dt.timedelta(minutes=minutes0)

        wave_times = [base_time]
        wave_temps = [cur_temp]
        # ���Ҫ���ӵĵ��ǰһ������ͬ���������µĵ�
        if not (t0_end==wave_times[-1] and start_temp==wave_temps[-1]):
            wave_times.append(t0_end)
            wave_temps.append(start_temp)

        # 2. ѭ���Σ��ϸ�����������
        last_time = t0_end
        for _ in range(loop_count):
            # ������������ÿ����ѭ����ʼʱ��Ҫ����
            segment_time = last_time

            for offset_minutes, temp in points:
                # �����������������ֱ���� offset_minutes ���µ���
                delta = offset_minutes
                # ������һ����ʵʱ����������
                segment_time = segment_time + dt.timedelta(minutes=delta)
                        # ���Ҫ���ӵĵ��ǰһ������ͬ���������µĵ�
                if not (segment_time==wave_times[-1] and temp==wave_temps[-1]):
                    wave_times.append(segment_time)
                    wave_temps.append(temp)

            # ѭ��������last_time ����Ϊ segment_time
            last_time = segment_time

        # 6. ���ƺ�ɫ����
        # ���Ƴ��ɵ� preview �ߣ�����еĻ�����ǩΪ "_wave_preview"��
        for ln in [l for l in self.ax.get_lines() if l.get_label() == "_wave_preview"]:
            ln.remove()

        # ������
        (line,) = self.ax.plot(
            mdates.date2num(wave_times),
            wave_temps,
            '-',
            lw=2,
            color='red',
            label="_wave_preview"
        )
        # ȷ�����񡢿̶Ȳ���
        self.canvas.draw_idle()

    def temp_cycle_start(self):
        """��ʼ��ֹͣ�¶�ѭ��"""
        if not self.chamber or not self.chamber.connected:  # ��ȷʹ�� connected ����
            messagebox.showwarning("Not Connected", "Please connect chamber first!")
            return

        if self.cycle_running == False:
            # �л�״̬
            self.cycle_running = True
            self.temp_cycle_start_btn.config(text="Wave Stop")

            # 1. ���� wave_preview ���ɺ���
            self.wave_preview()

            # 2. ��ȡ _wave_preview �ߵ����е�
            preview_lines = [ln for ln in self.ax.get_lines() if ln.get_label() == "_wave_preview"]
            if not preview_lines:
                messagebox.showerror("Error", "Please input temp wave setting or load one!")
                return

            x_data = list(mdates.num2date(preview_lines[0].get_xdata()))
            y_data = list(preview_lines[0].get_ydata())

            # 3. ��ֵ����ÿ�Ե�֮����� 1 ���Ӽ���ĵ㣨�¶����Բ�ֵ��
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

            # �������Թ�������
            self._cycle_points = expanded_points

            # ��������
            self._run_temp_cycle_loop()
        
        # �����ǰ���������У���ֹͣ���У����޸ı�־λ�Ͱ���
        else:
            # ֹͣѭ��
            self._stop_temp_cycle()
            self.cycle_running = False
            self.temp_cycle_start_btn.config(text="Wave Start")



    def _run_temp_cycle_loop(self):
        """ÿ 5 �����Ƿ��е�ƥ�䵱ǰʱ�䣬���������¶�"""
        if not self.cycle_running:
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
        """�ֶ�ֹͣѭ��"""
        self.cycle_running = False
        self.temp_cycle_start_btn.config(text="Temp Cycle Start")
        self._cycle_points = []

    def center_now(self):
        self.center_now_without_draw()
        self.canvas.draw_idle()

    def center_now_without_draw(self):
        """�� X �������ƶ�����ǰϵͳʱ�䣬���ֿ�Ȳ���"""
        # 1. ȡ��ǰ�� xlim�����Ǳ������ Matplotlib ����������
        x0, x1 = self.ax.get_xlim()
        span = x1 - x0

        # 2. ��ȡ��ǰʱ���Ӧ�� Matplotlib ����������������
        now_dt = dt.datetime.now()
        now_num = mdates.date2num(now_dt)

        # 3. �����趨 xlim��ʹ��ǰʱ�����
        new_left  = now_num - span / 2
        new_right = now_num + span / 2
        self.ax.set_xlim(new_left, new_right)

        # 4. ���´ο̶ȣ�����ж�̬�ο̶��߼���
        self.update_minor_locator_without_draw()

    def mark_new_point(self):
        self.mark_new_point_without_draw()
        self.canvas.draw_idle()

    def mark_new_point_without_draw(self):

        # 1. ֱ�Ӵ� data_scatter ȡ���һ����
        offsets = self.data_scatter.get_offsets()
        if len(offsets) == 0:
            return
        x_num, y_last = offsets[-1]
        # ͬʱ��Ҫһ�� datetime �汾���ڸ�ʽ���ı�
        x_last_dt = mdates.num2date(x_num)

        # 2. �Ƴ��ϴ� mark ���������б��
        #    ���ǰ��ϴε� circle/text �����浽 self._mark_artists �б�
        for art in getattr(self, '_mark_artists', []):
            art.remove()
        # �����б�
        self._mark_artists = []

        # 3. ����ƫ�ƣ��� on_plot_click ����һ�£�
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        dx = (x1 - x0) * 0.02
        dy = (y1 - y0) * 0.02

        # 4. �����ı���ǩ
        label = f"{x_last_dt.strftime('%H:%M:%S')}\n{y_last:.1f}��"
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

        # 5. ������ɫԲ��
        #    �뾶��Ϊ y ���ȵ� 5%
        radius = (y1 - y0) * 0.05
        #    ���ں������رȲ�һ�� 1:1���� display_ratio ���ȱȵ���
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
        """��ʼ��ʱ����һ�Σ�˫��̶�������"""

        # ���� Y ��ÿ 20��C ���� 
        self.ax.yaxis.set_major_locator(MultipleLocator(20))

        # ���� X �����̶ȣ�ÿ�� 1 ����ֻ��ʾ��-�� ���� 
        major_locator   = DayLocator()
        major_formatter = DateFormatter('%m-%d')
        self.ax.xaxis.set_major_locator(major_locator)
        self.ax.xaxis.set_major_formatter(major_formatter)

        # �D�D X ��ο̶ȣ�ÿ 30 ���� 1 ����ֻ��ʾʱ:�� �D�D 
        minor_locator   = MinuteLocator(byminute=range(0, 60, 10))
        minor_formatter = DateFormatter('%H:%M')
        self.ax.xaxis.set_minor_locator(minor_locator)
        self.ax.xaxis.set_minor_formatter(minor_formatter)

        '''# �D�D ��̬�ο̶� �D�D
        # �ȸ�һ��ռλ formatter������ update_minor_locator ������ locator��  
        self.ax.xaxis.set_minor_formatter(DateFormatter('%H:%M'))
        # Ȼ�������ö�̬�߼�ȥѡ locator  
        #self.update_minor_locator()'''

        # ���� ������/�ο̶����񶼻����� ���� 
        self.ax.grid(which='major', linestyle='--', alpha=0.5)
        self.ax.grid(which='minor', linestyle=':',  alpha=0.3)

        # ���� ��ǩλ����ƫ�� ���� 
        # �������ڣ�������
        self.ax.xaxis.set_tick_params(which='major',
                                      labeltop=True, labelbottom=False, pad=10)
        # �Σ�ʱ�䣩������
        self.ax.xaxis.set_tick_params(which='minor',
                                      labeltop=False, labelbottom=True, pad=5)
    
    def update_minor_locator(self):
        self.update_minor_locator_without_draw()
        if hasattr(self, 'canvas'):
            self.canvas.draw_idle()

    def update_minor_locator_without_draw(self):
        """
        ���ݵ�ǰ xlim ��̬ѡ��ο̶ȣ�
        - ������ < 1 �죬���÷��ӿ̶ȣ�10/20/30/60 ���ӱ�����
        - ������ �� 1 �죬����Сʱ�̶ȣ���� = ceil(������� / Ŀ��Сʱ�̶���)
        Ŀ��ο̶��������� ~10 ���ڣ���֤��ӵ����
        """
        x0, x1 = self.ax.get_xlim()
        span_days = x1 - x0
        span_minutes = span_days * 24 * 60

        # Ŀ��ο̶���
        target_ticks = 10

        if span_days < 1.0:
            # ��� < 1 �죺�����÷��ӱ���
            candidates = [240,120,60, 30, 20, 10,5,1]
            # ѡ����ӽ� target_ticks �����ķ��Ӻ�ѡ
            best = min(candidates,
                       key=lambda intr: abs(span_minutes / intr - target_ticks))
            # ������С��60���ӣ�������Ϊ���ӿ̶�
            if best<=60:
                self._minor_locator = MinuteLocator(byminute=range(0, 60, best))
            # ������Ϊ120��240��������ΪСʱ�̶�
            else:
                self._minor_locator = HourLocator(interval=int(best/60))

            self.ax.xaxis.set_minor_locator(self._minor_locator)


        else:
            # ��� �� 1 �죺��Сʱ�̶�
            # ������Сʱ��
            span_hours = span_days * 24
            # ÿ������Сʱһ���̶ȣ�ʹ�õ� ~target_ticks ��
            interval_hours = max(1, math.ceil(span_hours / target_ticks))
            self._minor_locator = HourLocator(interval=interval_hours)

            # Ӧ���µĴο̶�
            self.ax.xaxis.set_minor_locator(self._minor_locator)
            # ��ʽ����ǩ�����ӿ̶���ʾ HH:MM��Сʱ�̶Ƚ���ʾ HH
            fmt = '%H:%M' if span_days < 1.0 else '%H:%M'
            self.ax.xaxis.set_minor_formatter(mdates.DateFormatter(fmt))

    def on_plot_click(self, event):
        """����������¼�"""
        if event.button != 1:  # ֻ����������
            return
        if event.inaxes != self.ax:  # ȷ������ڻ�ͼ������
            return

        all_points = []
        # ��ȡ���������ϵĵ�
        for line in self.ax.get_lines():
            xdata = mdates.num2date(line.get_xdata())  # ת��Ϊdatetime����
            ydata = line.get_ydata()
            for x, y in zip(xdata, ydata):
                all_points.append((x, y))

        # ��ȡ����ɢ��
        for collection in self.ax.collections:
            if isinstance(collection, matplotlib.collections.PathCollection):  # ȷ����ɢ�㼯��
                offsets = collection.get_offsets()
                for point in offsets:
                    x = mdates.num2date(point[0])  # ת��x����Ϊdatetime����
                    y = point[1]
                    all_points.append((x, y))

        if not all_points:  # ���û�е㣬ֱ�ӷ���
            return
        # ��ȡ��ǰͼ���ʱ�䷶Χ���¶ȷ�Χ
        x_min, x_max = self.ax.get_xlim()
        y_min, y_max = self.ax.get_ylim()
        x_range = x_max - x_min  # ʱ�䷶Χ
        y_range = y_max - y_min  # �¶ȷ�Χ
        # ������λ�õ����е�ľ���
        click_time = mdates.num2date(event.xdata)
        min_dist = float('inf')
        nearest_point = None
        nearest_points = []

        for point in all_points:
            # ��һ��ʱ�����¶Ȳ�
            time_diff = abs((point[0] - click_time).total_seconds() / 60)
            temp_diff = abs(point[1] - event.ydata)
        
            # ��ʱ�����¶Ȳ��һ����0-1��Χ��
            normalized_time_diff = time_diff / (x_range * 24 * 60)  # ת��Ϊ0-1��Χ
            normalized_temp_diff = temp_diff / y_range  # ת��Ϊ0-1��Χ
        
            # ʹ�ù�һ�����ֵ�������
            dist = math.sqrt(normalized_time_diff**2 + normalized_temp_diff**2)
        
            if dist < min_dist:
                min_dist = dist
                nearest_points = [point]
            elif dist == min_dist:
                nearest_points.append(point)

        # ����ж������㣬ѡ��ʱ�������
        if nearest_points:
            nearest_point = min(nearest_points, key=lambda x: x[0])

        # �Ƴ�֮ǰ�ı�ע��Բ��������У�
        for txt in self.ax.texts:
            if hasattr(txt, 'is_point_label'):
                txt.remove()
    
        # �Ƴ�֮ǰ��Բ��
        for circle in self.ax.patches:
            if hasattr(circle, 'is_highlight_circle'):
                circle.remove()

        # ����±�ע��Բ��
        if nearest_point:
            # ����ı���ע
            label_text = f'{nearest_point[0].strftime("%H:%M:%S")} \n{nearest_point[1]:.1f}��'
            # �����עλ�õ�ƫ����
            # ��ȡ��ǰ������ķ�Χ
            x_min, x_max = self.ax.get_xlim()
            y_min, y_max = self.ax.get_ylim()
            # ������ݱ���
            x_range = x_max - x_min
            y_range = y_max - y_min
            # ����ƫ�����������Ϸ�ƫ�ƣ�
            x_offset = x_range * 0.02  # x��ƫ��2%
            y_offset = y_range * 0.02  # y��ƫ��2%
        
            # ����ı���ע��λ���ڵ�����Ϸ�
            text = self.ax.text(
                mdates.date2num(nearest_point[0]) + x_offset, 
                nearest_point[1] + y_offset,
                label_text,
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'),
                verticalalignment='bottom',
                horizontalalignment='left'
            )
            text.is_point_label = True

            # �����������ʵ�ʱ���
            fig_width = self.figure.get_figwidth()
            fig_height = self.figure.get_figheight()
        
            # ����ʵ�ʵ���ʾ����
            display_ratio = (x_range / fig_width) / (y_range / fig_height)
        
            # ������Բ��������ʾ�����������ݰ뾶
            radius = (y_max - y_min) * 0.05  # �����뾶�����Ը�����Ҫ����
            ellipse = Ellipse(
                (mdates.date2num(nearest_point[0]), nearest_point[1]),
                width=radius * display_ratio,  # ����뾶
                height=radius,  # ����뾶
                fill=False,
                color='orange',
                linewidth=0.5
            )
            ellipse.is_highlight_circle = True
            self.ax.add_patch(ellipse)
        
            self.canvas.draw_idle()

    def on_scroll(self, event):
        """���������ţ����������λ��"""
        base_scale = 1.1
        # ȷ�������� X ���� Y
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
        # ���ֽ���x����Ч
        #self.ax.set_ylim(ydata - new_height * (1 - rely), ydata + new_height * (rely))
        self.update_minor_locator()

    # �������� ���ź�ƽ�ƺ��� ��������
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
        """ֻ���ص�ǰ��־����һ���鵵��־���������е㣬����Ԥ������"""
        # 1. �ҵ�������־�ļ������޸�ʱ������
        pattern = os.path.join(os.getcwd(), "ChamCtrlLog*.txt")
        files = glob.glob(pattern)
        if not files:
            return
        files.sort(key=lambda f: os.path.getmtime(f))
        to_load = files[-2:] if len(files) >= 2 else files[-1:]

        # 3. ���º�ɫԤ�����ߵ����ݣ�����еĻ���
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

        # 6. ��ȡ��־���ݲ�������ɫɢ��
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

        #if times and temps:
            #self.ax.scatter(times, temps, s=10, color='blue')

        # 4. ������ɫɢ�������
        if times and temps:
            # Matplotlib wants Nx2 array of floats
            pts = [(mdates.date2num(t), temp) for t, temp in zip(times, temps)]
            self.data_scatter.set_offsets(pts)
        else:
            # no data �� clear scatter
            self.data_scatter.set_offsets([])

        # 8. �������Զ����У������ʱ����
        if self.auto_center == 1:
            self.center_now_without_draw()

        # 9. �������Զ���ǣ������³��ֵĵ�
        if self.auto_mark == 1:
            self.mark_new_point_without_draw()

        # 7. ˢ�»���
        self.canvas.draw_idle()

    def toggle_connection(self):
        """Connect/Disconnect ��ť�ص����ȴ���������� IP"""
        # �����û���ӣ���������
        if not self.chamber:
            # ��ѡ������ȡ IP��"ChamberXX:IP" �� IP��
            selection = self.selected_ip.get()           # e.g. "Chamber06:10.166.156.173"
            try:
                ip = selection.split(":", 1)[1]          # �õ� "10.166.156.173"
            except IndexError:
                messagebox.showerror("Error", "Invalid selection")
                return
            # ��������
            self.chamber = Chamber(ip)
            if self.chamber.connect():
                self.conn_btn.config(text="Disconnect")
                self._start_polling()
            else:
                messagebox.showerror("Error", f"Could not connect to {ip}")
                self.chamber = None
        else:
            # ������ʱ�Ͽ�
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
            self._poll_thread.join(timeout=2)  # �ȴ���ѯ�߳̽��������ȴ�2��

    def _poll_loop(self):
        if not self._running:
            return
        self.after(10000, self._poll_loop)
        # 1. ��� chamber �Ƿ���Ч ���û�����ӣ��˳�
        if not self.chamber:
            return
        # ��ȡ����״̬
        status_code = self.chamber.get_run_status()
        if not self.chamber:
            return
        # ��ȡ�����¶�
        temp_value = self.chamber.get_temp()
        target_temp_value = self.chamber.get_target_temp()
        run_mode_value = self.chamber.get_run_type()
        # ��ȡ��ǰ���ں�ʱ��
        now = dt.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")
        # ���� UI
        self.after(0, lambda s=status_code, t=temp_value, tt=target_temp_value,rm=run_mode_value: self._update_ui(s, t,tt,rm))
        # ֻҪ������Ч�¶ȣ���д�롰�¶� ʱ�䡱����������״�д�룬����ĩβ���ϡ� ���ڡ�
        if temp_value is not None:
            # ��־�������
            self.write_count += 1
            if self.write_count >= 1000:
                self._rollover_if_needed()
                self.write_count = 0

            # ÿ�ζ���¼�¶ȡ�ʱ�������
            line = f"{temp_value:.2f} {time_str} {date_str}\n"
            self.log_file.write(line)
            self.log_file.flush()
            # �������ߣ���������µ㲢�ػ�
            self.after(0, self.plot_log_data)


    def _rollover_if_needed(self):
        #���ﵽд����ֵ�󣬼���ļ���С���� >10MB ʱ������־
        try:
            self.log_file.flush()
            size = os.path.getsize(self.log_path)
        except OSError:
            size = 0
        # ������� 10 MB��ִ�й���
        if size > 10 * 1024 * 1024:
            # ��ʽ��ʱ���
            ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            new_name = f"ChamCtrlLog-{ts}.txt"
            new_path = os.path.join(self.log_dir, new_name)
            # �رղ�����������־
            self.log_file.close()
            os.replace(self.log_path, new_path)
            # ���µ���־�ļ�
            self.log_file = open(self.log_path, "a+", encoding="utf-8")
            # ���ļ���һ��д�����������
            #self.last_log_date = None
        # ����д�����
        self.write_count = 0

    def _update_ui(self, status_code, temp_value, target_temp_value, run_mode_value):
        # ��������״̬
        text = ({0:"Constant Mode",1:"Viarable Mode",2:"Constant Humidity",3:"Viarable Humidity"}.get(run_mode_value, "error")+', '+{0:"Stop",1:"Run",2:"Pause"}.get(status_code, "error"))
        self.status_var.set(text)
        # �����¶�
        self.temp_var.set(f"{temp_value:.2f} ��C" if temp_value is not None else "--")
        # ����Ŀ���¶�
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
            messagebox.showinfo("pass", f"temp set as {t} ��C")
        else:
            messagebox.showerror("fail", "temp set fail")

    def update_datetime(self):
        now = dt.datetime.now()
        self.date_var.set(now.strftime("%Y-%m-%d"))
        self.time_var.set(now.strftime("%H:%M:%S"))
        self.after(1000, self.update_datetime)

    def on_close(self):
        """���ڹر�ʱ������ IP �Ͳ��������ı������˳�"""
        config = configparser.ConfigParser()
        # ������� ini�����ȶ�ȡ���������ֶ�
        if os.path.exists(self.ini_path):
            try:
                config.read(self.ini_path, encoding="utf-8")
            except Exception:
                pass

        # ����ѡ�е� IP
        cur = self.selected_ip.get().strip()
        if cur:
            config["DEFAULT"]["last_ip"] = cur

        # ��������ı�������
        wt = self.wave_text.get("1.0", tk.END).rstrip("\n")
        if wt:
            config["DEFAULT"]["wave_text"] = wt

        # д�� ini �ļ�
        try:
            with open(self.ini_path, "w", encoding="utf-8") as f:
                config.write(f)
        except Exception as e:
            messagebox.showwarning("Warning", f"Failed to save settings:\n{e}")

        # ֹͣ��̨���ر���־��ԭ���߼�
        self._stop_polling()
        if self.log_file:
            self.log_file.close()
        self.destroy()

if __name__ == "__main__":
    app = ChamberGUI()
    app.mainloop()
