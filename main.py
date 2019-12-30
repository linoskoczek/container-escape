from flask import Flask, render_template, request, session, redirect, url_for
import subprocess
import socket
import errno
import docker
import random
import string
import time
import sys
import os


app = Flask(__name__)
app.secret_key = 'inzynierka123'

client = docker.from_env()
ports_used = []


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/challenges', methods=['GET'])
def shell():
    return render_template("challenges.html")


@app.route('/runc_cve', methods=['GET'])
def runc_cve():
    random_id = ''
    if 'id' not in session:
        alphabet = string.ascii_letters + string.digits
        random_id = ''.join([random.choice(alphabet) for n in range(16)])
        session['id'] = random_id
        try:
            container_name = start_runc_cve_container(random_id)
        except Exception as e:
            return e, 500  # TODO
    else:
        random_id = session['id']
    return render_template("cve-2019-5736.html", name=random_id)


def start_runc_cve_container(user_id):
    port = get_free_port()
    if port == -1:
        raise Exception('Cannot find available port')
    try:
        container = client.containers.run(
            ports={f'{port}/tcp':f'{port}/tcp'}, 
            privileged=True, 
            remove=True, 
            name=user_id,
            detach=True,
            image='runc_vuln_host'
        )
        run_container_inside_container(container, port)
        return container.name
    except (docker.errors.BuildError, docker.errors.APIError) as e:
        print(e)
        return 'Error', 500  # TODO error handling


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
    docker_socket_check = '''sh -c 'test -e /var/run/docker.sock && echo -n \"1\" || echo -n "0"' '''
    while container.exec_run(docker_socket_check)[1].decode('utf-8') != '1':
        time.sleep(0.5)
    if container.exec_run('docker build -t vuln /opt')[0] != 0:  # command exit code
        print(f'something went wrong while building container inside container ({container.id})')
        raise docker.errors.BuildError
    if container.exec_run(f'docker run -p {port}:8081 -d --restart unless-stopped vuln')[0] != 0:
        print(f'something went wrong while running container inside container ({container.id})')
        raise docker.errors.BuildError
    create_nginx_config(container.name, port)


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
    print(subprocess.call(['/usr/sbin/nginx', '-s', 'reload']))


def build_runc_cve_image():
    client.images.build(
        tag='runc_vuln_host',
        path='./containers/runc/'
    )


def cleanup():
    pass


if __name__ == '__main__':
    if os.geteuid() != 0:
        print('[!] Application requires root privileges (service restarting and docker stuff)')
        sys.exit(-1)
    try:
        build_runc_cve_image()
    except (docker.errors.BuildError, docker.errors.APIError):
        print('something went wrong during docker image build')
        sys.exit(-1)
    app.run(debug=True, host='127.0.0.1')
