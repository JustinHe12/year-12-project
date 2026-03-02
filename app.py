from flask import Flask

#Creates the app
app = Flask(__name__)

#Homepage
@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"