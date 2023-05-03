import cv2
import numpy as np
import pandas as pd
import mysql.connector
import csv
from numpy import linalg as LA


def pull_database_data(table_name):
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        passwd='',
        db='research_sensor_data')
    cursor = connection.cursor()
    cursor.execute(
        "SELECT locate_date, lat, lon, new_x, new_y, depth FROM " + table_name)
    rows = cursor.fetchall()
    return rows


def calcurate_data(data):
    count = 0
    for i in range(len(data)):
        if (data[i][1] != 0):
            break
        count += 1
    data = data[count:]

    predict_lat_array = []
    predict_lon_array = []

    while 1:
        start_lat = data[0][1]
        start_lon = data[0][2]
        start_x = data[0][3]
        start_y = data[0][4]

        count = 0
        for i in range(len(data)):

            if (data[i][1] == 0):
                last_lat = data[i - 1][1]
                last_lon = data[i - 1][2]
                last_x = data[i - 1][3]
                last_y = data[i - 1][4]
                break
            predict_lat_array.append(data[i][1])
            predict_lon_array.append(data[i][2])
            count += 1

        if (count == len(data)):
            break

        print(start_lat, start_lon, start_x, start_y)
        print(last_lat, last_lon, last_x, last_y)

        diff_lat = last_lat - start_lat
        diff_lon = last_lon - start_lon
        diff_x = last_x - start_x
        diff_y = last_y - start_y

        lon_lat_array = np.array([diff_lon, diff_lat])
        x_y_array = np.array([diff_x, diff_y])
        i = np.inner(lon_lat_array, x_y_array)
        n = LA.norm(lon_lat_array) * LA.norm(x_y_array)
        c = i / n
        radian = np.arccos(np.clip(c, -1.0, 1.0))
        if np.cross(x_y_array, lon_lat_array) < 0:
            radian = -radian
        R = np.array([[np.cos(radian), -np.sin(radian)],
                      [np.sin(radian),  np.cos(radian)]])

        coefficient_x_to_lon = lon_lat_array[0] / np.dot(R, x_y_array)[0]
        coefficient_y_to_lat = lon_lat_array[1] / np.dot(R, x_y_array)[1]

        data = data[count:]

        count = 0

        for i in range(len(data)):
            if (data[i][1] != 0):
                break
            new_x_y_array = np.array([data[i][3], data[i][4]])
            predict_lon = start_lon + \
                np.dot(R, new_x_y_array)[0] * coefficient_x_to_lon
            predict_lat = start_lat + \
                np.dot(R, new_x_y_array)[1] * coefficient_y_to_lat

            predict_lon_array.append(round(predict_lon, 9))
            predict_lat_array.append(round(predict_lat, 9))

            count += 1

        data = data[count + 1:]
        break
    return predict_lat_array, predict_lon_array


def array_to_csv(lat_data, lon_data):
    data = np.array([lat_data, lon_data])
    data = data.T
    with open('text.csv', 'w') as f:
        np.savetxt(f, data, delimiter=',', fmt='%s')


def main():
    table_name = "sensor_data_fountain_2"
    data = pull_database_data(table_name)
    predict_lat_array, predict_lon_array = calcurate_data(data)
    array_to_csv(predict_lat_array, predict_lon_array)


if __name__ == '__main__':
    main()
