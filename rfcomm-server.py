#!/usr/bin/env python3
"""PyBluez simple example rfcomm-server.py

Simple demonstration of a server application that uses RFCOMM sockets.

Author: Albert Huang <albert@csail.mit.edu>
$Id: rfcomm-server.py 518 2007-08-10 07:20:07Z albert $
"""
import threading

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
        self.acceptBluetoothConnection()

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


def startReceiveMessage(blueServer):
    while True:
        try:
            data = blueServer.receiveMessage()
            print("Received ", data)
            # Switching service mode
            mode = data["mode"]
            if mode == "obstacle":
                reply = "obstacle avoidance"
            elif mode == "elevator":
                reply = "elevator detection"
            elif mode == "start":
                reply = "connected"
            else:
                reply = "unknown command"

            reply = reply.encode("utf-8")
            blueServer.sendMessage(reply)
            print(f"Sending {reply}")
        except (Exception, bt.BluetoothError, SystemExit, KeyboardInterrupt):
            print("Bluetooth server Failed to receive data")


if __name__ == '__main__':
    btServer = BluetoothServer()
    btServer.startBluetoothServer()
    btReceiveThread = threading.Thread(target=startReceiveMessage(btServer))
    btReceiveThread.start()
