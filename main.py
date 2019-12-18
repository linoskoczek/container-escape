from flask import Flask, render_template, request, session, redirect, url_for, flash


app = Flask(__name__)
app.secret_key = 'inzynierka123'


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


@app.route('/shell', methods=['GET'])
def shell():
    return render_template("shell.html")


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1')
