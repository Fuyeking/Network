import json
import socket
import threading

data_size = 1024


class ServerNode:

    def __init__(self, host, ip_port):
        '''

        :param host: 用于和一个work通信的端口
        :param ip_port: work的IP地址
        '''
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 用于通信的socket
        self.server_socket.bind((host, ip_port))
        self.net_state = False  # 网络连接状态
        self.__socket_reference_count = 0  # socket会在多个线程中被使用，引用次数，在析构过程中，引用次数为0，便可以直接删除
        self.thread_list = []
        self.client = None

    def __del__(self):
        self.__close_socket()

    def __close_socket(self):
        if self.__socket_reference_count == 0:
            self.server_socket.close()

    def set_thread_list(self, thread_list):
        self.thread_list = thread_list

    def increase_reference_count(self):
        self.__socket_reference_count += 1

    def decrease_reference_count(self):
        self.__socket_reference_count -= 1

    def create_conn(self):
        self.server_socket.listen(5)
        while not self.net_state:
            self.client, addr = self.server_socket.accept()
            print('client address', addr)
            self.net_state = True

    def start_send_loss(self):
        self.client.send("OK".encode('utf-8'))

    def run_thread(self):
        for i in range(len(self.thread_list)):
            self.thread_list[i].start()


# 服务端的接受线程
class ServerRecBaseThread(threading.Thread):
    server_obj: ServerNode

    def __init__(self, thread_id, thread_name, server_obj, rec_q, rec_lock):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.thread_name = thread_name
        self.server_obj = server_obj
        self.rec_q = rec_q
        self.rec_lock = rec_lock
        self.server_obj.increase_reference_count()
        print("开启" + self.thread_name)

    def __del__(self):
        self.server_obj.decrease_reference_count()

    def run(self):
        while True:
            self.rec_data()

    def rec_data(self):
        if self.server_obj.net_state:
            data = self.server_obj.client.recv(data_size)
            if data:
                self.rec_lock.acquire()
                self.rec_q.put(self.post_process(data))
                self.rec_lock.release()

    # 可以被之类重载
    def post_process(self, data):
        print("recieve data:", data)
        return json.loads(data.decode())


# 服务端的发送进程
class ServerSendBaseThread(threading.Thread):
    server_obj: ServerNode

    def __init__(self, thread_id, thread_name, server_obj, send_q, send_lock):
        threading.Thread.__init__(self)
        self.thread_id = thread_id
        self.thread_name = thread_name
        self.server_obj = server_obj
        self.send_q = send_q
        self.send_lock = send_lock
        self.server_obj.increase_reference_count()
        print("start the thread" + self.thread_name)

    def __del__(self):
        self.server_obj.decrease_reference_count()

    def run(self):
        while True:
            self.send_data()

    def send_data(self):
        if self.server_obj.net_state:
            self.send_lock.acquire()
            if not self.send_q.empty():
                data = self.send_q.get()
                self.server_obj.client.send(self.pre_process(data))
            self.send_lock.release()

    # 可以被子类重载
    def pre_process(self, data):
        return json.dumps(data).encode()