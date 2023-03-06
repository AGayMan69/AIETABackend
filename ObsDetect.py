import numpy as np
import cv2 as cv2
import depthai as dai
from collections import Counter
import time

x_loc = 100
y_loc = 60
thickness = 1


class ObsDetect:
    def __init__(self, device: dai.Device):
        self.device = device
        self.queue = self.device.getOutputQueue(name="disparity", maxSize=4, blocking=False)

    def reverse_number(self, num):
        max_num = 190
        min_num = 0
        return (max_num + min_num) - num

    def region_check(self, foo, list_path):  # foo defines x-coordinate of point
        if foo <= 100:
            list_path[0] += 1
        if (foo > 100) and (foo <= 200):
            list_path[1] += 1
        if (foo > 200) and (foo <= 300):
            list_path[2] += 1
        if foo > 300:
            list_path[3] += 1
        return list_path

    def cal_direct(self, list_path: list, list_dir: list, threshold_val: int, display: bool):

        # insert a ListPath, t, input img to read
        # Forward
        if max(list_path[1:3]) <= threshold_val:
            list_dir.append(3)
        # Right
        elif max(list_path[3:4]) <= threshold_val:
            list_dir.append(4)
        # Left
        elif max(list_path[0:1]) <= threshold_val:
            list_dir.append(5)
        # Back
        else:
            list_dir.append(6)

        # if display:
        # cv2.putText(img, str(list_path), (x_loc, y_loc + 80), cv2.FONT_HERSHEY_TRIPLEX, 1, 2, 1)
        # print(str(list_path))

    def get_direct_msg(self, index: int) -> str:
        direct_msg = ""
        if index == 1:
            direct_msg = "前方不便前行"
        elif index == 2:
            direct_msg = "前方不便前行"
        elif index == 3:
            direct_msg = "向前走"
        elif index == 4:
            direct_msg = "向右走"
        elif index == 5:
            direct_msg = "向左走"
        else:
            direct_msg = "向後走"

        return direct_msg

    def get_guide(self, list_dir: list, display: bool):

        threshold_val = 9
        inDisparity = self.queue.get()
        frame = inDisparity.getFrame()
        frame = frame[::, 0:400]
        frame = self.reverse_number(frame)
        if display:
            edges = cv2.Canny(frame, 37, 43)
            contours, hierarchy = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            cv2.drawContours(frame, contours, -1, (0, 0, 255), -1)
        # counter += 1
        spac = 20
        collision_val = 12
        (rows, cols) = frame.shape  # 480 rows and 640 cols
        # print cols
        flag120 = [0, 0, 0, 0]
        flag140 = [0, 0, 0, 0]
        f14 = 0
        f12 = 0
        f10 = 0
        f8 = 0
        for i in range(int(rows / spac)):  # note the presence of colon
            for j in range(int(cols / spac)):
                if frame[spac * i, spac * j] <= 50:
                    continue
                # if display:
                #     cv2.circle(frame, (spac * j, spac * i), 1, (0, 255, 0), 1)

                if frame[spac * i, spac * j] <= 80:
                    f8 += 1
                    if display:
                        cv2.putText(frame, "0", (spac * j, spac * i), cv2.FONT_HERSHEY_PLAIN, 1, (0, 200, 20), thickness)
                elif frame[spac * i, spac * j] <= 100:
                    f10 += 1
                    if display:
                        cv2.putText(frame, "1", (spac * j, spac * i), cv2.FONT_HERSHEY_PLAIN, 1, (0, 200, 20), thickness)
                elif frame[spac * i, spac * j] <= 130:
                    f12 = 1
                    if display:
                        cv2.putText(frame, "2", (spac * j, spac * i), cv2.FONT_HERSHEY_PLAIN, 1, (0, 200, 20), thickness)
                        flag120 = self.region_check(spac * j, flag120)
                # if f8 == 0 and f10 == 0:
                # showDirect(flag120)
                elif frame[spac * i, spac * j] <= 170:
                    f14 = 1
                    if display:
                        cv2.putText(frame, "3", (spac * j, spac * i), cv2.FONT_HERSHEY_PLAIN, 1, (0, 200, 20), thickness)
                    flag140 = self.region_check(spac * j, flag140)
                # if f8 == 0 and f10 == 0 and f12 == 0:
                # showDirect(flag140)
                elif frame[spac * i, spac * j] <= 180:
                    if display:
                        cv2.putText(frame, "4", (spac * j, spac * i), cv2.FONT_HERSHEY_PLAIN, 1, (0, 200, 20), thickness)

        if f8 >= collision_val:
            list_dir.append(1)
        elif f10 >= collision_val:
            list_dir.append(2)
        elif f12 == 1:
            self.cal_direct(flag120, list_dir, threshold_val, display=display)
        else:
            self.cal_direct(flag140, list_dir, threshold_val, display=display)

        if display:
            cv2.imshow("disparity", frame)

    def retrieve_message(self):
        WAIT_TIME = 1
        cur_time = time.time()
        timeout = cur_time + WAIT_TIME
        direction = []
        while True:
            cur_time = time.time()
            self.get_guide(list_dir=direction, display=True)
            if cur_time >= timeout:
                timeout = cur_time + WAIT_TIME
                count = Counter(direction)
                msg = self.get_direct_msg(count.most_common(1)[0][0])
                return msg
