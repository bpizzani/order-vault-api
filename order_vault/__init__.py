from flask import Flask
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # This allows all domains to access your API

from order_vault import main
