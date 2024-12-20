import logging
import math
import os
import zipfile
from datetime import datetime, timedelta, date
import requests
from helper import utils
from helper.tradeservice import TradeService
from shoonya.api_helper import ShoonyaApiPy
import pandas as pd

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
            "selectedCandle": "1min",
            "qty": 0,
            "strategy": "pivot"
        }

        self.pivots = {
            "PP": 0,
            "R1": 0,
            "R2": 0,
            "R3": 0,
            "R4": 0,
            "S1": 0,
            "S2": 0,
            "S3": 0,
            "S4": 0,
        }
        self.pivot_upper_level = 0
        self.pivot_lower_level = 0
        self.simulation = False

    def reset_config(self):
        self.config_data = {
            "candles": ["1min", "5min", "15min", "30min", "1hour"],
            "levels": 50,
            "monitoringStatus": False,
            "realTrades": False,
            "selectedCandle": "1min",
            "qty": 0
        }
        self.ltp = 0
        self.pivots = {
            "PP": 0,
            "R1": 0,
            "R2": 0,
            "R3": 0,
            "R4": 0,
            "S1": 0,
            "S2": 0,
            "S3": 0,
            "S4": 0,
        }
        self.pivot_upper_level = 0
        self.pivot_lower_level = 0
        self.upperLevel = 0
        self.lowerLevel = 0

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
        self.reset_config()
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
            if (self.upperLevel == 0 or self.lowerLevel == 0) and self.config_data['strategy'] == 'level':
                print('levels', self.upperLevel, self.lowerLevel, self.freeze)
                self.checkLevelCross();
                print('levels', self.upperLevel, self.lowerLevel, self.freeze)
            elif self.config_data['strategy'] == 'pivot' and any(value == 0 for value in self.pivots.values()):
                print('pivots', self.pivots)
                self.checkLevelCross();
                print('pivots', self.pivots)

            if self.activeTrade:
                self.exitTrade(self.ltp)

            self.freeze = False
        else:
            print(f"Status is {self.config_data['monitoringStatus']}")
        print(f"Status is 2 {self.config_data['monitoringStatus']}")

    def checkLevelCross(self):
        if self.config_data["strategy"] == 'level':
            self.level_strategy()
        elif self.config_data["strategy"] == 'pivot':
            self.pivot_strategy()

    def pivot_strategy(self):
        if any(value == 0 for value in self.pivots.values()):
            self.set_pivot()
        else:
            print("None of the pivot values are zero.")

        if self.pivot_upper_level == 0 or self.pivot_lower_level == 0:
            self.pivot_upper_level, self.pivot_lower_level = self.find_pivot_range()

        print('pivot_upper_level', self.pivot_upper_level, self.pivot_lower_level)

        if self.is_current_time_in_market():
            if self.ltp > self.pivot_upper_level:
                self.tradeAction(self.ltp, True)
                self.pivot_upper_level, self.pivot_lower_level = self.find_pivot_range()
            elif self.ltp < self.pivot_lower_level:
                self.tradeAction(self.ltp, False)
                self.pivot_upper_level, self.pivot_lower_level = self.find_pivot_range()

    def find_pivot_range(self):
        pivot_values = list(self.pivots.values())

        for i in range(len(pivot_values) - 1):
            upper_limit = pivot_values[i]
            lower_limit = pivot_values[i + 1]

            if upper_limit > self.ltp > lower_limit:
                return int(upper_limit), int(lower_limit)
        return None, None

    def set_pivot(self):
        market = self.get_bn_lastday();
        pivots = utils.calculate_pivot_points_levels_4(market['high'], market['low'], market['close'])
        self.pivots = pivots

    def level_strategy(self):
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
        if self.is_current_time_in_buy_market():
            current_time = datetime.now()
            time_string = current_time.strftime("%I:%M %p")
            print('insertTrade', "C:", close, " isUpperLevelCross:", isUpperLevelCross, ' activeTrade:',
                  self.activeTrade)
            print("==========================================================")

            atm = (int(close / 100) * 100) + 100

            if isUpperLevelCross:
                atm = atm - 100
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
                atm = atm + 100
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

        exit_trade = False
        level = 0

        if self.config_data['strategy'] == 'level':
            if self.activeStrike == "CE" and (forceexit or close >= self.upperLevel):
                exit_trade = True
                level = self.upperLevel
            elif self.activeStrike == "PE" and (forceexit or close <= self.lowerLevel):
                exit_trade = True
                level = self.lowerLevel
        elif self.config_data['strategy'] == 'pivot':
            if self.activeStrike == "CE" and (forceexit or close >= self.pivot_upper_level):
                exit_trade = True
                level = self.pivot_upper_level
            elif self.activeStrike == "PE" and (forceexit or close <= self.pivot_lower_level):
                exit_trade = True
                level = self.pivot_lower_level

        if exit_trade and level > 0:
            trade_entry = {
                'marketAt': close,
                'candleCloseAt': time_string,
                'isBuying': False,
                'type': self.activeStrike
            }
            self.trade_service.create_trade(trade_entry)
            self.placeOrders(level, self.activeStrike, False)
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
            'time': current_time_string,
            'qty': self.config_data['qty']
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
        quantity = 15 if self.config_data['qty'] == 0 else self.config_data['qty']
        discloseqty = 0
        price_type = 'MKT'
        price = 0
        trigger_price = None
        retention = 'DAY'
        remarks = 'my_order_001'
        # print(tradingsymbol)
        if self.config_data['realTrades']:
            ret = self.api.place_order(buy_or_sell='B', product_type='C',
                                       exchange='NSE', tradingsymbol=tradingsymbol,
                                       quantity=quantity, discloseqty=discloseqty, price_type=price_type, price=price,
                                       trigger_price=trigger_price,
                                       retention=retention, remarks=remarks)

    def sellOrder(self, strike):
        tradingsymbol = strike['TradingSymbol']
        quantity = 15 if self.config_data['qty'] == 0 else self.config_data['qty']
        discloseqty = 0
        price_type = 'MKT'
        price = 0
        trigger_price = None
        retention = 'DAY'
        remarks = 'my_order_001'
        # print(tradingsymbol)
        if self.config_data['realTrades']:
            ret = self.api.place_order(buy_or_sell='S', product_type='C',
                                       exchange='NSE', tradingsymbol=tradingsymbol,
                                       quantity=quantity, discloseqty=discloseqty, price_type=price_type, price=price,
                                       trigger_price=trigger_price,
                                       retention=retention, remarks=remarks)

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
                if (self.upperLevel == 0 or self.lowerLevel == 0) and self.config_data['strategy'] == 'level':
                    print('levels', self.upperLevel, self.lowerLevel, self.freeze)
                    self.checkLevelCross();
                    print('levels', self.upperLevel, self.lowerLevel, self.freeze)
                elif self.config_data['strategy'] == 'pivot' and any(value == 0 for value in self.pivots.values()):
                    print('pivots', self.pivots)
                    self.checkLevelCross();
                    print('pivots', self.pivots)

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

    def getMarketAt(self):
        return self.ltp

    def is_current_time_in_market(self):
        current_time = datetime.now().time()
        start_time = datetime.strptime('09:15:00', '%H:%M:%S').time()
        end_time = datetime.strptime('15:25:00', '%H:%M:%S').time()
        if self.simulation:
            return True
        else:
            return start_time < current_time < end_time

    def is_current_time_in_buy_market(self):
        current_time = datetime.now().time()
        start_time = datetime.strptime('09:15:01', '%H:%M:%S').time()
        end_time = datetime.strptime('15:14:59', '%H:%M:%S').time()
        if self.simulation:
            return True
        else:
            return start_time < current_time < end_time

    def get_bn_lastday(self):
        try:
            today = datetime.today()
            lastBusDay = today - timedelta(days=5)
            lastBusDay = lastBusDay.replace(hour=0, minute=0, second=0, microsecond=0)
            print('lastBusDay', int(lastBusDay.timestamp()))

            ret = self.api.get_time_price_series(exchange='NSE', token='26009', starttime=int(lastBusDay.timestamp()),
                                                 interval="240")

            if None != ret:
                last_date = None
                open = 0
                close = 0
                high = 0
                low = 0
                for candle in ret:

                    date_object = datetime.strptime(candle['time'], '%d-%m-%Y %H:%M:%S')
                    formatted_date = date_object.strftime('%d-%m-%Y')

                    if None == last_date:
                        last_date = formatted_date
                        high = candle['inth']
                        low = candle['intl']
                        close = candle['intc']
                    elif last_date != None and last_date != formatted_date:
                        last_date = candle['time']
                        open = candle['into']
                        high = candle['inth']
                        low = candle['intl']
                        close = candle['intc']
                    elif last_date != None and last_date == formatted_date:
                        last_date = candle['time']
                        open = candle['into']
                        high = max(high, candle['inth'])
                        low = min(low, candle['intl'])
                        break;

            # open = 0

            if open == 0 or close == 0 or high == 0 or low == 0:
                raise ValueError("One or more variables is equal to 0.")
                return None
            else:
                print("No variable is equal to 0.")

            return {
                "open": float(open),
                "high": float(high),
                "low": float(low),
                "close": float(close)
            }
        except Exception as e:
            print(f"An error occurred: {e}")
