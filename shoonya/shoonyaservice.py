import datetime
import logging
import math

from helper import utils
from helper.tradeservice import TradeService
from shoonya.api_helper import ShoonyaApiPy
import time

# enable dbug to see request and responses
logging.basicConfig(level=logging.DEBUG)

# start of our program
api = ShoonyaApiPy()

uid = "FA54939"
vc = "FA54939_U"
app_key = "456bd303324fa7cf27fdcbe164a8a200"
pwd = "Dimpy@2503"
imei = "abc1234"
susertoken = ""

db_path = 'trades.db'
trade_service = TradeService(db_path)

ltp = 0
upperLevel = 0
lowerLevel = 0
activeTrade = False

def login(totp):
    try:
        # make the api call
        ret = api.login(userid=uid, password=pwd, twoFA=totp, vendor_code=vc, api_secret=app_key, imei=imei)
        if ret:
            utils.writeJson(ret, 'config')
            setSession()
            return True
        else:
            return False
    except Exception as e:
        return False
        print(f"An exception occurred: {e}")


def setSession():
    data = utils.readJson('config')
    susertoken = data['susertoken']
    print("susertoken", susertoken)
    api.set_session(uid, pwd, susertoken)


def getHoldings():
    try:
        ret = api.get_holdings()
        if ret != None:
            # startSocket();
            return True
        else:
            return False
    except Exception as e:
        return False
        print(f"An exception occurred: {e}")
        return False


def logout():
    api.close_websocket()
    api.logout()


def open_callback():
    global socket_opened
    socket_opened = True
    print('app is connected')
    api.subscribe('NSE|26009')


def event_handler_quote_update(message):
    global ltp
    # print("quote event: {0}".format(time.strftime('%d-%m-%Y %H:%M:%S')) + str(message))
    print(message['lp'])
    if message['lp']:
        ltp = message['lp']


def checkLevelCross(close):
    global upperLevel
    global lowerLevel

    if upperLevel == 0:
        upperLevel = round(close / 100) * 100
        lowerLevel = math.floor(close / 100) * 100

    if lowerLevel == 0:
        upperLevel = round(close / 100) * 100
        lowerLevel = math.floor(close / 100) * 100

    if close >= upperLevel:
        upperLevel = math.ceil(close / 100) * 100  # Set a new upper level
        lowerLevel = math.floor(close / 100) * 100  # Set a new lower level
        # insert trade
    elif close < lowerLevel:
        upperLevel = math.ceil(close / 100) * 100  # Set a new upper level
        lowerLevel = math.floor(close / 100) * 100  # Set a new lower level
        # insert trade


def insertTrade(close, isUpperLevelCross):
    current_time = datetime.datetime.now()
    time_string = current_time.strftime("%I:%M %p")

    global activeTrade
    if isUpperLevelCross:
        if not activeTrade:
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': True,
                'type': 'CE'
            }
            trade_service.create_trade(trade_entry)
            activeTrade = True
        elif activeTrade:
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': False,
                'type': 'CE'
            }
            trade_service.create_trade(trade_entry)
            activeTrade = False
            insertTrade(close, isUpperLevelCross)
    elif not isUpperLevelCross:
        if not activeTrade:
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': True,
                'type': 'PE'
            }
            trade_service.create_trade(trade_entry)
            activeTrade = True
        elif activeTrade:
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': False,
                'type': 'PE'
            }
            trade_service.create_trade(trade_entry)
            activeTrade = False
            insertTrade(close, isUpperLevelCross)


# application callbacks
def event_handler_order_update(message):
    # print("order event: " + str(message))
    return


def startSocket():
    ret = api.start_websocket(order_update_callback=event_handler_order_update,
                              subscribe_callback=event_handler_quote_update, socket_open_callback=open_callback)


def CandleCloseEvent():
    global ltp
    current_time = datetime.datetime.now()
    current_minute = current_time.minute

    if current_minute % 5 == 0:
        checkLevelCross(ltp)
        print(f"End of 5-minute candle at minute {current_minute} time {current_time}")
    else:
        print(f"Not the end of 5-minute candle at minute {current_minute} time {current_time}")


def stopSocket():
    api.close_websocket();


# login("")
setSession()
getHoldings()

# current_time = datetime.datetime.now()
# current_minute = current_time.minute
# print('current_minute',current_minute)
