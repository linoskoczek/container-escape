from main import client, keepalive_containers

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


def remove_orphans():
    while True:
        time.sleep(300)
        current_time = datetime.datetime.now()
        print('[+] removing orphaned containers')
        for container_name in list(keepalive_containers.keys()):
            delta = current_time - keepalive_containers[container_name]
            if (delta.seconds > 300):
                del keepalive_containers[container_name]
                client.containers.get(container_name).stop()
                os.remove(f'/etc/nginx/sites-enabled/containers/{container_name}.conf')
                print(f'[+] stopped and removed container and config of {container_name}')

        for container in client.containers.list():
            if container.name not in keepalive_containers.keys():
                try:
                    os.remove(f'/etc/nginx/sites-enabled/containers/{container.name}.conf')
                except:
                    pass
                container.stop()
                print(f'[+] stopped and removed container and config of {container.name}')
