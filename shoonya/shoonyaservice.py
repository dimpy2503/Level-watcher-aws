import logging
import math
import os
import zipfile
from datetime import datetime, timedelta, date
import requests
from helper import utils
from helper.tradeservice import TradeService
from shoonya.api_helper import ShoonyaApiPy
import time

logging.basicConfig(level=logging.DEBUG)


class TradingApp:
    def __init__(self):
        self.api = ShoonyaApiPy()
        self.uid = "FA54939"
        self.vc = "FA54939_U"
        self.app_key = "456bd303324fa7cf27fdcbe164a8a200"
        self.pwd = "Dimpy@250383"
        self.imei = "abc1234"
        self.susertoken = ""
        self.activeStrike = ""
        self.activeTradeSymbol = ""
        self.db_path = 'trades.db'
        self.trade_service = TradeService(self.db_path)
        self.ltp = 0
        self.upperLevel = 0
        self.lowerLevel = 0
        self.activeTrade = False
        self.freeze = False
        self.downloadBook = False
        self.socket_opened = False
        self.config_data = {
            "candles": ["1min", "5min", "15min", "30min", "1hour"],
            "levels": 50,
            "monitoringStatus": False,
            "realTrades": False,
            "selectedCandle": "1min"
        }

    def login(self, totp):
        try:
            ret = self.api.login(userid=self.uid, password=self.pwd, twoFA=totp, vendor_code=self.vc,
                                 api_secret=self.app_key, imei=self.imei)
            if ret:
                utils.writeJson(ret, 'config')
                self.setSession()
                return True
            else:
                return False
        except Exception as e:
            return False

    def setSession(self):
        data = utils.readJson('config')
        self.susertoken = data['susertoken']
        self.api.set_session(self.uid, self.pwd, self.susertoken)

    def getHoldings(self):
        try:
            ret = self.api.get_holdings()
            if ret is not None:
                return True
            else:
                return False
        except Exception as e:
            return False

    def logout(self):
        self.closeSocket()
        self.api.logout()

    def closeSocket(self):
        if self.activeTrade:
            self.exitTrade(self.ltp, True)
        self.api.close_websocket()

    def downloadMaster(self):
        global downloadBook
        root = 'https://api.shoonya.com/'
        # masters = ['NSE_symbols.txt.zip', 'NFO_symbols.txt.zip', 'CDS_symbols.txt.zip', 'MCX_symbols.txt.zip',
        #            'BSE_symbols.txt.zip']
        masters = ['NFO_symbols.txt.zip']

        folder = "./scripmasters/"

        for zip_file in masters:
            url = root + zip_file
            print(f'downloading {url}')

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

    def mockTest(self, close):
        if self.freeze:
            return
        elif self.config_data['monitoringStatus']:
            self.freeze = True
            self.ltp = close
            if self.upperLevel == 0 or self.lowerLevel == 0:
                print('mockTest levels', self.upperLevel, self.lowerLevel, self.freeze)
                self.checkLevelCross();

            if self.activeTrade:
                self.exitTrade(self.ltp)

            self.freeze = False
        else:
            print(f"Status is {self.config_data['monitoringStatus']}")
        print(f"Status is {self.config_data['monitoringStatus']}")

    def checkLevelCross(self):
        if self.config_data['levels'] == 100:
            print("100 level")
            if self.upperLevel == 0:
                self.upperLevel = math.ceil(self.ltp / 100) * 100
                self.lowerLevel = math.floor(self.ltp / 100) * 100

            if self.lowerLevel == 0:
                self.upperLevel = math.ceil(self.ltp / 100) * 100
                self.lowerLevel = math.floor(self.ltp / 100) * 100

            print('levels ', "U:", self.upperLevel, " L:", self.lowerLevel, " C:", self.ltp)
            print("==========================================================")

            if self.is_current_time_in_market():
                if self.ltp > self.upperLevel:
                    self.tradeAction(self.ltp, True)
                    self.upperLevel = math.ceil(self.ltp / 100) * 100  # Set a new upper level
                    self.lowerLevel = math.floor(self.ltp / 100) * 100  # Set a new lower level
                    # insert trade

                elif self.ltp < self.lowerLevel:
                    self.tradeAction(self.ltp, False)
                    self.upperLevel = math.ceil(self.ltp / 100) * 100  # Set a new upper level
                    self.lowerLevel = math.floor(self.ltp / 100) * 100  # Set a new lower level
                    # insert trade
        elif self.config_data['levels'] == 50:
            print("50 level")

            if self.upperLevel == 0 or self.lowerLevel == 0:
                last_two_digits = self.ltp % 100
                if last_two_digits > 50:
                    self.upperLevel = self.ltp - last_two_digits + 100
                    self.lowerLevel = self.ltp - last_two_digits + 50
                else:
                    self.upperLevel = self.ltp - last_two_digits + 50
                    self.lowerLevel = self.ltp - last_two_digits

            print('levels ', "U:", self.upperLevel, " L:", self.lowerLevel, " C:", self.ltp)
            print("==========================================================")

            if self.is_current_time_in_market():
                if self.ltp > self.upperLevel:
                    self.tradeAction(self.ltp, True)
                    last_two_digits = self.ltp % 100
                    if last_two_digits > 50:
                        self.upperLevel = self.ltp - last_two_digits + 100
                        self.lowerLevel = self.ltp - last_two_digits + 50
                    else:
                        self.upperLevel = self.ltp - last_two_digits + 50
                        self.lowerLevel = self.ltp - last_two_digits
                elif self.ltp < self.lowerLevel:
                    self.tradeAction(self.ltp, False)
                    last_two_digits = self.ltp % 100
                    if last_two_digits > 50:
                        self.upperLevel = self.ltp - last_two_digits + 100
                        self.lowerLevel = self.ltp - last_two_digits + 50
                    else:
                        self.upperLevel = self.ltp - last_two_digits + 50
                        self.lowerLevel = self.ltp - last_two_digits


    def CandleCloseEvent(self):
        current_time = datetime.now()
        current_minute = current_time.minute

        if self.freeze:
            return
        else:
            self.freeze = True
            # print(f"ltp is {self.ltp}")
            # print(f"config_data {self.config_data}")
            if self.ltp == 0:
                self.freeze = False
                return
            elif self.config_data['monitoringStatus']:
                selectedCandle = self.config_data['selectedCandle']
                # print(f"End of {selectedCandle} candle at minute {current_minute} time {current_time}")
                # ["1min", "5min", "15min", "30min", "1hour"],
                if selectedCandle == '5min' and current_minute in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 0]:
                    self.checkLevelCross()
                elif selectedCandle == '15min' and current_minute in [15, 30, 45, 0]:
                    self.checkLevelCross()
                elif selectedCandle == '30min' and current_minute in [30, 0]:
                    self.checkLevelCross()
                elif selectedCandle == '1hour' and current_minute in [0]:
                    self.checkLevelCross()
                elif selectedCandle == '1min':
                    self.checkLevelCross()
                else:
                    # print(f"Not the end of 5-minute candle at minute {current_minute} time {current_time}")
                    1
            self.freeze = False

    def tradeAction(self, close, isUpperLevelCross):
        current_time = datetime.now()
        time_string = current_time.strftime("%I:%M %p")
        print('insertTrade', "C:", close, " isUpperLevelCross:", isUpperLevelCross, ' activeTrade:', self.activeTrade)
        print("==========================================================")

        atm = (int(close / 100) * 100) + 100

        if isUpperLevelCross:
            if not self.activeTrade:
                self.insert_trade(close, time_string, True, 'CE')
                self.placeOrders(atm, 'CE', True)
                self.activeTrade = True
            elif self.activeTrade:
                self.insert_trade(close, time_string, False, self.activeStrike)
                self.placeOrders(atm, self.activeStrike, False)
                self.activeTrade = False
                self.tradeAction(close, isUpperLevelCross)

        elif not isUpperLevelCross:
            if not self.activeTrade:
                self.insert_trade(close, time_string, True, 'PE')
                self.placeOrders(atm, 'PE', True)
                self.activeTrade = True
            elif self.activeTrade:
                self.insert_trade(close, time_string, False, self.activeStrike)
                self.placeOrders(atm, self.activeStrike, False)
                self.activeTrade = False
                self.tradeAction(close, isUpperLevelCross)

    def insert_trade(self, close, time_string, isBuying, type):
        trade_entry = {
            'marketAt': close,
            'candleCloseAt': time_string,
            'isBuying': isBuying,
            'type': type
        }
        self.trade_service.create_trade(trade_entry)
        self.activeStrike = type

    def exitTrade(self, close, forceexit=False):
        current_time = datetime.now()
        time_string = current_time.strftime("%I:%M %p")
        if self.activeStrike == "CE" and (forceexit or close >= self.upperLevel):
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': False,
                'type': 'CE'
            }
            self.trade_service.create_trade(trade_entry)
            self.placeOrders(self.upperLevel, 'CE', False)
            self.activeTrade = False
        elif self.activeStrike == "PE" and (forceexit or close <= self.lowerLevel):
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': False,
                'type': 'PE'
            }
            self.trade_service.create_trade(trade_entry)
            self.placeOrders(self.lowerLevel, 'PE', False)
            self.activeTrade = False

    def placeOrders(self, strike, type, isBuy):
        print('placeOrders', strike, type, isBuy, self.activeTrade, self.activeTradeSymbol)

        if not self.downloadBook:
            self.downloadMaster()
            self.downloadBook = True;
        strike = self.filterBankNiftyOptions(str(strike), type)
        if isBuy:
            self.buyOrder(strike)
            self.activeTradeSymbol = strike
        else:
            self.sellOrder(self.activeTradeSymbol)

        current_time = datetime.now()
        current_time_string = current_time.strftime('%d %b %H:%M:%S')  # 24-hour format

        entry = {
            'strike': self.activeTradeSymbol['TradingSymbol'],
            'ltp': self.getLtp(self.activeTradeSymbol),
            'time': current_time_string
        }
        self.trade_service.create_ledger_entry(entry)

    def filterBankNiftyOptions(self, strike, type):
        masterFile = "./scripmasters/NFO_symbols.txt"
        tradingSymbolList = utils.readFile(masterFile)

        banknifty = []

        for tradingSymbol in tradingSymbolList:
            if 'BANKNIFTY' in tradingSymbol['Symbol']:
                banknifty.append(tradingSymbol)

        unique_expiries = set(item['Expiry'] for item in banknifty)
        date_objects = [datetime.strptime(date_str, '%d-%b-%Y').date() for date_str in unique_expiries]

        today = date.today()
        filtered_dates = [d for d in date_objects if d > today]
        smallest_greater_date = min(filtered_dates, default=None)
        options_expiry = smallest_greater_date.strftime('%d-%b-%Y')

        # print('options_expiry', options_expiry)

        # Filter the list to get all rows with the smallest valid expiry date
        rows_with_smallest_valid_expiry = [row for row in banknifty if
                                           row['Expiry'].lower() == options_expiry.lower() and strike in row[
                                               'TradingSymbol'] and type in row[
                                               'OptionType']]

        if len(rows_with_smallest_valid_expiry) > 0:
            return rows_with_smallest_valid_expiry[0]

        return None

    def buyOrder(self, strike):
        tradingsymbol = strike['TradingSymbol']
        quantity = 50
        discloseqty = 0
        price_type = 'MKT'
        price = 0
        trigger_price = None
        retention = 'DAY'
        remarks = 'my_order_001'
        # print(tradingsymbol)
        # ret = api.place_order(buy_or_sell='B', product_type='C',
        #                       exchange='NSE', tradingsymbol=tradingsymbol,
        #                       quantity=quantity, discloseqty=discloseqty, price_type=price_type, price=price,
        #                       trigger_price=trigger_price,
        #                       retention=retention, remarks=remarks)

    def sellOrder(self, strike):
        tradingsymbol = strike['TradingSymbol']
        quantity = 50
        discloseqty = 0
        price_type = 'MKT'
        price = 0
        trigger_price = None
        retention = 'DAY'
        remarks = 'my_order_001'
        # print(tradingsymbol)
        # ret = api.place_order(buy_or_sell='S', product_type='C',
        #                       exchange='NSE', tradingsymbol=tradingsymbol,
        #                       quantity=quantity, discloseqty=discloseqty, price_type=price_type, price=price,
        #                       trigger_price=trigger_price,
        #                       retention=retention, remarks=remarks)

    def startSocket(self):
        ret = self.api.start_websocket(order_update_callback=self.event_handler_order_update,
                                       subscribe_callback=self.event_handler_quote_update,
                                       socket_open_callback=self.open_callback)

    # application callbacks
    def event_handler_order_update(self, message):
        # print("order event: " + str(message))
        return

    def event_handler_quote_update(self, message):
        if message['lp'] != None:
            if self.freeze:
                return
            else:
                self.freeze = True
                self.ltp = int(float(message['lp']))
                print(self.ltp)
                if self.upperLevel == 0 or self.lowerLevel == 0:
                    print('levels', self.upperLevel, self.lowerLevel, self.freeze)
                    self.checkLevelCross();

                if self.is_current_time_in_market() == False and self.activeTrade:
                    self.exitTrade(self.ltp, True)

                if self.activeTrade:
                    self.exitTrade(self.ltp)
                self.freeze = False

    def open_callback(self):
        self.socket_opened = True
        self.api.subscribe('NSE|26009')

    def getLtp(self, strike):
        ret = self.api.get_quotes(exchange=strike['Exchange'], token=strike['Token'])
        if 'lp' in ret:
            return ret['lp']
        else:
            return 0

    def is_current_time_in_market(self):
        current_time = datetime.now().time()
        start_time = datetime.strptime('09:15:00', '%H:%M:%S').time()
        end_time = datetime.strptime('15:25:00', '%H:%M:%S').time()
        return start_time < current_time < end_time
