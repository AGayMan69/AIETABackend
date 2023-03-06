import numpy as np
import cv2 as cv2
import depthai as dai
import time
import skimage.measure
from ObsDetect import ObsDetect as oDetector

extended_disparity = True
# for better accuracy for longer distances
subpixel = False
# better handling for occulsions:
lr_check = True

# Create pipeline
pipeline = dai.Pipeline()

# Define node
monoLeft = pipeline.create(dai.node.MonoCamera)
monoRight = pipeline.create(dai.node.MonoCamera)
depth = pipeline.create(dai.node.StereoDepth)
xout = pipeline.create(dai.node.XLinkOut)

xout.setStreamName("disparity")

# Setting properties for depth camera
monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoLeft.setBoardSocket(dai.CameraBoardSocket.LEFT)
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setBoardSocket(dai.CameraBoardSocket.RIGHT)

# Depth node settings
depth.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
depth.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_5x5)
depth.setLeftRightCheck(lr_check)
depth.setExtendedDisparity(extended_disparity)
depth.setSubpixel(subpixel)

config = depth.initialConfig.get()
config.postProcessing.speckleFilter.enable = True
config.postProcessing.speckleFilter.speckleRange = 5
config.postProcessing.temporalFilter.enable = False
config.postProcessing.spatialFilter.enable = False
config.postProcessing.spatialFilter.holeFillingRadius = 2
config.postProcessing.spatialFilter.numIterations = 1
# config.postProcessing.thresholdFilter.minRange = 400
# config.postProcessing.thresholdFilter.maxRange = 270
config.postProcessing.decimationFilter.decimationFactor = 1
depth.initialConfig.set(config)
# depth.initialConfig.setConfidenceThreshold(195)
depth.initialConfig.setLeftRightCheckThreshold(30)
# Creating link between nodes
monoLeft.out.link(depth.left)
monoRight.out.link(depth.right)
depth.disparity.link(xout.input)

# cv windows
cv2.namedWindow('disparity')
cv2.namedWindow('Navig', cv2.WINDOW_AUTOSIZE)
cv2.resizeWindow('Navig', 400, 100)
cv2.moveWindow('disparity', 1800, 500)
cv2.moveWindow('Navig', 5, 5)

# Start pipeline
with dai.Device(pipeline) as device:
    oDetect = oDetector(device)
    while True:
        msg = oDetect.retrieve_message()
        time.sleep(1)
        if cv2.waitKey(1) == ord('q'):
            break
