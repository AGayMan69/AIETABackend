import cv2
import numpy as np
import time
import math
from math import atan2, degrees


class EscalatorDetector:
    def __init__(self):
        self.lk_params = dict(
            winSize=(10,10),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        self.startPointIsSet = False
        self.startAndEndPoint = {'Start':(0,0),'End':(0,0)}
        self.setTimeOut(1)

    #set start point for detection
    def setStartPoint(self,startX, startY):
        self.startAndEndPoint['Start'] = (startX,startY)
        self.startAndEndPoint['End'] = (startX,startY)
        self.oldPoints = np.array([[startX, startY]], dtype=np.float32)
        self.startPointIsSet = True

    def resizeFrame(self,img):
        resizedFrame = cv2.resize(img, (0, 0), fx=0.4, fy=0.4, interpolation=cv2.INTER_CUBIC)
        resizedFrame = cv2.cvtColor(resizedFrame, cv2.COLOR_BGR2GRAY)
        return resizedFrame;

    def calOpticalFlow(self,preFrame, curFrame):
        newPoints, status, error = cv2.calcOpticalFlowPyrLK(preFrame, curFrame, self.oldPoints, None, **self.lk_params)
        self.oldPoints = newPoints
        return newPoints.ravel()

    def getAngleBtw2Points(self,pointA, pointB):
        dx = pointB[0] - pointA[0]
        dy = pointB[1] - pointA[1]
        degree = (degrees(atan2(dy, dx)) + 360) % 360
        return degree

    # def getAngleBtw2Points(self,pointA,pointB):
    #         xDiff = pointB[0] - pointA[0]
    #         yDiff = pointB[1] - pointA[1]
    #         deg = degrees(atan2(yDiff, xDiff))
    #         return math.fmod((math.fmod(deg,360)+360), 360)

    def getDirection(self,angle):
        if 190 < angle < 350:
            return 'UP'
        elif 170 > angle > 10:
            return 'DOWN'
        else:
            return 'STOP'

    def setTimeOut(self,sec):
        self.duration = sec
        return self.duration

    def DisplayDetectPoint(self,cv,img,X,Y):
        cv.circle(img, (int(X), int(Y)), 5, (0, 0, 255), -1)
        cv.imshow('Frame', img)

    def startDetection(self,videoDir):
        self.startPointIsSet = False
        cap = cv2.VideoCapture(videoDir)

        curTime = time.time()
        timeOut = curTime+self.duration

        # get the first frame
        _,frame = cap.read()

        if not _ :
            print('Error')
            return

        prevGrayFrame = self.resizeFrame(frame)
        self.oldPoints = ([[]])

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = self.resizeFrame(frame)

            if not self.startPointIsSet:
                cX = int(frame.shape[1] / 2)
                cY = int(frame.shape[0] / 2)
                self.setStartPoint(cX,cY)
            # print(self.startAndEndPoint)
            print('detecting')

            # get flow from current frame and prev frame
            nX, nY = self.calOpticalFlow(prevGrayFrame,frame)
            self.startAndEndPoint['End'] = (int(nX),int(nY))
            prevGrayFrame = frame

            # self.DisplayDetectPoint(cv2,frame.copy(),nX,nY)
            key = cv2.waitKey(1)
            if key == 27 or curTime > timeOut:
                break
        cap.release()
        cv2.destroyAllWindows()
        # return self.startAndEndPoint
        angles = self.getAngleBtw2Points(self.startAndEndPoint['Start'], self.startAndEndPoint['End'])
        # print(angles)
        return self.getDirection(angles)



















