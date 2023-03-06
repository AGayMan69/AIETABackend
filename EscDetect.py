import cv2
import numpy as np
import time
from math import atan2, degrees
import math
# update
import depthai as dai
import uuid


def resize_frame(frame):
    return cv2.resize(frame, (640, 640))


def gray_scale_frame(frame):
    return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


def is_boxes_overlap(R1, R2):
    r1_x1, r1_y1, r1_x2, r1_y2 = R1
    r2_x1, r2_y1, r2_x2, r2_y2 = R2
    # Return False if no overlap possible on X-Axis
    if r1_x2 <= r2_x1 or r2_x2 <= r1_x1:
        return False
    # Return False if no overlap possible on Y-Axis
    if r1_y2 <= r2_y1 or r2_y2 <= r1_y1:
        return False
    return True


# nn data, being the bounding box locations, are in <0..1> range - they need to be normalized with frame width/height
def frame_norm(frame, bbox):
    normVals = np.full(len(bbox), frame.shape[0])
    normVals[::2] = frame.shape[1]
    return (np.clip(np.array(bbox), 0, 1) * normVals).astype(int)


labelMap = [
    "down",
    "front",
    "step"
]


def get_bbox(results, frame):
    # Lists to store bounding boxes for escalators and steps
    esc_bboxes = []
    step_bboxes = []

    for result in results:
        bbox = frame_norm(frame, (result.xmin, result.ymin, result.xmax, result.ymax))
        bbox = np.insert(bbox, 0, result.label).tolist()
        if labelMap[result.label] == 'step':
            # print('Step size: ',str(bbox[4]-bbox[2]),'px')
            step_bboxes.append(bbox)
        else:
            esc_bboxes.append(bbox)

    return esc_bboxes, step_bboxes


def save_frame(frame):
    cv2.imwrite('SavedFrame/' + str(uuid.uuid4()) + '.jpg', frame)


class EscalatorDetector:

    def __init__(self, device: dai.Device):
        # Lucas-Kanade for front view
        self.lk_params = dict(
            winSize=(25, 25),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        # Lucas-Kanade for down view
        self.lk_params2 = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))

        self.minStepMovement = 0
        self.isFrontView = False

        # boolean for return an error
        self.errorOccurs = False
        self.escExist = True
        self.oakdConnectionError = False

        self.startEndCoords = {'start': [], 'end': []}
        self.missingPt = []
        self.lastFrame = None

        self.oldPoints = None
        self.prevPt = None

        self.pipelineError = False
        self.device = device
        # self.pipeline = pipeline
        # try:
        #     self.device = dai.Device(self.pipeline)
        # except Exception as e:
        #     print('No available Device')
        #     self.pipelineError = True

    def display(self, frame):
        frameBgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        for idx, p1 in enumerate(self.startEndCoords['end']):
            x1, y1 = self.prevPt[idx]
            x2, y2 = p1
            cv2.arrowedLine(frameBgr, (x1, y1), (x2, y2), (0, 0, 255), 2, 4, 0, 5)
        frameDisplay = cv2.resize(frameBgr, (320, 320))
        cv2.imshow('result', frameDisplay)
        cv2.waitKey(1)

    def display_2(self, frame):
        cv2.imshow('result', frame)
        cv2.waitKey(1)

    def getAngleBtw2Points(self, pointA, pointB):
        dx = pointB[0] - pointA[0]
        dy = pointB[1] - pointA[1]
        if -self.minStepMovement < dy < self.minStepMovement and self.isFrontView:
            return 0
        degree = (degrees(atan2(dy, dx)) + 360) % 360
        return degree

    def identifyDirection(self):
        totalDeg = 0
        for idx, p0 in enumerate(self.startEndCoords['start']):
            p1 = self.startEndCoords['end'][idx]
            totalDeg += self.getAngleBtw2Points(p0, p1)
        length = len(self.startEndCoords['start'])
        if length == 0:
            return 0
        avgDeg = totalDeg / length
        # print('avgAngle: ', int(avgDeg))
        return self.ang2EscDirection(avgDeg)

    def ang2EscDirection(self, angle):
        if 190 < angle < 350:
            if self.isFrontView:
                return '電梯向上'
            return '電梯向下'
        elif 170 > angle > 10:
            if self.isFrontView:
                return '電梯向下'
            return '電梯向上'
        else:
            return '電梯靜止'

    def initialSetting(self):
        self.errorOccurs = False
        self.escExist = True
        self.isFrontView = True
        self.oakdConnectionError = False

        self.startEndCoords = {'start': [], 'end': []}
        self.missingPt = []
        self.minStepMovement = 0

    def setStartPoints(self, objArea):

        self.prevPt = []
        y = int(objArea[1] + (objArea[3] - objArea[1]) / 2)
        x1 = int(objArea[0] + (objArea[2] - objArea[0]) * 0.25)
        x2 = int(objArea[0] + (objArea[2] - objArea[0]) * 0.50)
        x3 = int(objArea[0] + (objArea[2] - objArea[0]) * 0.75)
        self.prevPt = [(x1, y), (x2, y), (x3, y)]

        for pt in self.prevPt:
            self.startEndCoords['start'].append(pt)
            p = np.array([pt[0], pt[1]], dtype=np.float32).reshape(1, 2)
            self.oldPoints = np.vstack([self.oldPoints, p])

    def calOpticalFlow(self, preFrame, curFrame):
        for idx, pt in enumerate(self.oldPoints):
            if idx not in self.missingPt:
                # store old points for arrow line
                self.prevPt[idx] = (int(pt[0]), int(pt[1]))
                pt = np.array([[pt[0], pt[1]]], dtype=np.float32)

                # Calculate optical flow using appropriate parameters
                lk_params = self.lk_params if self.isFrontView else self.lk_params2
                newPoints, status, error = cv2.calcOpticalFlowPyrLK(preFrame, curFrame, pt, None, **lk_params)

                # Update point location if optical flow succeeded
                if status[0] == 1:
                    self.oldPoints[idx] = newPoints
                    nX, nY = newPoints.ravel()
                    if len(self.startEndCoords['end']) < idx + 1 or len(self.startEndCoords['end']) == 0:
                        self.startEndCoords['end'].append((int(nX), int(nY)))
                    else:
                        self.startEndCoords['end'][idx] = (int(nX), int(nY))
                else:
                    self.missingPt.append(idx)

    def getNewCoords(self, x, y):
        rx = 640 / 320
        ry = rx
        return int(rx * x), int(ry * y)

    def displayLastFrame(self):
        cv2.imshow('Last Frame', self.lastFrame)
        cv2.waitKey(0)

    def detectOAKD(self):
        try:
            # Output queues will be used to get the rgb frames and nn data from the outputs defined above
            qRgb = self.device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
            qDet = self.device.getOutputQueue(name="nn", maxSize=4, blocking=False)

            # Get the start time of the execution time
            self.st = time.time()

            # Skip the blur frame
            cur_time = time.time()
            time_out = cur_time + 2
            while time_out > cur_time:
                cur_time = time.time()
                qRgb.get()
                qDet.get()

            # 3 second for finding the escalator
            cur_time = time.time()
            time_out = cur_time + 3

            esc_found = False
            nearest_esc = None
            frame = None

            while cur_time < time_out and esc_found is False:

                cur_time = time.time()

                inRgb = qRgb.get()
                inDet = qDet.get()

                # Lists to store bounding boxes for escalators and steps
                esc_bboxes = []
                step_bboxes = []

                if inRgb is not None:
                    frame = inRgb.getCvFrame()
                    # self.display_2(frame)
                else:
                    self.errorOccurs = True
                    return

                if inDet is not None:
                    esc_bboxes, step_bboxes = get_bbox(inDet.detections, frame)
                else:
                    self.errorOccurs = True
                    return

                nearest_esc = None
                esc_found = False

                if esc_bboxes:
                    # Find the nearest escalator
                    min_dst = float('inf')

                    # Center point of frame
                    cx = int(frame.shape[1] / 2)
                    cy = int(frame.shape[0] / 2)

                    for esc in esc_bboxes:
                        # Center point of bounding box
                        ecx = int((esc[1] + esc[3]) / 2)
                        ecy = int((esc[2] + esc[4]) / 2)
                        esc_dst = math.sqrt((cx - ecx) ** 2 + (cy - ecy) ** 2)

                        if esc_dst < min_dst:
                            min_dst = esc_dst
                            nearest_esc = esc

                    # Checking overlapping for step and escalator
                    if nearest_esc:
                        for step in step_bboxes:
                            if is_boxes_overlap(nearest_esc[1:], step[1:]):
                                # print('Step found')
                                nearest_esc[1:] = step[1:]
                                nearest_esc.append(frame)
                                save_frame(frame)
                                esc_found = True
                                break

            if esc_found and nearest_esc is not None:
                self.oldPoints = np.empty((0), np.float32).reshape(0, 2)

                if nearest_esc[0] == 1:
                    # print('Front view Escalator')
                    self.isFrontView = True
                else:
                    # print('Down view Escalator')
                    self.isFrontView = False

                self.setStartPoints(nearest_esc[1:-1])

                # print('Start')
                self.minStepMovement = int((nearest_esc[4] - nearest_esc[2]) * 0.15)
                # print('Min: ', self.minStepMovement)
                prev_frame = gray_scale_frame(nearest_esc[-1])

                cur_time_2 = time.time()
                time_out_2 = cur_time + 3

                while True:
                    cur_time_2 = time.time()

                    inRgb = qRgb.get()

                    if inRgb is not None:
                        frame = inRgb.getCvFrame()
                    else:
                        self.errorOccurs = True
                        return

                    frame = gray_scale_frame(frame)
                    self.calOpticalFlow(prev_frame, frame)
                    prev_frame = frame
                    # self.display(frame)

                    key = cv2.waitKey(1)

                    if key == 27 or cur_time_2 > time_out_2:
                        self.lastFrame = frame
                        break
                cv2.destroyAllWindows()
            else:
                self.escExist = False
                return

        except RuntimeError as e:
            # self.logger.exception("createPipeline(): " + str(e))
            self.pipelineError = True

    def displayLastFrame(self):
        cv2.imshow('Last Frame', self.lastFrame)
        cv2.waitKey(0)

    def run(self):

        if self.device is None or self.pipelineError:
            return False, 'pipeline error'

        self.detectOAKD()

        if self.errorOccurs or len(self.startEndCoords['end']) != len(self.startEndCoords['start']):
            self.initialSetting()
            return False, 'Could not get first frame from camera.'

        if not self.escExist:
            self.initialSetting()
            return True, '找不到電梯'

        escDir = self.identifyDirection()
        self.initialSetting()

        # get the end time
        et = time.time()
        # get the execution time
        elapsed_time = et - self.st
        print('Execution time:', int(elapsed_time), 'seconds')

        return True, escDir
