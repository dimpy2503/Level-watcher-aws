import sqlite3


class TradeService:
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._create_table()

    def _create_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY,
                marketAt TEXT,
                candleCloseAt TEXT,
                isBuying INTEGER,
                type TEXT
            )
        ''')
        self.conn.commit()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ledger_book (
                id INTEGER PRIMARY KEY,
                strike REAL,
                ltp REAL,
                time TEXT,
                qty TEXT
            )
        ''')
        self.conn.commit()

    def create_ledger_entry(self, entry):
        sql = 'INSERT INTO ledger_book (strike, ltp, time, qty) VALUES (?, ?, ?, ?)'
        self.cursor.execute(sql, (entry['strike'], entry['ltp'], entry['time'], entry['qty']))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_ledger_entry(self, entry_id):
        sql = 'SELECT * FROM ledger_book WHERE id = ?'
        self.cursor.execute(sql, (entry_id,))
        return self.cursor.fetchone()

    def get_all_ledger_entries(self):
        sql = 'SELECT * FROM ledger_book ORDER BY id desc'
        self.cursor.execute(sql, ())
        return self.cursor.fetchall()

    def update_ledger_entry(self, entry_id, entry):
        sql = 'UPDATE ledger_book SET strike=?, ltp=?, time=? WHERE id=?'
        self.cursor.execute(sql, (entry['strike'], entry['ltp'], entry['time'], entry_id))
        self.conn.commit()

    def delete_ledger_entry(self, entry_id):
        sql = 'DELETE FROM ledger_book WHERE id = ?'
        self.cursor.execute(sql, (entry_id,))
        self.conn.commit()

    def delete_all_ledger_entries(self):
        sql = 'DELETE FROM ledger_book'
        self.cursor.execute(sql)
        self.conn.commit()

    def create_trade(self, trade):
        sql = 'INSERT INTO trades (marketAt, candleCloseAt, isBuying, type) VALUES (?, ?, ?, ?)'
        self.cursor.execute(sql, (trade['marketAt'], trade['candleCloseAt'], trade['isBuying'], trade['type']))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_trade(self, trade_id):
        sql = 'SELECT * FROM trades WHERE id = ?'
        self.cursor.execute(sql, (trade_id,))
        return self.cursor.fetchone()

    def get_all_trades(self):
        sql = 'SELECT * FROM trades ORDER BY id desc'
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def update_trade(self, trade_id, trade):
        sql = 'UPDATE trades SET marketAt=?, candleCloseAt=?, isBuying=?, type=? WHERE id=?'
        self.cursor.execute(sql,
                            (trade['marketAt'], trade['candleCloseAt'], trade['isBuying'], trade['type'], trade_id))
        self.conn.commit()

    def delete_trade(self, trade_id):
        sql = 'DELETE FROM trades WHERE id = ?'
        self.cursor.execute(sql, (trade_id,))
        self.conn.commit()

    def delete_all_trade(self, ):
        sql = 'DELETE FROM trades'
        self.cursor.execute(sql)
        self.conn.commit()
