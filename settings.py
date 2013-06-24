from pymongo import MongoClient

# configuration
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True
SECRET = "somesecretkeyhere"
CLIENT = MongoClient('localhost', 27017)
BETAPASS = "somebetapasshere"
db = CLIENT.en4s
