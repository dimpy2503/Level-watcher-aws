import random
import time
# from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify, session, render_template, url_for, redirect
import logging
from dotenv import load_dotenv
from helper import requesthandler
from helper.tradeservice import TradeService
import threading
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from shoonya.shoonyaservice import TradingApp

load_dotenv()
import os

port = os.getenv("port")
db_path = 'trades.db'

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.secret_key = os.urandom(24)

trade_service = TradeService(db_path)


# only routs
@app.route("/")
@app.route("/login")
@app.route("/dashboard")
def login():
    return render_template(requesthandler.login())


@app.route("/logout")
def logout():
    return render_template(requesthandler.logout())


@app.route("/authenticate")
def authenticate():
    totp = request.args.get("totp")
    print('totp', totp)
    if not totp:
        return """
                <span style="color: red">
                    Please enter factor2.
                </span>
                <a href='/'>Try again.<a>"""
    return requesthandler.authenticate(totp)


@app.route('/api/config', methods=['GET', 'POST'])
def apiconfig():
    if request.method == 'GET':
        return requesthandler.apiconfig()
    elif request.method == 'POST':
        data = request.json
        return requesthandler.updateconfig(data)


@app.route("/config")
def config():
    return render_template(requesthandler.config())


@app.route('/api/trades', methods=['GET'])
def get_all_trades():
    trades = trade_service.get_all_trades()
    print('trades', trades)
    trade_list = [
        {'id': trade[0], 'marketAt': trade[1], 'candleCloseAt': trade[2], 'isBuying': bool(trade[3]), 'type': trade[4]}
        for trade in trades]
    return jsonify(trade_list)


@app.route('/api/ledger-book', methods=['GET'])
def get_all_ledger_entries():
    ledger_entries = trade_service.get_all_ledger_entries()
    ledger_list = [
        {'id': entry[0], 'strike': entry[1], 'ltp': entry[2], 'time': entry[3]}
        for entry in ledger_entries
    ]
    return jsonify(ledger_list)


@app.route('/api/clear-ledger-book', methods=['DELETE'])
def delete_all_ledger_entries():
    trades = trade_service.delete_all_ledger_entries()
    return {}


@app.route('/api/clear-trades', methods=['DELETE'])
def delete_all_trades():
    trades = trade_service.delete_all_trade()
    trades = trade_service.delete_all_ledger_entries()
    return {}


# Initialize the random number
random_number = random.randint(43100, 43500)
random_number_lock = threading.Lock()


# Function to update the random number every second
def update_random_number():
    global random_number
    while True:
        new_random = random.randint(43100, 43900)
        with random_number_lock:
            random_number = new_random
        requesthandler.trading_app.mockTest(new_random)
        time.sleep(10)


if __name__ == "__main__":
    try:
        requesthandler.trading_app.downloadMaster()
        # Start a separate thread to update the random number
        update_thread = threading.Thread(target=update_random_number)
        update_thread.daemon = True
        update_thread.start()

        scheduler = BlockingScheduler()
        # Add your job scheduling code here

        # Schedule the event to run at the end of the 5th minute (replace 5 with your desired minute).
        # scheduler.add_job(shoonyaservice.CandleCloseEvent, 'cron', minute='5', second=0)
        # scheduler.add_job(trading_app.CandleCloseEvent, 'cron', minute='*', second=0)
        # scheduler.add_job(trading_app.CandleCloseEvent, 'cron', minute='*', second=0)
        # scheduler.add_job(requesthandler.CandleCloseEvent, 'cron', minute='*')
        scheduler.add_job(requesthandler.CandleCloseEvent, CronTrigger.from_crontab('* * * * *'))
        # scheduler.add_job(requesthandler.trading_app.CandleCloseEvent, 'cron', second='*')
        scheduler.start()

        app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
    except Exception as e:
        print(f"An error occurred: {e}")
    # app.run(host="0.0.0.0", port=port, debug=True)
