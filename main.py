from flask import (Flask, render_template, request, session, redirect, url_for,
                 flash)
import subprocess as sp
import random
import string
import sys


app = Flask(__name__)
app.secret_key = 'inzynierka123'


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/challenges', methods=['GET'])
def shell():
    return render_template("challenges.html")


@app.route('/runc_cve', methods=['GET'])
def runc_cve():
    if 'id' not in session:
        alphabet = string.ascii_letters + string.digits
        random_id = ''.join([random.choice(alphabet) for n in range(16)])
        session['id'] = random_id
        app.logger.info(f"starting runc challenge for user {session['id']}")
        start_runc_cve_container()
    return render_template("cve-2019-5736.html")


def start_runc_cve_container():
    pass


def build_runc_cve_image():
    return sp.call(['/usr/bin/docker', 'build', '-t', 'vuln_host', 'containers/runc/.'])


if __name__ == '__main__':
    if build_runc_cve_image() != 0:
        sys.exit(-1)
    app.run(debug=True, host='127.0.0.1')
