import cv2
import numpy as np
import time
# import math
from math import atan2, degrees

# update
import depthai as dai


class EscalatorDetector:
    def __init__(self):
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        # self.lk_params = dict(
        #     winSize=(10,10),
        #     maxLevel=3,
        #     criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        self.errorOccurs = False
        self.startPointIsSet = False
        self.startAndEndPoint = {'Start': (0, 0), 'End': (0, 0)}
        self.prevPt_arrow = (0, 0)
        self.setTimeOut(3)
        self.isOAKD = self.checkDevices()

        if self.isOAKD:
            self.setDepthaiSetting()

    # If mxid exist then return true
    def checkDevices(self, mxid='19443010C15BDC1200'):
        return dai.Device.getDeviceByMxId(mxid)[0]

    def setDepthaiSetting(self):
        self.pipeline = dai.Pipeline()
        self.camRgb = self.pipeline.create(dai.node.ColorCamera)
        self.xoutVideo = self.pipeline.create(dai.node.XLinkOut)
        self.xoutVideo.setStreamName("video")
        # Properties
        self.camRgb.setBoardSocket(dai.CameraBoardSocket.RGB)
        self.camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
        # Window size
        self.camRgb.setVideoSize(480, 640)
        self.xoutVideo.input.setBlocking(False)
        self.xoutVideo.input.setQueueSize(1)
        # Linking
        self.camRgb.video.link(self.xoutVideo.input)

    # set start point for detection
    def setStartPoint(self, startX, startY):
        self.startAndEndPoint['Start'] = (startX, startY)
        self.startAndEndPoint['End'] = (startX, startY)
        self.oldPoints = np.array([[startX, startY]], dtype=np.float32)
        self.startPointIsSet = True

    def rgbToBgr(self, img):
        # resizedFrame = cv2.resize(img, (0, 0), fx=0.4, fy=0.4, interpolation=cv2.INTER_CUBIC)
        # resizedFrame = cv2.cvtColor(resizedFrame, cv2.COLOR_BGR2GRAY)
        resizedFrame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return resizedFrame;

    def resizeFrame(self, img):
        resizedFrame = cv2.resize(img, (640, 480))
        resizedFrame = cv2.cvtColor(resizedFrame, cv2.COLOR_BGR2GRAY)
        return resizedFrame;

    def calOpticalFlow(self, preFrame, curFrame):
        newPoints, status, error = cv2.calcOpticalFlowPyrLK(preFrame, curFrame, self.oldPoints, None, **self.lk_params)
        self.oldPoints = newPoints
        return newPoints.ravel()

    def getAngleBtw2Points(self, pointA, pointB):
        dx = pointB[0] - pointA[0]
        dy = pointB[1] - pointA[1]
        # if y does not move by more than 5% of frame height
        # print(dy)
        if -32 < dy < 32:
            return 0
        degree = (degrees(atan2(dy, dx)) + 360) % 360
        return degree

    # def getAngleBtw2Points(self,pointA,pointB):
    #         xDiff = pointB[0] - pointA[0]
    #         yDiff = pointB[1] - pointA[1]
    #         deg = degrees(atan2(yDiff, xDiff))
    #         return math.fmod((math.fmod(deg,360)+360), 360)

    def identifyDirection(self, angle):
        if 190 < angle < 350:
            return 'UP'
        elif 170 > angle > 10:
            return 'DOWN'
        else:
            # Include stopped
            return 'Unknown'

    def setTimeOut(self, sec):
        self.duration = sec
        return self.duration

    def display(self, img, X, Y):
        cv2.arrowedLine(img, self.prevPt_arrow, (int(X), int(Y)), (0, 0, 255), 5, 8, 0, 5)
        cv2.circle(img, (int(X), int(Y)), 5, (0, 0, 255), -1)
        cv2.imshow('Frame', img)

    def run(self):
        if self.isOAKD:
            self.detectWithOAKD()
        else:
            self.detect()
        cv2.destroyAllWindows()

        if not self.errorOccurs:
            # # return self.startAndEndPoint
            angles = self.getAngleBtw2Points(self.startAndEndPoint['Start'], self.startAndEndPoint['End'])
            # # print(angles)
            return self.identifyDirection(angles)
        return 'Error'

    # RGB camera
    def detect(self, videoDir=0):
        self.startPointIsSet = False
        cap = cv2.VideoCapture(videoDir)

        curTime = time.time()
        timeOut = curTime + self.duration

        # get the first frame
        _, frame = cap.read()

        if not _:
            self.errorOccurs = True
            return

        prevGrayFrame = self.resizeFrame(frame)
        self.oldPoints = ([[]])

        while True:
            ret, frame = cap.read()

            # update duration
            curTime = time.time()

            if not ret:
                break
            frame = self.resizeFrame(frame)
            # print(frame.shape)

            if not self.startPointIsSet:
                cX = int(frame.shape[1] / 2)
                cY = int(frame.shape[0] / 2)
                self.setStartPoint(cX, cY)
                # for arrow line
                self.prevPt_arrow = (cX, cY)
            # print(self.startAndEndPoint)

            # get flow from current frame and prev frame
            nX, nY = self.calOpticalFlow(prevGrayFrame, frame)
            self.startAndEndPoint['End'] = (int(nX), int(nY))
            prevGrayFrame = frame

            self.display(frame.copy(), nX, nY)
            self.prevPt_arrow = self.startAndEndPoint['End']

            key = cv2.waitKey(1)
            if key == 27 or curTime > timeOut:
                break
        cap.release()
        # cv2.destroyAllWindows()
        # # return self.startAndEndPoint
        # angles = self.getAngleBtw2Points(self.startAndEndPoint['Start'], self.startAndEndPoint['End'])
        # # print(angles)
        # return self.getDirection(angles)

    # OAKD RGB Camera
    def detectWithOAKD(self):
        self.startPointIsSet = False

        # Connect to device and start pipeline
        with dai.Device(self.pipeline, dai.UsbSpeed.HIGH) as device:
            video = device.getOutputQueue(name="video", maxSize=1, blocking=False)

            videoIn = video.get()
            if videoIn is None:
                # Failed to read the first frame
                self.errorOccurs = True
                return

            # Skip the first few second of blurry frame
            cur = time.time()
            timeOut = cur + 2
            while cur < timeOut:
                videoIn = video.get()
                # cv2.imshow('Frame', videoIn.getCvFrame())
                cur = time.time()

            # prevGrayFrame = self.resizeFrame(videoIn.getCvFrame())
            prevGrayFrame = videoIn.getCvFrame()
            self.oldPoints = ([[]])
            curTime = time.time()
            timeOut = curTime + self.duration

            while True:
                # ret, frame = cap.read()
                videoIn = video.get()

                if videoIn is None:
                    break
                # update duration
                curTime = time.time()
                # frame = self.resizeFrame(videoIn.getCvFrame())
                frame = videoIn.getCvFrame()

                if not self.startPointIsSet:
                    cX = int(frame.shape[1] / 2)
                    cY = int(frame.shape[0] / 2)
                    self.setStartPoint(cX, cY)
                    # for arrow line
                    self.prevPt_arrow = (cX, cY)

                # get flow from current frame and prev frame
                nX, nY = self.calOpticalFlow(prevGrayFrame, frame)
                self.startAndEndPoint['End'] = (int(nX), int(nY))
                prevGrayFrame = frame

                # print('nx = ',nX,' ny = ',nY)
                self.display(frame.copy(), nX, nY)
                self.prevPt_arrow = self.startAndEndPoint['End']

                key = cv2.waitKey(1)
                if key == 27 or curTime > timeOut:
                    break

            # cv2.destroyAllWindows()
            # # return self.startAndEndPoint
            # angles = self.getAngleBtw2Points(self.startAndEndPoint['Start'], self.startAndEndPoint['End'])
            # # print(angles)
            # return self.getDirection(angles)


esc = EscalatorDetector()
result = esc.run()
print(result)
