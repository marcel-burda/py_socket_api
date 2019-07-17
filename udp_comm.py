# -*- coding: utf-8 -*-

# python 3

"""
Class for handling Wifi operations - python 3.6
---------------------------------------
Author: Marcel Burda
Date: 17.07.2019
"""

import socket  # udp services
import time  # time functions like e.g. sleep
import threading  # multi-threading and mutex
import struct  # packing and unpacking byte objects in specified c types
import keyboard  # quitting program


class WifiComm:

    def __init__(self, target_address, port, printing=True):
        """
        When you create a WifiComm object, this initialisation happens.
        :param target_address: (str) target IP address of MCU
        :param port: (int) port number of the socket/communication (see https://bit.ly/1MYu7Qk)
        :param printing: (bool) a flag for printing some information and received/sent data
        """
        # set host address and port
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = port
        # create socket object with UDP services
        self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # bind the socket object to host address and port
        self.udp_sock.bind((self.host, self.port))
        # set printing flag
        self.printing = printing
        if self.printing:
            # print success
            print("UDP Socket successfully created ( host: '" + self.host + "', port: " + str(self.port) + " )")
        # set and print target address
        self.target_address = target_address
        if self.printing:
            print("Target IP address is '" + target_address + "'")
        # initialize thread objects
        self.t1_receive = list()
        self.t1_stop = False
        self.t2_stop = False
        # initialize mutex object (acquire: lock, release: unlock)
        self.mutex = threading.Lock()
        # buffer in which formatted received data is stored
        self.buffer = [['------>']]
        # set format string for unpacking raw received data (see documentation of pythons module struct!)
        self.format_string = 'B'  # this means all incoming bytes are interpreted as uint8

    def __receive_thread(self):
        """
        A internal method, called from 'run_receive_thread'.
        Thread waits till data is arriving and format them then into a readable list. After that the data in the
        list is passed to the buffer.
        """
        while not self.t1_stop:
            # receiving data
            try:
                self.udp_sock.settimeout(3.0)  # code stuck at recvfrom() if nothing received, solution: timeout
                raw_recv = self.udp_sock.recvfrom(2**16)  # arg for recvfrom should be greater than possible data length
            except socket.error as msg:
                if str(msg) == 'timed out':
                    pass
                else:
                    print("WARNING: __receive_thread -> " + str(msg))
            else:
                raw_data = raw_recv[0]
                raw_address = raw_recv[1]
                # 'nice' print out
                if self.printing:
                    print(" DATA RECEIVED -> " + raw_data.hex() + " length: " + str(len(raw_data)) + "  from: " + str(raw_address))
                # for loop stores the raw byte data into a buffer
                ctr = 0
                try:
                    recv_data = struct.unpack(self.format_string * len(raw_data), raw_data)
                except struct.error as msg:
                    print("WARNING: __receive_thread -> " + str(msg))
                else:
                    self.mutex.acquire()  # enter critical section
                    self.buffer += [[recv_data]]
                    self.mutex.release()  # leave critical section

    def run_receive_thread(self):
        """
        Start the receive loop.
        """
        # check if thread is already active, shoots trouble if started multiply times
        if isinstance(self.t1_receive, list):
            # create thread object
            self.t1_receive = threading.Thread(target=self.__receive_thread, args=[])
            # start created thread
            self.t1_receive.start()
            if self.printing:
                print('Started receive thread')

    # noinspection PyMethodMayBeStatic
    def __pack_tx_data(self, send_data, send_data_format):
        """
        A internal method, called by 'send_message'.
        Pack all the information with the corresponding types into a single byte object.
        Byte object is needed by socket module to send.
        :param send_data: (list of int) TX data
        :param send_data_format: (str) format string to pack data, default: all uint8
        :return: the resulting byte object
        """
        # init byte object
        all_data = bytes(0)
        # for loop iterate over send_data list and pack the elements in all_data
        for i in range(len(send_data)):
            try:
                all_data += struct.pack(send_data_format, send_data[i])
            except struct.error as msg:
                print("WARNING: __pack_tx_data -> " + str(msg))
        return all_data

    def send_message(self, send_data, send_data_format='B'):
        """
        Method for triggering a single send command.
        :param send_data: (list of int) TX data
        :param send_data_format: (str) format string to pack data, default: all uint8
        """
        # store ID and Data in a byte object
        msg = self.__pack_tx_data(send_data, send_data_format)
        # send message if length of byte object is greater 0 (=packing was success)
        if len(msg) > 0:
            try:
                self.udp_sock.sendto(msg, (self.target_address, self.port))
            except socket.error as msg:
                print("WARNING: send_message -> " + str(msg))
            else:
                # nice print out
                if self.printing:
                    print(" DATA SENT     -> " + str(send_data))
        else:
            print('WARNING: send_message -> message length is 0')

    def __send_cyclic_thread(self, send_data, send_data_format, interval_time):
        """
        Internal method called by 'run_send_cyclic_thread'
        Simple send loop with a simple nap. Get killed if corresponding t2_stop is set.
        This happens in 'run_send_cyclic_thread'.
        :param send_data: (list of int) TX data
        :param send_data_format: (str) format string to pack data, default: all uint8
        :param interval_time: (int) how long am I allowed to nap lol
        """
        while not self.t2_stop:
            self.send_message(send_data, send_data_format)
            time.sleep(interval_time)

    def run_send_cyclic_thread(self, send_data, send_data_format='B', interval_time=1):
        """
        A method for triggering a send cycle.
        First check if thread is already running. If that is the case, set active thread to False,
        which will break the loop in '__send_cyclic_thread'
        :param send_data: (list of int) TX data
        :param send_data_format: (str) format string to pack data, default: all uint8
        :param interval_time: (float or int) how long is the thread allowed to nap lol lol
        """
        t2 = threading.Thread(target=self.__send_cyclic_thread, args=[send_data, send_data_format, interval_time])
        t2.start()


if __name__ == '__main__':

    # prepare target ip address
    target_ip = socket.gethostbyname(socket.gethostname()).split('.')  # get own ip and split into list
    target_ip[-1] = '255'  # last value of list is 255 (broadcast for testing)
    target_ip = target_ip[0] + '.' + target_ip[1] + '.' + target_ip[2] + '.' + target_ip[3]  # put ip together again
    # set port
    socket_port = 1025
    # create udp class obj
    udp = WifiComm(target_ip, socket_port, printing=True)
    # run receive thread
    udp.run_receive_thread()
    # send data in cyclic thread
    s_data = [1, 2, 3, 4, 0xFF, 0b10101010]
    udp.run_send_cyclic_thread(s_data)

    # exit program condition (press ESC)
    while True:
        if keyboard.is_pressed('esc'):
            udp.t1_stop = True
            udp.t2_stop = True
            break
        time.sleep(0.1)
