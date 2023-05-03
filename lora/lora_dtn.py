import serial
import time
import random
import pandas as pd
import numpy as np
import glob

ser = serial.Serial("/dev/ttyUSB_01", 19200)

user_id = '03'

require_connection_command = "00"
send_ack_command = "01"
sent_all_data_command = "02"
send_request_command = "03"
ch_array = ["07", "08", "09", "0A", "0B", "0C", "0D", "0E", "0F", "10", "11", "12", "13", "14", "15", "16", "17", "18",
            "19", "1A", "1C", "1D", "1E", "1F", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "2A", "2B", "2C", "2D", "2E"]
T = 30
broad = "00"

node_connection_time_array = [0] * 10

connectable_node_list = [0] * 10
connectable_node_num = [0] * 10
node_ra_list = [''] * 10

time_out_send_ch = 35

# -*- 初期化 -*-
def init(id, ch):
    address = "@DI"+id+"/W\r\n"
    channel = "@CH"+ch+"/W\r\n"
    ser.write(b"@GI11/W\r\n")  # グループID設定コマンド
    ser.write(b"@EI03/W\r\n")  # 機器ID設定
    ser.write(bytes(address, 'utf-8'))  # 目的局設定　
    ser.write(b"@SF00/W\r\n")  # 拡散率設定
    ser.write(bytes(channel, 'utf-8'))  # 周波数チャンネル設定


# -*- 受信する際のデータ読み取り -*-
def showreceived():
    data = ser.readline()
    str = data.decode('utf-8')
    return (str)


# -*- 送信する際のデータ書き出し -*-
def write_data(txt):
    length = len(txt)
    #print("ユーザデータ文字数(10進数) > ", length)
    hex_len = hex(length)[2:]
    # ユーザデータが15文字以下の場合、16進数表記の先頭に０をつけて２桁にする
    if len(hex_len) < 2:
        tmp_num = hex_len
        hex_len = '0' + tmp_num
    #print("ユーザデータ文字数(16進数) > ", hex_len)
    tmp = "@DT" + str(hex_len) + txt + "\r\n"
    ser.write(tmp.encode())
    return False


def require_connection(random_sec, ch_dbm_str):
    print('-----require-----')
    t_end = time.time() + random_sec
    while time.time() < t_end:
        txt = "_" + require_connection_command + "_" + user_id + "_" + ch_dbm_str + "_" + str(connectable_node_list[int(user_id)])
        write_data(txt)
        while True:
            if ser.in_waiting:
                message = showreceived()
                if message.find("*IR=01") >= 0:
                    write_data(txt)
                elif message.find("*IR=02") >= 0:
                    write_data(txt)
                elif message.find("*IR=03") >= 0:
                    print('---success---')
                    break


def response_connection(random_sec):
    print('-----response-----')
    t_end = time.time() + random_sec
    while time.time() < t_end:
        if ser.in_waiting:
            message = showreceived()
            if message.find("*DR") >= 0:  # 送信機からデータを受信した時
                print(message)
                message = message.split("\r\n")
                data = message[0].split("_")
                if (data[1] == require_connection_command):
                    connectable_node_num[int(data[2])] = 1
                    connect_num = 0
                    for i in range(len(connectable_node_num)):
                        if(connectable_node_num[i] != 0):
                            connect_num += 1
                    connectable_node_list[int(user_id)] = connect_num
                    connectable_node_list[int(data[2])] = int(data[4])
                    print(connectable_node_list)
                    node_ra_list[int(data[2])] = data[3]
                if (data[1] == send_ack_command):
                    node_array = data[4].split(',')
                    if str(int(user_id)) in node_array:
                        send_data_to_parent(data[2], data[3], node_array)
                            


def send_ack(sec, ch):
    print('-----send_ack-----')
    t_end = time.time() + sec
    while time.time() < t_end:
        txt = "_" + send_ack_command + "_" + user_id + "_" + ch
        write_data(txt)
        while True:
            if ser.in_waiting:
                message = showreceived()
                if message.find("*IR=01") >= 0:
                    write_data(txt)
                elif message.find("*IR=02") >= 0:
                    write_data(txt)
                elif message.find("*IR=03") >= 0:
                    print('---success---')
                    break


def send_data(txt):
    print('-----send_data-----')
    write_data(txt)
    t1 = time.time()
    while 1:
        if ser.in_waiting:
            message = showreceived()
            if message.find("*IR=01") >= 0:
                write_data(txt)
            elif message.find("*IR=02") >= 0:
                write_data(txt)
            elif message.find("*IR=03") >= 0:
                t2 = time.time()  # 処理終了時刻
                elapsed_time = t2-t1
                print(f"経過時間：{elapsed_time}")
                print('---success---')
                break



def send_sensor_data(destination_node):
    time.sleep(5)
    print('-----send_sensor_data-----')
    file = glob.glob("node_1/data/*")
    destination_data_path = "node_1/data/node_" + destination_node + ".csv"
    try:
        file.remove(destination_data_path)
    except:
        pass
    for l in file:
        with open(l) as f:
            print(f)
            for line in f:
                send_data(line)
    send_data("_" + sent_all_data_command)
    return 0


def search_ch():
    print('-----search_channel-----')
    dbm_array = []
    for i in range(len(ch_array)):
        init("00",ch_array[i])
        for j in range(10):
            ser.write(b"@RA\r\n")
        count = 0
        while 1:
            if ser.in_waiting:

                message = showreceived()
                if (message[4] == "-"):
                    count += 1
                    if (count == 10):
                        data = message.split("=")
                        data = data[1].split("d")
                        data = int(data[0]) + 100
                        dbm_array.append(str(data))
                        break
    ch_dbm_str = ",".join(dbm_array)
    return ch_dbm_str


def find_ch(ch_dbm_str):
    print('-----find_channel-----')
    dbm_array = []
    for i in range(len(ch_array)):
        init("00",ch_array[i])
        for j in range(10):
            ser.write(b"@RA\r\n")
        count = 0
        while 1:
            if ser.in_waiting:

                message = showreceived()
                if (message[4] == "-"):
                    count += 1
                    if (count == 10):
                        data = message.split("=")
                        data = data[1].split("d")
                        dbm_array.append(int(data[0]) + ch_dbm_str[i])
                        break
    ch_index = np.argmin(dbm_array)
    init(broad, "1B")
    return ch_array[ch_index]

def sum_ra():
    tmp_array = [0] * 39
    for i in range(len(node_ra_list)):
        try:
            t = node_ra_list[i].split(',')
            for j in range(len(t)):
                tmp_array[j] += int(t[j])
        except:
            continue
    return tmp_array

def send_ch(ch):
    node_list = []
    for i in range(len(connectable_node_num)):
        if i == int(user_id):
            continue
        if(connectable_node_num[i] != 0):
            node_list.append(str(i))
    node_list_str = ",".join(node_list)


    print('-----send ch-----')
    t_end = time.time() + time_out_send_ch
    while time.time() < t_end:
        txt = "_" + send_ack_command + "_" + user_id + "_" + str(ch) +  "_" + node_list_str
        write_data(txt)
        while True:
            if ser.in_waiting:
                message = showreceived()
                if message.find("*IR=01") >= 0:
                    write_data(txt)
                elif message.find("*IR=02") >= 0:
                    write_data(txt)
                elif message.find("*IR=03") >= 0:
                    print('---success---')
                    break
    init(broad, str(ch))
    count = 0
    while 1:
            if receive_data() == 0:
                count += 1
                if (count < len(node_list)):
                    send_request_data(node_list[count])
                else:
                    break
    send_sensor_data('none')
    init(broad, "1B")
    print('終了時間', time.time())

            

def send_data_to_parent(p_id, ch, node_array):
    init(p_id, ch)
    time.sleep(time_out_send_ch)
    line_num = node_array.index(str(int(user_id)))
    if line_num == 0:
        send_sensor_data(p_id)
    else:
        after_send_data(p_id)
    receive_data()
    init(broad, "1B")
    print('終了時間', time.time())


def after_send_data(p_id):
    print('----wait_send_data----')
    while 1:

        if ser.in_waiting:
            message = showreceived()
            if message.find("*DR") >= 0:  # 送信機からデータを受信した時
                print(message)
                message = message.split("\r\n")
                data = message[0].split("_")
                if(data[1] == send_request_command and data[3] == str(int(user_id))):
                    time.sleep(10)
                    send_sensor_data(p_id)
                    break

def send_request_data(node):
    print('-----send_request_data-----')
    t_end = time.time() + time_out_send_ch
    for i in range(3):
        txt = "_" + send_request_command + "_" + user_id + "_" + node
        write_data(txt)
        while True:
            if ser.in_waiting:
                message = showreceived()
                if message.find("*IR=01") >= 0:
                    write_data(txt)
                elif message.find("*IR=02") >= 0:
                    write_data(txt)
                elif message.find("*IR=03") >= 0:
                    print('---success---')
                    break

def receive_data():
    print('----receiving_data----')
    t1 = time.time()
    while 1:
        if(time.time() > t1 + 180):
            print("---can't receive data---")
            return 1
        if ser.in_waiting:
            message = showreceived()
            if message.find("*DR") >= 0:  # 送信機からデータを受信した時
                t1 = time.time()
                print(message)
                data = message.split("_")
                try:
                    if(data[1] == send_request_command):
                        continue
                except:
                    pass
                if len(data) > 1:
                    data = data[1].split("\r\n")
                    if (data[0] == sent_all_data_command):
                        return 0
                node_id = message[6:8]
                data_path = "node_3/data/node_" + node_id + ".csv"
                base_data = message[6:]
                data = message[6:].strip()
                try:
                    df = pd.read_csv(data_path, header=None, dtype=object)
                    data_sp =data.split(",")
                    data_df = pd.DataFrame(data_sp)
                    x = pd.concat([df, data_df.T], axis=0)
                    if (x.duplicated().sum()):
                        continue
                except:
                    pass
                with open(data_path, mode='a') as f:
                        f.write(base_data)


def establish_connection():
    count = 0
    ch_dbm_str = ""
    while 1:
        random_sec_req = random.randint(10, 20)
        random_sec_res = T - random_sec_req
        if count % 30 == 0:
            ch_dbm_str = search_ch()
            init(broad, "1B")
        
        require_connection(random_sec_req, ch_dbm_str)
        response_connection(random_sec_res)
        count += 1
        if(count == 5):
            print(connectable_node_list)
            print(node_ra_list)
            try:
                if(int(user_id) < connectable_node_list.index(1)):
                    ra_list = sum_ra()
                    print(ra_list)
                    ch = find_ch(ra_list)
                    print(ch)
                    send_ch(ch)
            except:
                continue

def main():
    print('開始時間', time.time())
    establish_connection()


if __name__ == '__main__':
    main()