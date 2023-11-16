import random
import time
from flask import Flask, request, jsonify, session, render_template, url_for, redirect
import logging
from dotenv import load_dotenv
from helper import requesthandler
from helper.tradeservice import TradeService
import threading
from flask_apscheduler import APScheduler
from flask_socketio import SocketIO

load_dotenv()
import os

os.environ['TZ'] = 'Asia/Kolkata'

port = os.getenv("port")
db_path = 'trades.db'


# set configuration values
class Config:
    SCHEDULER_API_ENABLED = True


logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)
app.config.from_object(Config())
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

scheduler = APScheduler()

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
        {'id': entry[0], 'strike': entry[1], 'ltp': entry[2], 'time': entry[3], 'qty': entry[4]}
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
            print(random_number)
        requesthandler.trading_app.mockTest(new_random)
        time.sleep(5)


def check_market():
    while True:
        market_at = requesthandler.trading_app.getMarketAt()
        handle_update(message=market_at)
        time.sleep(5)


# cron examples
@scheduler.task('cron', id='do_job_2', minute='*')
def job2():
    print('Job 2 executed')
    requesthandler.trading_app.CandleCloseEvent()


@socketio.on('update_value')
def handle_update(message):
    # Broadcast the updated value to all connected clients
    socketio.emit('update_value', {'marketAt': message})


@socketio.on("connect")
def handle_connect():
    print("Client connected")


requesthandler.reinitialize_trading_app()
requesthandler.trading_app.downloadMaster()

if __name__ == "__main__":
    # Start a separate thread to update the random number
    # update_thread = threading.Thread(target=update_random_number)
    # update_thread.daemon = True
    # update_thread.start()

    update_thread = threading.Thread(target=check_market)
    update_thread.daemon = True
    update_thread.start()

    scheduler.init_app(app)
    scheduler.start()
    socketio.run(app, debug=True, host="0.0.0.0", port=port, use_reloader=False, allow_unsafe_werkzeug=True)

    # app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False, threaded=True)
    # app.run(host="0.0.0.0", port=port, debug=True)
