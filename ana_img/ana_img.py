import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
from sklearn.metrics import confusion_matrix
import time
import glob

frame_height = 9.5
frame_width = 15

def edge_sort(arr):
    tmp = []
    edge_array = []
    for i in range(len(arr)):
        tmp.append(np.sum(arr[i]))
        
    tmp_max = arr[(tmp.index(max(tmp)))]
    tmp_min = arr[(tmp.index(min(tmp)))]

    arr.pop(tmp.index(max(tmp)))
    tmp.pop(tmp.index(max(tmp)))
    arr.pop(tmp.index(min(tmp)))
    
    edge_array.append(tmp_min)
    
    if arr[0][0] > arr[1][0]:
        index_min = 0
        index_max = 1
    else:
        index_min = 1
        index_max = 0
    
    edge_array.append(arr[index_min])
    edge_array.append(arr[index_max])
    
    edge_array.append(tmp_max)
    
    return edge_array

def detect_edge(img):
    blur = cv2.GaussianBlur(img,(5,5),0)
    ret3,th3 = cv2.threshold(blur,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    contours, hierarchy = cv2.findContours(
        th3, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = list(filter(lambda x: cv2.contourArea(x) > 4000000, contours))
    approx_contours = []
    for i, cnt in enumerate(contours):
        arclen = cv2.arcLength(cnt, True)
        approx_cnt = cv2.approxPolyDP(cnt, epsilon=0.01 * arclen, closed=True)
        approx_contours.append(approx_cnt[0][0])
        approx_contours.append(approx_cnt[1][0])
        approx_contours.append(approx_cnt[2][0])
        approx_contours.append(approx_cnt[3][0])
        
        edge_array = edge_sort(approx_contours)
        
    return edge_array

def change_aspect(img, edge):
    p_original = np.float32(edge)
    p_trans = np.float32([[0, 0], [700, 0], [0, 450], [700, 450]])
    M = cv2.getPerspectiveTransform(p_original, p_trans)
    trans_color = cv2.warpPerspective(img, M, (700, 450))
    trans_color = delete_frame(trans_color)
    return trans_color

def delete_frame(img):
    p_original = np.float32([[50, 50], [650, 50], [50, 400], [650, 400]])
    p_trans = np.float32([[0, 0], [700, 0], [0, 450], [700, 450]])
    M = cv2.getPerspectiveTransform(p_original, p_trans)
    trans_color = cv2.warpPerspective(img, M, (700, 450))
    return trans_color

def background_subtraction(base_trans_color, matter_trans_color):
    def numpy_gray(src):
        b, g, r = src[:, :, 0], src[:, :, 1], src[:, :, 2]
        gray = 0.7 * b + 0.2 * g + 0 * r
        return gray
    gray_num = numpy_gray(base_trans_color)
    gray_num = gray_num.astype(np.uint8)
    ret4,th4 = cv2.threshold(gray_num,30,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    
    gray_num = numpy_gray(matter_trans_color)
    gray_num = gray_num.astype(np.uint8)
    ret3,th3 = cv2.threshold(gray_num,30,255,cv2.THRESH_BINARY)
    
    fgbg_1 = cv2.createBackgroundSubtractorMOG2(detectShadows = False )

    fgmask2 = fgbg_1.apply(th4)
    fgmask2 = fgbg_1.apply(th3)
    
    fgmask2 = cv2.medianBlur(fgmask2,5)
    ret, thresh2 = cv2.threshold(fgmask2, 120, 255, cv2.THRESH_BINARY)
    contours, hierarchy = cv2.findContours(
        thresh2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours = list(filter(lambda x: cv2.contourArea(x) > 0, contours))
    return contours

def predict_plastic(matter_trans_color, contours):
    
    def change_numpy(arr):
        base_dn = matter_trans_color[225][350]
        df = pd.DataFrame(data=[arr], columns=['b', 'g', 'r'])
        df['b'] = df['b']/base_dn[0]
        df['g'] = df['g']/base_dn[1]
        df['r'] = df['r']/base_dn[2]
        df["b/g"] = df["b"] / df["g"]
        df["b/r"] = df["b"] / df["r"]
        df["g/r"] = df["g"] / df["r"]
        return df
    
    model = pickle.load(open('./pth/new_gbdt_class_tree_9_3.pkl', 'rb'))
    
    for i in range(len(contours)):
        cimg = np.zeros_like(matter_trans_color)
        cv2.drawContours(cimg, contours, -1, color=(0, 0, 255), thickness=-1)
        
    for i in range(450):
        for j in range(700):
            if(cimg[i][j][2] == 255):
                y_pred = model.predict(change_numpy(matter_trans_color[i][j]))
                if(y_pred >= 0.5):
                    matter_trans_color[i][j] = (0, 255, 0)
                else:
                    matter_trans_color[i][j] = (0, 0, 255)
    
    new_img = np.zeros_like(matter_trans_color)
    
    for i in range(len(contours)):
        cimg = np.zeros_like(matter_trans_color)
        cv2.drawContours(cimg, [contours[i]], -1, color=(0, 0, 255), thickness=1)
    
    plastic_num = 0
    natural_num = 0
    for i in range(len(contours)):
        cimg = np.zeros_like(matter_trans_color)
        cv2.drawContours(cimg, [contours[i]], -1, color=(0, 0, 255), thickness=-1)
        cv2.drawContours(cimg, [contours[i]], -1, color=(0, 0, 0), thickness=1)
        g = 0
        r = 0
        for j in range(450):
            for k in range(700):
                if(cimg[j][k][2] == 255):
                    if matter_trans_color[j][k][1] == 255:
                        g += 1
                    if matter_trans_color[j][k][2] == 255:
                        r += 1
        
        if g >= r:
            cv2.drawContours(new_img, [contours[i]], -1, color=(0, 255, 0), thickness=-1)
        else:
            cv2.drawContours(new_img, [contours[i]], -1, color=(0, 0, 255), thickness=-1)

    for i in range(450):
        for j in range(700):
            if(new_img[i][j][2] == 255):
                plastic_num += 1
            if(new_img[i][j][1] == 255):
                natural_num += 1

    return plastic_num, natural_num

def main():
    img_path_list = sorted(glob.glob('img/*.JPG'))
    for i in range(len(img_path_list) - 1):
        t1 = time.time()
        base_1_color = cv2.imread(img_path_list[i])
        base_1 = cv2.imread(img_path_list[i], 0)
        matter_1_color = cv2.imread(img_path_list[i + 1])
        matter_1 = cv2.imread(img_path_list[i + 1], 0)

        frame_area = frame_height * frame_width
        pixel_unit = frame_area / (450 * 700)

        base_edge = detect_edge(base_1)
        base_trans_color = change_aspect(base_1_color, base_edge)
        matter_edge = detect_edge(matter_1)
        matter_trans_color = change_aspect(matter_1_color, matter_edge)

        contours = background_subtraction(base_trans_color, matter_trans_color)

        plastic_num, natural_num = predict_plastic(matter_trans_color, contours)

        plastic_area = plastic_num * pixel_unit
        natural_area = natural_num * pixel_unit

        print(plastic_area, natural_area)

        print(time.time() - t1)
    
if __name__ == '__main__':
    main()