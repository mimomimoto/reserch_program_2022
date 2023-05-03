from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Value, Array, Process
from gps3 import gps3
import cv2
import serial
import math
import pandas as pd
import numpy.polynomial.polynomial as P
import datetime
import pickle
import npsocket
from npsocket import SocketNumpyArray
import struct
import requests
import re 
import time
from ctypes import c_wchar_p
import RPi.GPIO as GPIO
node = "A"


def get_gps(new_x, new_y, path):
    sock_sender = SocketNumpyArray()
    sock_sender.initialize_sender('169.254.178.200', 8800)
    gps_socket = gps3.GPSDSocket()
    data_stream = gps3.DataStream()
    gps_socket.connect()
    c = gps_socket.watch()
    print(c)
    
    for new_data in gps_socket:
        dt_now = datetime.datetime.now()
        dt_now = dt_now.strftime('%Y-%m-%d %H:%M:%S')
        if (new_data):
            data_stream.unpack(new_data)
            lat = data_stream.TPV['lat']
            lon = data_stream.TPV['lon']
            if lat == 'n/a' and lon == 'n/a':
                lat = 0.0
                lon = 0.0
            data = pickle.dumps(node + ',' + dt_now + ',' + str(lat) + ',' + str(lon) + ',' + str(new_x.value) + ',' + str(new_y.value) + ',' + path.value.decode('utf-8'))
            message_size = struct.pack("I", len(data))
            sock_sender.socket.sendall(message_size + data)
            print(node, dt_now, lat, lon, new_x.value, new_y.value, path.value.decode('utf-8'))

def calcurate_location_from_imu(new_x, new_y):
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17, GPIO.OUT, initial=GPIO.LOW)
    time.sleep(2)
    GPIO.output(17, 1)
    time.sleep(2)
    ser = serial.Serial('/dev/ttyACM0', 9600)
    ini = []
    ini.append([0, 0])
    raw_yaw_data_heading = 0
    raw_yaw_data_time = []
    raw_yaw_data_heading = []

    i = 0

    print('Calibrate...')
    while True:

        data = str(ser.readline())
        data = data[2:][:-5]
        data = data.split(',')
        x_acc = float(data[0])
        heading = float(data[4])
        time_n = float(data[5])
        base_time = float(data[6])
        base_heading = float(data[7])

        pro_time = time_n - base_time

        tmp_heading = heading - base_heading
        raw_yaw_data_time.append(pro_time)
        raw_yaw_data_heading.append(tmp_heading)

        if (pro_time > 10000):
            correct_base_time = pro_time
            correct_base_heading = tmp_heading
            break


    raw_yaw_data_time = pd.DataFrame(raw_yaw_data_time)
    raw_yaw_data_heading = pd.DataFrame(raw_yaw_data_heading)
    raw_yaw_data_time = raw_yaw_data_time[1:]
    raw_yaw_data_heading = raw_yaw_data_heading[1:]
    raw_yaw_data_time[0][2:] = raw_yaw_data_time[0][2:] - raw_yaw_data_time[0][1]
    raw_yaw_data_time[0][1] = 0
    raw_yaw_data_heading[0][2:] = raw_yaw_data_heading[0][2:] - \
        raw_yaw_data_heading[0][1]
    raw_yaw_data_heading[0][1] = 0
    coef = P.polyfit(raw_yaw_data_time[0], raw_yaw_data_heading[0], 1)

    print('Calibration done!!')


    while True:
        i += 1

        data = str(ser.readline())
        data = data[2:][:-5]
        data = data.split(',')
        x_acc = float(data[0])
        heading = float(data[4])
        time_n = float(data[5])
        base_time = float(data[6])
        base_heading = float(data[7])

        pro_time = time_n - base_time - correct_base_time


        tmp_heading = heading - base_heading - correct_base_heading

        if (tmp_heading < 0):
            tmp_heading = 360 + tmp_heading

        error_heading = (coef[0] +
                        coef[1] * pro_time) % 360.0

        correct_heading = tmp_heading - error_heading

        if (correct_heading < 0):
            correct_heading = 360 + correct_heading

        def_time = 8.5/1000.0

        new_x.value = ini[-1][0] + x_acc * 9.8 *\
            math.cos(math.radians(correct_heading)) * \
            def_time * def_time / 2
        new_y.value = ini[-1][1] + x_acc * 9.8 *\
            math.sin(math.radians(correct_heading)) * \
            def_time * def_time / 2
        ini.append([new_x.value, new_y.value])

def get_img_data(path):
    sock_sender = SocketNumpyArray()
    sock_sender.initialize_sender('169.254.178.200', 8800)
    while True:
        dt_now = datetime.datetime.now()
        path.value = bytes(dt_now.strftime('%Y-%m-%d %H:%M:%S'), 'utf-8')



        #画像撮影モード変更
        mode_get = requests.get('http://192.168.1.254/?custom=1&cmd=3001&par=0')

        #画像撮影
        response = requests.get('http://192.168.1.254/?custom=1&cmd=1001')
        path_img = response.text
        path_img = re.search(r':(.+)</FPATH>', path_img).group(1)
        path_img = path_img.replace('\\', '/')

        #画像送信モード変更 
        mode_trans = requests.get('http://192.168.1.254/?custom=1&cmd=3001&par=2')

        #画像取得
        trans_img = requests.get('http://192.168.1.254' + path_img + '?custom=1&cmd=4002')

        #パス名送信
        data = pickle.dumps(path.value.decode('utf-8') + '.jpg')
        message_size = struct.pack("I", len(data))
        sock_sender.socket.sendall(message_size + data)
        
        #画像送信
        data = pickle.dumps(trans_img.content)
        message_size = struct.pack("I", len(data))
        sock_sender.socket.sendall(message_size + data)

        #全てのファイル削除
        delete_file = requests.get('http://192.168.1.254/?custom=1&cmd=4004')
        
        time.sleep(5)


def main():
    new_x = Value('d', 0.0)
    new_y = Value('d', 0.0)

    dt_now = datetime.datetime.now()
    dt_now = bytes(dt_now.strftime('%Y-%m-%d %H:%M:%S'), 'utf-8')
    path = Array('c', dt_now)

    p_calcurate_location_from_imu = Process(target=calcurate_location_from_imu, args=(new_x, new_y))
    p_calcurate_location_from_imu.start()

    p_get_gps = Process(target=get_gps, args=(new_x, new_y, path))
    p_get_gps.start()

    p_get_img_data = Process(target=get_img_data, args=(path,))
    p_get_img_data.start()


if __name__ == "__main__":
    main()
    