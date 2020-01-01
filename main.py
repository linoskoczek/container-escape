"""
TODOs:
====
 * revert button on challenge page
 * shutdown button on challenge page
 * hints on challenge page (optionally)
 * runc challenge solve infromation (bootstrap Modal component)
 * runc challenge description popup (also Modal)
 * review and fix esception handling in whole
"""
from flask import Flask, render_template, request, session, redirect, url_for
import docker

import subprocess
import threading
import datetime
import socket
import random
import string
import json
import time
import sys
import os


app = Flask(__name__)
app.secret_key = 'inzynierka123'

client = docker.from_env()
created_containers = []
keepalive_containers = {}


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/challenges', methods=['GET'])
def challenges():
    return render_template("challenges.html")


@app.route('/runc_cve', methods=['GET'])
def runc_cve():
    random_id = ''

    if 'id' not in session:
        alphabet = string.ascii_letters + string.digits
        random_id = ''.join([random.choice(alphabet) for n in range(16)])
        session['id'] = random_id
        global created_containers
        created_containers.append(f'{random_id}')
        threading.Thread(target=start_runc_cve_container, args=(random_id,)).start()
    else:
        try:
            client.containers.get(session['id'])
            random_id = session['id']
        except docker.errors.NotFound:
            session.pop('id', None)
            return redirect(url_for('runc_cve'))

    return render_template("cve-2019-5736.html", name=random_id)


@app.route('/api/container/keepalive', methods=['POST'])
def keepalive_container():
    global keepalive_containers
    data = json.loads(request.data)
    if 'id' in data:
        container_name = data['id']
        keepalive_containers[container_name] = datetime.datetime.now()
        print(f'[+] updated keepalive for {container_name}')
        return json.dumps({'status': 'ok'}), 200
    
    return json.dumps({'status': 'wrong format'}), 400


def start_runc_cve_container(user_id):
    port = get_free_port()

    if port == -1:
        print("[!] couldn't find available port")
        return

    try:
        container = client.containers.run(
            ports={f'{port}/tcp': f'{port}/tcp'},
            privileged=True,
            remove=True,
            name=user_id,
            detach=True,
            image='runc_vuln_host'
        )
        run_container_inside_container(container, port)
        create_nginx_config(container.name, port)
    except (docker.errors.BuildError, docker.errors.APIError) as e:
        print(e)
        return


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


def run_container_inside_container(container, port):
    docker_socket_check = '''sh -c 'test -e /var/run/docker.sock && echo -n "1" || echo -n "0"' '''

    while container.exec_run(docker_socket_check)[1].decode('utf-8') != '1':
        time.sleep(0.5)

    build_result = container.exec_run('docker build -t vuln /opt')
    if build_result[0] != 0:  # check if command exit code is 0
        print(f'[!] something went wrong while building internal container for {container.name}\n{build_result[1]}')
        raise docker.errors.BuildError

    run_result = container.exec_run(f'docker run -p {port}:8081 -d --restart unless-stopped vuln')
    if run_result[0] != 0:  # check if command exit code is 0
        print(f'[!] something went wrong while running internal container{container.name}\n{run_result[1]}')
        raise docker.errors.BuildError

    print(f'[+] internal container created for {container.name}')


def create_nginx_config(container_name, port):
    config =  'location /runc-cve-%s/ {\n' % container_name
    config += '    proxy_pass http://127.0.0.1:%s/;\n' % port
    config += '    proxy_http_version 1.1;\n'
    config += '    proxy_set_header X-Real-IP $remote_addr;\n'
    config += '    proxy_set_header Upgrade $http_upgrade;\n'
    config += '    proxy_set_header Connection "Upgrade";\n'
    config += '}\n'

    config_path = f'/etc/nginx/sites-enabled/containers/{container_name}.conf'
    with open(config_path, 'w+') as f:
        f.write(config)

    subprocess.call(['/usr/sbin/nginx', '-s', 'reload'])
    print(f'[+] nginx config created and reloaded for {container_name}')


def build_runc_cve_image():
    client.images.build(
        tag='runc_vuln_host',
        path='./containers/runc/'
    )


def cleanup(container_name):
    try:
        os.remove(f'/etc/nginx/sites-enabled/containers/{container_name}.conf')
        print(f'[+] removed nginx config for {container_name}')
    except OSError as e:
        print(e)

    try:
        client.containers.get(container_name).stop()
        print(f'[+] stopped container for {container_name}')
    except docker.errors.APIError as e:
        print(e)
        print(f"[!] couldn't stop container {container_name} while cleaning, it might need manual removal")


def remove_orphans():
    while True:
        time.sleep(600)
        current_time = datetime.datetime.now()
        print('[+] removing orphaned containers')
        for container_name in list(keepalive_containers.keys()):
            delta = current_time - keepalive_containers[container_name]
            if (delta.seconds > 600):
                del keepalive_containers[container_name]
                client.containers.get(container_name).stop()
                os.remove(f'/etc/nginx/sites-enabled/containers/{container_name}.conf')
                print(f'[+] stopped and removed container and config of {container_name}')


if __name__ == '__main__':
    if os.geteuid() != 0:
        print('[!] application requires root privileges (service restarting and docker stuff)')
        sys.exit(-1)

    try:
        build_runc_cve_image()
    except (docker.errors.BuildError, docker.errors.APIError):
        print('[!] something went wrong during docker image build')

    threading.Thread(target=remove_orphans).start()
    app.run(debug=True, host='127.0.0.1')
