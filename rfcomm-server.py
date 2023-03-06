import random
import threading
import time

import bluetooth as bt
import json
from EscDetect import EscalatorDetector as eDetector
from ObsDetect import ObsDetect as oDetector
import depthai as dai

escalaIsRunning = False


class BluetoothServer:
    def __init__(self, serverSocket=None, clientSocket=None):
        if serverSocket is None:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket
            self.serviceName = "ATETA"
            self.uuid = "00030000-0000-1000-8000-00805F9B34FB"
        else:
            self.serverSocket = serverSocket
            self.clientSocket = clientSocket

    def getBluetoothSocket(self):
        try:
            self.serverSocket = bt.BluetoothSocket(bt.RFCOMM)
            print("Bluetooth server socket successfully created for RFCOMM service...")
        except (bt.BluetoothError, SystemExit, KeyboardInterrupt) as e:
            print("Failed to create the bluetooth server socket ")

    def getBluetoothConnection(self):
        try:
            self.serverSocket.bind(("", bt.PORT_ANY))
            print("Bluetooth server socket bind successfully on host "" to PORT_ANY ...")
        except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt) as e:
            print("Failed to bind server socket on host to PORT_ANY ...")
        try:
            self.serverSocket.listen(1)
            print("Bluetooth server socket put to listening mode successfully ...")
        except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt) as e:
            print("Failed to put server socket to listening mode ...")
        try:
            port = self.serverSocket.getsocketname()[1]
            print("Waiting for connection on RFCOMM channel ", port)
        except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt):
            print("Failed to get connection on RFCOMM channel ...")

    def advertiseBluetoothService(self):
        try:
            bt.advertise_service(
                self.serverSocket,
                self.serviceName,
                service_id=self.uuid,
                service_classes=[self.uuid, bt.SERIAL_PORT_CLASS],
                profiles=[bt.SERIAL_PORT_PROFILE]
            )
            print(self.serviceName, "advertised successfully")
        except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt):
            print("Failed to advertise bluetooth services ...")

    def acceptBluetoothConnection(self):
        try:
            self.clientSocket, client_info = self.serverSocket.accept()
            print("Accepted bluetooth connection from ", client_info)

        except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt):
            print("Failed to accept bluetooth connection ...")

    def startBluetoothServer(self):
        self.getBluetoothSocket()
        self.getBluetoothConnection()
        self.advertiseBluetoothService()

    def receiveMessage(self):
        length = 1024
        try:
            data = self.clientSocket.recv(length)
            data = data.decode("utf-8")
            data_json = json.loads(data)
            return data_json
        except (Exception, IOError, bt.BluetoothError):
            pass

    def sendMessage(self, reply):
        try:
            self.clientSocket.send(reply)
        except (bt.BluetoothError):

            btServer.serverSocket.close()
            btServer.clientSocket.close()


class ServiceSwitcher:
    def __init__(self, blue_server: BluetoothServer, dev: dai.Device):
        self.blueServer = blue_server
        self.dev = dev
        self.currentService = None

    def startReceiveMessage(self):
        terminate = True
        print("re-established connection")
        while terminate:
            try:
                data = self.blueServer.receiveMessage()
                # print("Received ", data)

                # Switching service mode
                mode = data["mode"]
                # print(self.currentService.name)
                if mode == "obstacle":
                    if self.currentService is None:
                        print("Service begin ...")
                        self.logService("obstacle")
                        self.currentService = ObstacleService(self.blueServer, dev=self.dev)
                        self.currentService.runService()
                    elif self.currentService.name != "Obstacle Service":
                        self.logService("obstacle")
                        self.currentService.terminateService()
                        self.currentService = ObstacleService(self.blueServer, dev=self.dev)
                        self.currentService.runService()

                elif mode == "elevator":
                    if self.currentService.name != "Elevator Service":
                        self.logService("elevator")
                        self.currentService.terminateService()
                        self.currentService = EscalatorService(self.blueServer, dev=self.dev)
                        self.currentService.runService()

                elif mode == "stop":
                    self.currentService.terminateService()
                    self.currentService = None
                    print("Service stop ...")

                else:
                    sendSwitchServiceResponse(self.blueServer, "unknown command")

            except (bt.BluetoothError, TypeError):
                print("Closing the client socket")
                # if self.blueServer.clientSocket is not None:
                self.blueServer.clientSocket.close()
                # self.blueServer.serverSocket.close()
                terminate = False
                if self.currentService is not None:
                    self.currentService.terminateService()
                pipe_device = pipe_manager.get_device()
                if pipe_device is not None:
                    pipe_device.close()

    def logService(self, serviceName):
        print("Service Switcher: Starting", serviceName, "service ...")


def sendSwitchServiceResponse(bServer, mode):
    messageString = f"{mode}模式"
    responseDict = {"action": "switch mode", "message": messageString}
    jsonString = json.dumps(responseDict, indent=4)
    response = jsonString.encode("utf-8")
    bServer.sendMessage(response)
    print(f"Sending {jsonString}")
    time.sleep(1.5)


class ObstacleService:
    def __init__(self, bluetooth_server: BluetoothServer, dev: dai.Device):
        self.terminate = False
        self.serviceThread = None
        self.name = "Obstacle Service"
        self.btServer = bluetooth_server
        self.device = dev
        self.detector = oDetector(device)

    def _runService(self):
        while not self.terminate:
            self.obstacleMode()
            time.sleep(1)

    def runService(self):
        sendSwitchServiceResponse(self.btServer, "障礙物")
        self.serviceThread = threading.Thread(target=self._runService)
        self.serviceThread.start()

    def terminateService(self):
        print("Terminating", self.name, "...")
        self.terminate = True

    def obstacleMode(self):
        result = self.detector.retrieve_message()
        # result = "fuckyou"
        if not self.terminate:
            self.sendResponse(result)

    def sendResponse(self, result):
        responseDict = {"action": "obstacle detection", "message": result}
        jsonString = json.dumps(responseDict, indent=4)
        response = jsonString.encode("utf-8")
        print(f"Sending {jsonString}")
        self.btServer.sendMessage(response)


class EscalatorService:
    def __init__(self, bluetooth_server: BluetoothServer, dev: dai.Device):
        self.terminate = False
        self.serviceThread = None
        self.name = "Elevator Service"
        self.btServer = bluetooth_server
        self.detector = eDetector(dev)

    def _runService(self):
        global escalaIsRunning
        while not self.terminate:
            if not escalaIsRunning:
                escalaIsRunning = True
                self.elevatorMode()
                escalaIsRunning = False
                # time.sleep(1)

    def runService(self):
        sendSwitchServiceResponse(self.btServer, "電梯")
        self.serviceThread = threading.Thread(target=self._runService)
        self.serviceThread.start()

    def terminateService(self):
        print("Terminating", self.name, "...")
        self.terminate = True

    def elevatorMode(self):
        status, msg = self.detector.run()
        # status = True
        # msg = "escalator"
        if not self.terminate and status:
            self.sendResponse(msg)

    def sendResponse(self, result):
        responseDict = {"action": "elevator direction", "message": result}
        jsonString = json.dumps(responseDict, indent=4)
        response = jsonString.encode("utf-8")
        self.btServer.sendMessage(response)
        print(f"Sending {jsonString}")


class PipelineManger:
    def __init__(self):
        self.pipeline = None
        self.device = None

    def setup_pipeline(self):
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
        self.pipeline = pipe

    def create_device(self):
        self.device = dai.Device(self.pipeline)
        return self.device

    def get_device(self):
        return self.device


if __name__ == '__main__':
    btServer = BluetoothServer()
    pipe_manager = PipelineManger()
    btServer.startBluetoothServer()
    pipe_manager.setup_pipeline()
    try:
        while True:
            btServer.acceptBluetoothConnection()
            device = pipe_manager.get_device()
            if device is not None:
                device.close()
            device = pipe_manager.create_device()

            switchManager = ServiceSwitcher(btServer, dev=device)
            switchManager.startReceiveMessage()
    except (KeyboardInterrupt, SystemExit):
        device = pipe_manager.get_device()
        if device is not None:
            device.close()
        btServer.serverSocket.close()
        btServer.clientSocket.close()
        if switchManager.currentService is not None:
            switchManager.currentService.terminateService()
        print("Stopping the server")
