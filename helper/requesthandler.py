import datetime
import json

from flask import make_response, redirect, jsonify

from helper import utils
from shoonya import shoonyaservice

http_status_codes = {
    "CONTINUE": 100,
    "SWITCHING_PROTOCOLS": 101,
    "OK": 200,
    "CREATED": 201,
    "NO_CONTENT": 204,
    "BAD_REQUEST": 400,
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "INTERNAL_SERVER_ERROR": 500
}

levels = 100;
candle = ["1min", "5min", "15min", "30min", "1hour", "1day"]
selectedCandle = ""
monitoringStatus = True
realTrades = False


def login():
    res = shoonyaservice.getHoldings()
    if res:
        return "dashboard.html"
    else:
        return "index.html"


def authenticate(totp):
    if shoonyaservice.login(totp):
        return "dashboard"
    else:
        return make_response("Login failed", http_status_codes.get("BAD_REQUEST"))


def logout():
    shoonyaservice.logout()
    return "index.html"


def apiconfig():
    return shoonyaservice.config_data


def updateconfig(newconfig):
    if newconfig['monitoringStatus'] == True:
        shoonyaservice.config_data.update(newconfig)
        shoonyaservice.startSocket()
    return jsonify({"message": "Configuration updated successfully"})


def config():
    res = shoonyaservice.getHoldings()
    if res:
        return "config.html"
    else:
        return "index.html"
