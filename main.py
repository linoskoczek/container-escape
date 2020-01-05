from flask import Flask, render_template, request, session, redirect, url_for, abort
import threading
import datetime
import docker
import json
import os

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
        random_id = challenge + '-' + utils.generate_id()
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
            enabled_challenges[data['challenge']].remove_instance(session['id'])
            threading.Thread(target=enabled_challenges[data['challenge']].run_instance, args=(session['id'],)).start()
        except Exception as e:
            print(e)
            return 'Error', 400

    return 'Ok', 200


if __name__ == '__main__':
    utils.check_privs()
    utils.build_challenges(client)
    threading.Thread(target=utils.remove_orphans, args=(client, keepalive_containers)).start()
    app.run(host='127.0.0.1')
