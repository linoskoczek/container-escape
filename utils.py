import datetime
import string
import random
import socket
import time
import os


def generate_id():
    alphabet = string.ascii_letters + string.digits
    return ''.join([random.choice(alphabet) for n in range(16)])  # return 16 random ascii chars


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for port in range(30000, 40000):
        try:
            s.bind(('127.0.0.1', port))
            s.close()
            return port
        except:
            continue
    return -1
