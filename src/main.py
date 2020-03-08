from flask import Flask, render_template, request, session, redirect, url_for
from flask import abort, jsonify
import threading
import datetime
import logging
import docker
import os

import utils


app = Flask(__name__)
app.secret_key = 'inzynierka123'

app.logger.setLevel(logging.DEBUG)
formatter = app.logger.handlers[0].formatter
handler = logging.FileHandler('./sandbox-escape.log')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

client = docker.from_env()
keepalive_containers = {}
solved_challenges = []
enabled_challenges = {}


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/challenges', methods=['GET'])
def challenges_page():
    return render_template("challenges.html", challenges=enabled_challenges)


@app.route('/challenges/<challenge>', methods=['GET'])
def challenge_page(challenge):
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
            return redirect(url_for('challenge_page', challenge=challenge))

    return render_template(f"{challenge}.html", user_id=random_id)


@app.route('/api/container/keepalive', methods=['GET'])
def keepalive_container():
    global keepalive_containers

    if 'id' in session:
        container_name = session['id']
        keepalive_containers[container_name] = datetime.datetime.now()
        app.logger.info(f'updated keepalive for {container_name}')
        return jsonify(message='ok'), 200

    return jsonify(message='wrong format'), 400


@app.route('/api/container/run', methods=['GET'])
def run_container():
    if 'id' in session:
        challenge = session['id'].split('-')[0]

        if challenge in enabled_challenges:
            try:
                threading.Thread(target=enabled_challenges[challenge].run_instance, args=(session['id'],)).start()
                return jsonify(message='ok'), 200
            except Exception as e:
                app.logger.error(e)

    return jsonify(message='error'), 400


@app.route('/api/container/revert', methods=['GET'])
def revert_container():
    if 'id' in session:
        challenge = session['id'].split('-')[0]

        if challenge in enabled_challenges:
            try:
                enabled_challenges[challenge].remove_instance(session['id'])
                threading.Thread(target=enabled_challenges[challenge].run_instance, args=(session['id'],)).start()
                return jsonify(message='ok'), 200
            except Exception as e:
                app.logger.error(e)

    return jsonify(message='error'), 400


@app.route('/api/container/status', methods=['GET'])
def container_status():
    if 'id' in session:
        if session['id'] in solved_challenges:
            return jsonify(message='solved'), 200
        else:
            return jsonify(message='not solved'), 200

    return jsonify(message='error'), 400


if __name__ == '__main__':
    utils.check_privs()
    utils.challenges_loader(enabled_challenges, client, solved_challenges)
    utils.build_challenges(enabled_challenges)
    threading.Thread(target=utils.remove_orphans, args=(client, keepalive_containers, enabled_challenges)).start()
    app.run(host='127.0.0.1')
