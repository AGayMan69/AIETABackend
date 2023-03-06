import numpy as np
import cv2 as cv2
import depthai as dai
import time
import skimage.measure
from ObsDetect import ObsDetect as oDetector
from collections import Counter

extended_disparity = True
# for better accuracy for longer distances
subpixel = False
# better handling for occulsions:
lr_check = False
# Create pipeline
pipe = dai.Pipeline()

# nn model
nnPath = 'v5nModel_320/best_openvino_2021.4_6shave.blob'

# Define node
monoLeft = pipe.create(dai.node.MonoCamera)
monoRight = pipe.create(dai.node.MonoCamera)
stereo = pipe.create(dai.node.StereoDepth)
camRgb = pipe.create(dai.node.ColorCamera)
detectionNetwork = pipe.create(dai.node.YoloDetectionNetwork)
xout = pipe.create(dai.node.XLinkOut)
xoutRgb = pipe.create(dai.node.XLinkOut)
nnOut = pipe.create(dai.node.XLinkOut)

xout.setStreamName("disparity")
xoutRgb.setStreamName("rgb")
nnOut.setStreamName("nn")

# Setting properties for depth camera
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)

# Depth node settings
stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
# stereo.setRectifyEdgeFillColor(0)
stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_7x7)
stereo.setLeftRightCheck(lr_check)
stereo.setExtendedDisparity(extended_disparity)
stereo.setSubpixel(subpixel)

config = stereo.initialConfig.get()
config.postProcessing.speckleFilter.enable = True
config.postProcessing.speckleFilter.speckleRange = 5
config.postProcessing.temporalFilter.enable = False
config.postProcessing.spatialFilter.enable = False
config.postProcessing.spatialFilter.holeFillingRadius = 2
config.postProcessing.spatialFilter.numIterations = 1
# config.postProcessing.thresholdFilter.minRange = 400
# config.postProcessing.thresholdFilter.maxRange = 270
config.postProcessing.decimationFilter.decimationFactor = 1
stereo.initialConfig.set(config)
# depth.initialConfig.setConfidenceThreshold(195)
stereo.initialConfig.setLeftRightCheckThreshold(30)

# camRgb.setPreviewSize(640, 640)
camRgb.setPreviewSize(320, 320)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
camRgb.setInterleaved(False)
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
camRgb.setFps(50)

# Network specific settings
detectionNetwork.setConfidenceThreshold(0.6)
detectionNetwork.setNumClasses(3)
detectionNetwork.setCoordinateSize(4)

# 320 * 320
detectionNetwork.setAnchors([
    10.0,
    13.0,
    16.0,
    30.0,
    33.0,
    23.0,
    30.0,
    61.0,
    62.0,
    45.0,
    59.0,
    119.0,
    116.0,
    90.0,
    156.0,
    198.0,
    373.0,
    326.0
])

detectionNetwork.setAnchorMasks({
    "side40": [
        0,
        1,
        2
    ],
    "side20": [
        3,
        4,
        5
    ],
    "side10": [
        6,
        7,
        8
    ]
})

detectionNetwork.setIouThreshold(0.5)
detectionNetwork.setBlobPath(nnPath)
detectionNetwork.input.setBlocking(False)

# Linking
camRgb.preview.link(detectionNetwork.input)
detectionNetwork.passthrough.link(xoutRgb.input)
detectionNetwork.out.link(nnOut.input)
monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)
stereo.disparity.link(xout.input)

# cv windows
cv2.namedWindow('disparity')
cv2.namedWindow('Navig', cv2.WINDOW_AUTOSIZE)
cv2.resizeWindow('Navig', 400, 100)
cv2.moveWindow('disparity', 1800, 500)
cv2.moveWindow('Navig', 5, 5)

# Start pipeline
with dai.Device(pipe) as device:
    oDetect = oDetector(device)
    WAIT_TIME = 1
    direction = []
    cur_time = time.time()
    timeout = cur_time + WAIT_TIME
    while True:
        cur_time = time.time()
        msg = oDetect.get_guide(list_dir=direction, display=True)
        if cur_time >= timeout:
            timeout = cur_time + WAIT_TIME
            count = Counter(direction)
            msg = oDetect.get_direct_msg(count.most_common(1)[0][0])
            # print(msg)
            direction = []
        # time.sleep(1)
        if cv2.waitKey(1) == ord('q'):
            break
