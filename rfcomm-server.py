#!/usr/bin/env python3
"""PyBluez simple example rfcomm-server.py

Simple demonstration of a server application that uses RFCOMM sockets.

Author: Albert Huang <albert@csail.mit.edu>
$Id: rfcomm-server.py 518 2007-08-10 07:20:07Z albert $
"""
import threading
import time

import bluetooth as bt
import json


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
        self.clientSocket.send(reply)


class ServiceSwitcher:
    def __init__(self, blueServer):
        self.blueServer = blueServer
        self.currentService = ObstacleService()

    def startReceiveMessage(self):
        terminate = True
        while terminate:
            try:
                data = self.blueServer.receiveMessage()
                # print("Received ", data)

                # Switching service mode
                mode = data["mode"]
                if mode == "obstacle":
                    if self.currentService.name == "Elevator Service":
                        self.logService("obstacle")
                        self.currentService.terminateService()
                        self.currentService = ObstacleService()
                        self.currentService.runService()
                        self.sendSwitchServiceResponse("障礙物")

                elif mode == "elevator":
                    if self.currentService.name == "Obstacle Service":
                        self.logService("elevator")
                        self.currentService.terminateService()
                        self.currentService = ElevatorService()
                        self.currentService.runService()
                        self.sendSwitchServiceResponse("電梯")

                elif mode == "start":
                    self.sendSwitchServiceResponse("障礙物")
                    # check current service
                    print(self.currentService.name)
                    if self.currentService.name == "Elevator Service":
                        print("terminate elevator")
                        print("Service begin ...")
                        self.logService("obstacle")
                        self.currentService.terminateService()
                        self.currentService = ObstacleService()
                        self.currentService.runService()
                    elif self.currentService.serviceThread is None:
                        print("Service begin ...")
                        self.logService("obstacle")
                        self.currentService.runService()

                else:
                    self.sendSwitchServiceResponse("unknown command")

            except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt):
                print("Bluetooth server Failed to receive data")
                self.blueServer.clientSocket.close()
                self.blueServer.serverSocket.close()
                terminate = False
                self.currentService.terminateService()

    def logService(self, serviceName):
        print("Service Switcher: Starting", serviceName, "service ...")

    def sendSwitchServiceResponse(self, mode):
        messageString = f"{mode}模式"
        dict = {"action": "switch mode", "message": messageString}
        jsonString = json.dumps(dict, indent=4)
        response = jsonString.encode("utf-8")
        self.blueServer.sendMessage(response)
        print(f"Sending {response}")


class ObstacleService:
    def __init__(self):
        self.terminate = False
        self.serviceThread = None
        self.name = "Obstacle Service"

    def _runService(self):
        while not self.terminate:
            obstacleMode()

    def runService(self):
        self.serviceThread = threading.Thread(target=self._runService)
        self.serviceThread.start()

    def terminateService(self):
        self.terminate = True


class ElevatorService:
    def __init__(self):
        self.terminate = False
        self.serviceThread = None
        self.name = "Elevator Service"

    def _runService(self):
        while not self.terminate:
            elevatorMode()

    def runService(self):
        self.serviceThread = threading.Thread(target=self._runService)
        self.serviceThread.start()

    def terminateService(self):
        self.terminate = True


def obstacleMode():
    time.sleep(5)
    print("Running obstacle mode ...")


def elevatorMode():
    time.sleep(2)
    print("Running elevator mode ...")


if __name__ == '__main__':
    btServer = BluetoothServer()
    btServer.startBluetoothServer()
    while True:
        btServer.acceptBluetoothConnection()
        switchManager = ServiceSwitcher(btServer)
        switchManager.startReceiveMessage()
