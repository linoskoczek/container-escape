from flask import Flask, render_template, request, session, redirect, url_for, abort
import threading   # used for running cleanup task/thread
import datetime
import docker
import json        # used for API
import time
import sys
import os          # used for file removal

from runc import Runc
import utils

app = Flask(__name__)
app.secret_key = 'inzynierka123'

client = docker.from_env()
keepalive_containers = {}
enabled_challenges = {
    'runc' : Runc(client)
}


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/challenges', methods=['GET'])
def challenges():
    return render_template("challenges.html")


@app.route('/challenges/<challenge>', methods=['GET'])
def display_challenge(challenge):
    if challenge not in enabled_challenges:
        abort(404)

    if 'id' not in session:
        random_id = utils.generate_id()
        session['id'] = random_id
    else:
        try:
            client.containers.get(session['id'])
            random_id = session['id']
        except:
            session.clear()
            return redirect(url_for('display_challenge', challenge=challenge))

    return render_template(f"{challenge}.html", name=random_id)


@app.route('/api/container/keepalive', methods=['GET'])
def keepalive_container():
    global keepalive_containers

    if 'id' in session:
        container_name = session['id']
        keepalive_containers[container_name] = datetime.datetime.now()
        print(f'[+] updated keepalive for {container_name}')
        return json.dumps({'message': 'ok'}), 200

    return json.dumps({'message': 'wrong format'}), 400


@app.route('/api/container/run', methods=['POST'])
def run_container():
    data = (json.loads(request.data))
    
    if data['challenge'] in enabled_challenges and 'id' in session:
        threading.Thread(target=enabled_challenges[data['challenge']].run_instance, args=(session['id'],)).start()
        return json.dumps({'message': "Ok"}), 200

    return json.dumps({'message': "Something wen't wrong"}), 400


@app.route('/api/container/revert', methods=['POST'])
def stop_container():
    data = (json.loads(request.data))

    if 'id' in session:
        try:
            client.containers.get(session['id']).stop()
            threading.Thread(target=enabled_challenges[data['challenge']].run_instance, args=(session['id'],)).start()
        except:
            return 'Error', 400

    return 'Ok', 200


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


def build_challenges():
    client.images.build(tag='runc_vuln_host', path='./containers/runc/')  # runc challenge


if __name__ == '__main__':
    if os.geteuid() != 0:
        print('[!] application requires root privileges (for restarting services and docker stuff)')
        sys.exit(-1)

    try:
        build_challenges()
    except (docker.errors.BuildError, docker.errors.APIError):
        print('[!] something went wrong during building challenge images')

    threading.Thread(target=remove_orphans).start()
    app.run(host='127.0.0.1')
