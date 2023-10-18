from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify, session, render_template, url_for, redirect
import logging
from dotenv import load_dotenv
from helper import requesthandler
from helper.tradeservice import TradeService
from shoonya import shoonyaservice

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


@app.route('/api/clear-trades', methods=['DELETE'])
def delete_all_trades():
    trades = trade_service.delete_all_trade()
    return {}


scheduler = BackgroundScheduler()

# Schedule the event to run at the end of the 5th minute (replace 5 with your desired minute).
scheduler.add_job(shoonyaservice.CandleCloseEvent, 'cron', minute='*', second=0)

scheduler.start()

if __name__ == "__main__":
    # app.run(debug=True)
    app.run(host="0.0.0.0", port=port, debug=True)
