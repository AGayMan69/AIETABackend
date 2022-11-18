#!/usr/bin/env python3
"""PyBluez simple example rfcomm-server.py

Simple demonstration of a server application that uses RFCOMM sockets.

Author: Albert Huang <albert@csail.mit.edu>
$Id: rfcomm-server.py 518 2007-08-10 07:20:07Z albert $
"""

import bluetooth
import json

server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
server_sock.bind(("", bluetooth.PORT_ANY))
server_sock.listen(1)

port = server_sock.getsockname()[1]

# uuid = "94f39d29-7d6d-437d-973b-fba39e49d4ee"
uuid = "00030000-0000-1000-8000-00805F9B34FB"

bluetooth.advertise_service(server_sock, "SampleServer", service_id=uuid,
                            service_classes=[uuid, bluetooth.SERIAL_PORT_CLASS],
                            profiles=[bluetooth.SERIAL_PORT_PROFILE],
                            # protocols=[bluetooth.OBEX_UUID]
                            )


print("Waiting for connection on RFCOMM channel", port)

client_sock, client_info = server_sock.accept()
print("Accepted connection from", client_info)
while True:
    length = 1024
    try:
            data = client_sock.recv(length)
            data = data.decode("utf-8")
            data_json = json.loads(data)
            print("Received ", data)
            # Switching service mode
            match data_json["mode"]:
                case "obstacle":
                    reply = "obstacle avoidance"
                case "elevator":
                    reply = "elevator detection"
                case "start":
                    reply = "connected"
                case _:
                    reply = "unknown command"

            client_sock.send(reply)
            print(f"Sending {reply}")
    except KeyboardInterrupt:
        print("Disconnected.")

        client_sock.close()
        server_sock.close()
        print("All done.")
