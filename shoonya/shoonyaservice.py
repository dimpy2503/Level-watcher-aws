import logging
import math
import os
import zipfile
from datetime import datetime

import requests

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
activeStrike = ""
activeTradeSymbol = ""

db_path = 'trades.db'
trade_service = TradeService(db_path)

ltp = 0
upperLevel = 0
lowerLevel = 0
activeTrade = False

config_data = {
    "candles": ["1min", "5min", "15min", "30min", "1hour", "1day"],
    "levels": 100,
    "monitoringStatus": False,
    "realTrades": False,
    "selectedCandle": ""
}


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
    global activeTrade
    # print("quote event: {0}".format(time.strftime('%d-%m-%Y %H:%M:%S')) + str(message))
    print(message['lp'])
    if message['lp']:
        ltp = message['lp']
        if activeTrade:
            exitTrade(ltp)


def exitTrade(close):
    global activeTrade
    current_time = datetime.now()
    time_string = current_time.strftime("%I:%M %p")
    if activeStrike == "CE" and close >= upperLevel:
        trade_entry = {
            'marketAt': close,
            'candleCloseAt': time_string,
            'isBuying': True,
            'type': 'CE'
        }
        trade_service.create_trade(trade_entry)
        placeOrders(upperLevel, 'CE', False)
        activeTrade = False
    elif activeStrike == "PE" and close <= lowerLevel:
        trade_entry = {
            'marketAt': close,
            'candleCloseAt': time_string,
            'isBuying': True,
            'type': 'CE'
        }
        trade_service.create_trade(trade_entry)
        placeOrders(lowerLevel, 'PE', False)
        activeTrade = False


def checkLevelCross(close):
    global upperLevel
    global lowerLevel

    print(upperLevel, lowerLevel, close)

    if upperLevel == 0 or lowerLevel == 0:
        upperLevel = round(close / 100) * 100
        lowerLevel = math.floor(close / 100) * 100

    # if lowerLevel == 0:
    #     upperLevel = round(close / 100) * 100
    #     lowerLevel = math.floor(close / 100) * 100

    print('levels', upperLevel, lowerLevel)

    if close >= upperLevel:
        insertTrade(close, True)
        upperLevel = math.ceil(close / 100) * 100  # Set a new upper level
        lowerLevel = math.floor(close / 100) * 100  # Set a new lower level
        # insert trade

    elif close < lowerLevel:
        insertTrade(close, False)
        upperLevel = math.ceil(close / 100) * 100  # Set a new upper level
        lowerLevel = math.floor(close / 100) * 100  # Set a new lower level
        # insert trade


def insertTrade(close, isUpperLevelCross):
    current_time = datetime.now()
    time_string = current_time.strftime("%I:%M %p")

    global activeTrade
    global activeStrike
    if isUpperLevelCross:
        if not activeTrade:
            insert_trade(close, time_string, True, 'CE')
            placeOrders(upperLevel, 'CE', True)
            activeTrade = True
        elif activeTrade:
            insert_trade(close, time_string, False, activeStrike)
            placeOrders(upperLevel, activeStrike, False)
            activeTrade = False
            insertTrade(close, isUpperLevelCross)
    elif not isUpperLevelCross:
        if not activeTrade:
            insert_trade(close, time_string, True, 'PE')
            placeOrders(lowerLevel, 'PE', True)
            activeTrade = True
        elif activeTrade:
            insert_trade(close, time_string, False, activeStrike)
            placeOrders(lowerLevel, activeStrike, False)
            activeTrade = False
            insertTrade(close, isUpperLevelCross)


def insert_trade(close, time_string, isBuying, type):
    global activeStrike
    trade_entry = {
        'marketAt': close,
        'candleCloseAt': time_string,
        'isBuying': isBuying,
        'type': type
    }
    trade_service.create_trade(trade_entry)
    activeStrike = type


def downloadMaster():
    global downloadBook
    root = 'https://shoonya.finvasia.com/'
    # masters = ['NSE_symbols.txt.zip', 'NFO_symbols.txt.zip', 'CDS_symbols.txt.zip', 'MCX_symbols.txt.zip',
    #            'BSE_symbols.txt.zip']

    masters = ['NFO_symbols.txt.zip']

    folder = "./scripmasters/"

    for zip_file in masters:
        print(f'downloading {zip_file}')
        url = root + zip_file
        r = requests.get(url, allow_redirects=True)
        open(folder + zip_file, 'wb').write(r.content)
        file_to_extract = zip_file.split()

        try:
            with zipfile.ZipFile(folder + zip_file) as z:
                z.extractall(folder)
                print("Extracted: ", zip_file)
                downloadBook = True
        except:
            downloadBook = False
            print("Invalid file")

        os.remove(folder + zip_file)
        print(f'remove: {zip_file}')


# application callbacks
def event_handler_order_update(message):
    # print("order event: " + str(message))
    return


def startSocket():
    ret = api.start_websocket(order_update_callback=event_handler_order_update,
                              subscribe_callback=event_handler_quote_update, socket_open_callback=open_callback)


def CandleCloseEvent():
    global ltp
    if ltp == 0:
        print("TLP is 0")
        return

    # checkLevelCross(ltp)
    # elif config_data['monitoringStatus'] == True:
    #     current_time = datetime.now()
    #     current_minute = current_time.minute
    #     # if current_minute % 5 == 0:
    #     #     checkLevelCross(ltp)
    #     #     print(f"End of 5-minute candle at minute {current_minute} time {current_time}")
    #     # else:
    #     #     print(f"Not the end of 5-minute candle at minute {current_minute} time {current_time}")
    #
        if current_minute in [15, 30, 45, 0]:
            checkLevelCross(ltp)
            print(f"End of 5-minute candle at minute {current_minute} time {current_time}")
        else:
            print(f"Not the end of 5-minute candle at minute {current_minute} time {current_time}")


def stopSocket():
    api.close_websocket();


def filterBankNiftyOptions(strike, type):
    masterFile = "./scripmasters/NFO_symbols.txt"
    tradingSymbolList = utils.readFile(masterFile)

    banknifty = []

    for tradingSymbol in tradingSymbolList:
        if 'BANKNIFTY' in tradingSymbol['Symbol']:
            banknifty.append(tradingSymbol)

    unique_expiries = set(item['Expiry'] for item in banknifty)
    date_objects = [datetime.strptime(date_str, '%d-%b-%Y').date() for date_str in unique_expiries]

    options_expiry = None
    today = datetime.now().today().day
    # today = 26

    while options_expiry == None:
        smallest_date_object = min(date_objects)
        if smallest_date_object.day == today:
            date_objects.remove(smallest_date_object)
            continue
        else:
            options_expiry = smallest_date_object.strftime('%d-%b-%Y')
            break

    print('options_expiry', options_expiry)

    # Filter the list to get all rows with the smallest valid expiry date
    rows_with_smallest_valid_expiry = [row for row in banknifty if
                                       row['Expiry'].lower() == options_expiry.lower() and strike in row[
                                           'TradingSymbol'] and type in row[
                                           'OptionType']]

    if len(rows_with_smallest_valid_expiry) > 0:
        return rows_with_smallest_valid_expiry[0]

    return None


def buyOrder(strike):
    tradingsymbol = strike['TradingSymbol']
    quantity = 50
    discloseqty = 0
    price_type = 'MKT'
    price = 0
    trigger_price = None
    retention = 'DAY'
    remarks = 'my_order_001'
    print(tradingsymbol)
    # ret = api.place_order(buy_or_sell='B', product_type='C',
    #                       exchange='NSE', tradingsymbol=tradingsymbol,
    #                       quantity=quantity, discloseqty=discloseqty, price_type=price_type, price=price,
    #                       trigger_price=trigger_price,
    #                       retention=retention, remarks=remarks)


def sellOrder(strike):
    tradingsymbol = strike['TradingSymbol']
    quantity = 50
    discloseqty = 0
    price_type = 'MKT'
    price = 0
    trigger_price = None
    retention = 'DAY'
    remarks = 'my_order_001'
    print(tradingsymbol)
    # ret = api.place_order(buy_or_sell='S', product_type='C',
    #                       exchange='NSE', tradingsymbol=tradingsymbol,
    #                       quantity=quantity, discloseqty=discloseqty, price_type=price_type, price=price,
    #                       trigger_price=trigger_price,
    #                       retention=retention, remarks=remarks)


downloadBook = False


def placeOrders(strike, type, isBuy):
    global downloadBook
    global activeTradeSymbol

    if not downloadBook:
        downloadMaster()
        downloadBook = True;
    strike = filterBankNiftyOptions(str(strike), type)
    if isBuy:
        buyOrder(strike)
        activeTradeSymbol = strike
    else:
        sellOrder(activeTradeSymbol)

    current_time = datetime.now().time()
    current_time_string = current_time.strftime('%H:%M:%S')  # 24-hour format

    entry = {
        'strike': activeTradeSymbol['TradingSymbol'],
        'ltp': 0,
        'time': current_time_string
    }
    trade_service.create_ledger_entry(entry)


def getPrice(token):
    exch = 'NSE'
    ret = api.get_quotes(exchange=exch, token=token)
    print(ret)


def mockTest(close):
    global ltp
    global upperLevel
    global lowerLevel
    ltp = close
    if upperLevel == 0 or lowerLevel == 0:
        print('mockTest levels', upperLevel, lowerLevel)
        checkLevelCross(ltp);

    if activeTrade:
        exitTrade(ltp)


# login("")
setSession()
getHoldings()
# strike = filterBankNiftyOptions(strike, type)
# getPrice(strike['Token'])
# print(strike)

# current_time = datetime.datetime.now()
# current_minute = current_time.minute
# print('current_minute',current_minute)
