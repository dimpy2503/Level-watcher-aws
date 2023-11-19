from flask import make_response, jsonify
from shoonya.shoonyaservice import TradingApp

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


# trading_app = TradingApp()
# trading_app.setSession()


def reinitialize_trading_app():
    global trading_app  # Use the global variable
    trading_app = TradingApp()  # Create a new instance of the TradingApp class
    trading_app.setSession()
    trading_app.get_bn_lastday()


def CandleCloseEvent():
    trading_app.CandleCloseEvent()


def login():
    res = trading_app.getHoldings()
    if res:
        return "dashboard.html"
    else:
        return "index.html"


def authenticate(totp):
    if trading_app.login(totp):
        return "dashboard"
    else:
        return make_response("Login failed", http_status_codes.get("BAD_REQUEST"))


def logout():
    trading_app.logout()
    return "index.html"


def apiconfig():
    return trading_app.config_data


def updateconfig(newconfig):
    trading_app.config_data.update(newconfig)
    print(trading_app.config_data)
    if newconfig['monitoringStatus']:
        trading_app.startSocket()
        1
    else:
        trading_app.closeSocket()
        reinitialize_trading_app()
    return jsonify({"message": "Configuration updated successfully"})


def config():
    res = trading_app.getHoldings()
    if res:
        return "config.html"
    else:
        return "index.html"

# reinitialize_trading_app();

# strike = trading_app.filterBankNiftyOptions('43700', 'CE')
# print(strike)
# print(trading_app.getLtp(strike))
