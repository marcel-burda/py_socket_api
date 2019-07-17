# -*- coding: utf-8 -*-

"""
simple script for sniffing on network (must have admin rights)
---------------------------------------
Author: Marcel Burda
Date: 17.07.2019
"""

import socket
import struct
import keyboard

# create a raw socket and bind it to the public interface
s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
host = socket.gethostbyname(socket.gethostname())
s.bind((host, 0))

# Include IP headers
s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

while not keyboard.is_pressed('esc'):
    
    # receive all packages
    s.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    # receive a package
    raw_data = s.recvfrom(2**16)

    data = struct.unpack('B' * len(raw_data[0]), raw_data[0])
    print("from: " + str(raw_data[1]) + " received data: " + str(data))

# disabled promiscuous mode
s.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
