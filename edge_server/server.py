from hashlib import new
from npsocket import SocketNumpyArray
from this import d
from webbrowser import get
import json
import pcapy
from impacket.ImpactDecoder import *
import re
import pandas as pd
from pandas import json_normalize
import mysql.connector
from multiprocessing import Value, Array, Process
import copy
import struct
import pickle
import threading
from multiprocessing import set_start_method


def recv_data(sock, addr, depth):
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        passwd='',
        db='research_sensor_data')

    while True:
        cursor = connection.cursor()

        while len(sock.data) < sock.payload_size:
            sock.data += sock.conn.recv(4096)

        packed_msg_size = sock.data[:sock.payload_size]
        sock.data = sock.data[sock.payload_size:]
        msg_size = struct.unpack("I", packed_msg_size)[0]

        # Retrieve all data based on message size
        while len(sock.data) < msg_size:
            sock.data += sock.conn.recv(4096)

        frame_data = sock.data[:msg_size]
        sock.data = sock.data[msg_size:]

        # Extract frame
        sensor_data = pickle.loads(frame_data)

        if sensor_data[-1] == 'g':
            path = sensor_data
            while len(sock.data) < sock.payload_size:

                sock.data += sock.conn.recv(4096)

            packed_msg_size = sock.data[:sock.payload_size]
            sock.data = sock.data[sock.payload_size:]
            msg_size = struct.unpack("I", packed_msg_size)[0]

            # Retrieve all data based on message size
            while len(sock.data) < msg_size:
                sock.data += sock.conn.recv(4096)

            frame_data = sock.data[:msg_size]
            sock.data = sock.data[msg_size:]

            # Extract frame
            img_data = pickle.loads(frame_data)

            with open('img/' + path, "wb") as f:
                f.write(img_data)
        else:
            sensor_data = sensor_data + "," + str(depth.value)
            print(sensor_data)
            seosor_data = sensor_data.split(",")
            cursor.execute(
                "INSERT INTO sensor_data_sc_2 (node, locate_date, lat, lon, new_x, new_y, img_path, depth) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", seosor_data)
            connection.commit()
            cursor.close()


def create_socket(depth):
    sock_receiver = SocketNumpyArray()
    sock_receiver.address = '169.254.6.97'
    sock_receiver.port = 8800
    sock_receiver.socket.bind((sock_receiver.address, sock_receiver.port))
    print('Socket bind complete')
    sock_receiver.socket.listen(10)
    while True:
        sock_cl = copy.copy(sock_receiver)
        sock_cl.conn, addr = sock_receiver.socket.accept()

        print('Socket now listening')
        sock_cl.payload_size = struct.calcsize("I")  # CHANGED
        sock_cl.data = b''

        recv_data_thread = threading.Thread(
            target=recv_data, args=(sock_cl, addr, depth), daemon=True)
        recv_data_thread.start()


def loop_get_packet(depth):

    def recv_pkts(hdr, data):
        nonlocal depth
        packet = EthDecoder().decode(data)
        ip = packet.child()
        udp = ip.child()
        data = udp.child()
        data = str(data)
        data = re.split('\n', data)
        tmp_data = []
        for i in range(len(data)):
            tmp_data.append(re.split(' ', data[i])[-1])
        data = "".join(tmp_data)
        data = re.split('"depth":', data)
        depth.value = float(re.split(',', data[1])[0])

    pcapy.findalldevs()
    max_bytes = 1024
    promiscuous = False
    read_timeout = 100  # in milliseconds
    pc = pcapy.open_live("en0", max_bytes, promiscuous, read_timeout)
    pc.setfilter('udp')
    pc.setfilter('dst port 8500')
    pc.loop(0, recv_pkts)


def main():
    set_start_method('fork')
    depth = Value('d', 0)

    p_create_socket = Process(target=create_socket, args=(depth,))
    p_create_socket.start()

    p_loop_get_packet = Process(target=loop_get_packet, args=(depth,))
    p_loop_get_packet.start()


if __name__ == '__main__':
    main()
