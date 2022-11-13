import os, time
from pathlib import Path
import sys
import math
from functools import partial
import logging as log

from PySide2.QtWidgets import QApplication, QWidget, QLabel, QTableWidgetItem, QPushButton, QStyle, QMainWindow, \
    QTableWidget, QLineEdit
from PySide2.QtCore import QFile, QThread, Signal, Qt
from PySide2.QtGui import QIcon, QPixmap, QPalette, QColor, QClipboard, QGuiApplication
from PySide2.QtUiTools import QUiLoader
from PySide2.QtWebEngineWidgets import *

from Broker import Broker

# log.basicConfig(level=log.DEBUG)

class DrawDownManager():
    def __init__(self):
        self.max_open_loss = None
        self.max_dd = 0.05
        self.dd_factor = 10
        self.du_factor = 5
        self.actual_dd = None
        self.is_drawdown = False
        self.is_drawup = False
        self.equity_data = []
        self.actual_equity = None
        self.min = None
        self.max = None

    def preprocess(self):
        equity = self.equity_data

        dd_history = []

        _max = equity[0]
        _min = _max

        for i in equity:
            eq = i

            if eq > _max:

                if _max > _min:

                    dd = (_max - _min) / _max

                    data = {
                        "min": _min,
                        "max": _max,
                        "drawdown": dd
                    }

                    dd_history.append(data)

                    _max = eq
                    _min = _max

                else:
                    _max = eq

            elif eq < _min:
                _min = eq

        self.max = _max
        self.min = _min
        self.actual_equity = self.equity_data[-1]

        print(dd_history)

    def drawdown(self):
        pass

    def load_data(self, dataset):
        if type(dataset) == list:
            if len(dataset) > 0:
                self.equity_data = dataset

                self.preprocess()
                self.drawdown()


class TableItem(QTableWidgetItem):

    def __init__(self, txt, ticket=None, cell_type=None):
        super(TableItem, self).__init__(txt)
        self.ticket = ticket
        self.cell_type = cell_type


class TableManager():
    def __init__(self, parent, display_table=None):
        if display_table is None:
            display_table = QTableWidget()
        self.display_table = display_table
        self.input_table = []
        self.saved_table = []
        self.to_update = []
        self.parent = parent
        self.force_reload = False

    def load_positions(self, positions):
        # print(" ------------ load position ---------------")
        if positions is not None:
            self.to_update = []
            for i in positions:
                self.to_update.append([None, None, None])

            self.input_table = positions
            if self.force_reload:
                reload = True

            else:
                reload = False

            # if saved_table is empty or table lenght are different
            if len(self.saved_table) == 0 or len(self.saved_table) != len(self.input_table):
                reload = True

            # if some ticket in the table are different
            else:
                for i in range(len(self.input_table)):
                    if self.input_table[i]['ticket'] != self.saved_table[i]['ticket']:
                        reload = True
                        break

            # if need reload total table
            if reload:

                self.display_table.clear()
                lines = len(self.input_table)
                self.display_table.setHorizontalHeaderLabels(["Symbol", "Volume", "Open", "SL", "TP", "Profit", "Close"])
                self.display_table.setColumnCount(7)
                self.display_table.setRowCount(lines)

                self.display_table.verticalHeader().hide()

                self.display_table.setColumnWidth(0, 50)

                self.to_update = []

                for i in range(len(self.input_table)):

                    tp = self.input_table[i]['tp']
                    sl = self.input_table[i]['sl']
                    profit = self.input_table[i]['profit']

                    ticket = self.input_table[i]['ticket']
                    symbol = str(self.input_table[i]['symbol'])
                    vol = str(self.input_table[i]['volume'])
                    side = str(self.input_table[i]['side'])
                    entry = str(self.input_table[i]['entry'])

                    symbol = QLabel(str(symbol))
                    symbol.setAlignment(Qt.AlignCenter)

                    entry = QLabel(str(entry))
                    entry.setAlignment(Qt.AlignCenter)

                    if side == "SHORT":
                        vol = '-' + vol
                    elif side == 'LONG':
                        vol = '+' + vol

                    vol = QLabel(str(vol))
                    vol.setAlignment(Qt.AlignCenter)

                    self.display_table.setCellWidget(i, 0, symbol)
                    self.display_table.setCellWidget(i, 1, vol)
                    self.display_table.setCellWidget(i, 2, entry)

                    close_button = QPushButton()
                    pixmapi = getattr(QStyle, 'SP_TitleBarCloseButton')
                    icon = self.parent.style().standardIcon(pixmapi)
                    close_button.setIcon(icon)
                    close_button.clicked.connect(partial(self.parent.broker.close_position, ticket))

                    self.display_table.setCellWidget(i, 6, close_button)

                    profit = QLabel(str(profit))
                    profit.setAlignment(Qt.AlignCenter)
                    self.display_table.setCellWidget(i, 5, profit)

                    if tp > 0.0:
                        tp = str(tp)
                    else:
                        tp = ' '
                    tp = TableItem(tp, ticket, 'tp')
                    tp.setTextAlignment(Qt.AlignCenter)
                    self.display_table.setItem(i, 4, tp)

                    if sl > 0.0:
                        sl = str(sl)
                    else:
                        sl = ' '
                    sl = TableItem(str(sl), ticket, 'sl')
                    sl.setTextAlignment(Qt.AlignCenter)
                    self.display_table.setItem(i, 3, sl)

                self.force_reload = False


            else:
                # if not reload check for update sl/tp/profit
                for i in range(len(self.input_table)):

                    if self.input_table[i]['sl'] != self.saved_table[i]['sl']:
                        self.to_update[i][0] = self.input_table[i]['sl']
                    if self.input_table[i]['tp'] != self.saved_table[i]['tp']:
                        self.to_update[i][1] = self.input_table[i]['tp']
                    if self.input_table[i]['profit'] != self.saved_table[i]['profit']:
                        self.to_update[i][2] = self.input_table[i]['profit']

                for i in range(len(self.to_update)):
                    profit = None
                    tp = None
                    sl = None
                    ticket = self.input_table[i]['ticket']

                    if self.to_update[i][0] is not None:
                        sl = self.to_update[i][0]

                    if self.to_update[i][1] is not None:
                        tp = self.to_update[i][1]

                    if self.to_update[i][2] is not None:
                        profit = self.to_update[i][2]

                    if profit is not None:
                        profit = QLabel(str(profit))
                        profit.setAlignment(Qt.AlignCenter)
                        self.display_table.setCellWidget(i, 5, profit)

                    if tp is not None:
                        if tp > 0.0:
                            tp = str(tp)
                        else:
                            tp = ' '
                        tp = TableItem(str(tp), ticket, 'tp')
                        tp.setTextAlignment(Qt.AlignCenter)
                        self.display_table.setItem(i, 4, tp)

                    if sl is not None:
                        if sl > 0.0:
                            sl = str(sl)
                        else:
                            sl = ' '
                        sl = TableItem(str(sl), ticket, 'sl')
                        sl.setTextAlignment(Qt.AlignCenter)
                        self.display_table.setItem(i, 3, sl)

            self.saved_table = self.input_table


class DataLoop(QThread):
    _signal = Signal(object)

    def __init__(self,parent):
        log.debug("DataLoop.__init__() ")
        super(DataLoop, self).__init__()
        self.symbol = None
        self.positions = []
        self.parent = parent

    def __del__(self):
        self.wait()

    def update_symbol(self, sym):

        print("update:" + str(sym))
        self.symbol = sym

    def run(self):
        log.debug('DataLoop.run()')
        while True:

            time.sleep(0.3)
            try:
                account = self.parent.broker.account_info()
                balance = account.balance
                profit = account.profit

                account_data = [balance, profit]

                pair_data = None

                if self.symbol is not None:

                    data = self.parent.broker.symbol_info(self.symbol)

                    try:
                        spread = data.spread
                        ask = data.ask
                        bid = data.bid
                        lot = data.trade_contract_size
                        min = data.volume_min
                        max = data.volume_max
                        step = data.volume_step
                        pair_data = [spread, ask, bid, lot, min, max, step]

                    except Exception as e:
                        log.critical(f'DataLoop.run(): {e}')

                self.get_positions()

                positions = self.positions
                data = [account_data, pair_data, positions]
                log.debug(f'DataLoop.run():  ==> emit data ==> {data}')
                self._signal.emit(data)


            except Exception as e:
                log.critical(f'DataLoop.run(): {e}')
                pass

    def get_positions(self):
        log.debug('DataLoop.get_position()')
        pos = self.parent.broker.positions_get()
        positions = []

        if pos is not None:
            for i in pos:

                if i.type == 1:
                    side = "LONG"
                elif i.type == 0:
                    side = "SHORT"
                else:
                    side = None

                p = {
                    "symbol": i.symbol,
                    "ticket": i.ticket,
                    "volume": i.volume,
                    "entry": i.price_open,
                    "sl": i.sl,
                    "tp": i.tp,
                    "profit": round(i.profit, 2),
                    "side": side
                }

                positions.append(p)

        if len(positions) == 0:
            positions = None

        self.positions = positions


class Trader(QMainWindow):
    def __init__(self, parent):
        log.debug('Trader.__init__()')
        super(Trader, self).__init__()
        self.parent = parent
        self.setWindowTitle("trderX")
        self.setWindowIcon(QIcon(':/icon.png'))

        loader = QUiLoader()

        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)

        # ui_file = QFile('form.ui')
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)

        ui_file.close()

        self.last_widget = None

        self.trade_price = 0

        self.positions_displayed = []
        self.positions_updated = []

        self.pair = None
        self.lot_size = 0
        self.lot = 0
        self.lot_min = None
        self.lot_max = None
        self.lot_step = None

        self.RR_usd = 0
        self.RR_percent = 0

        self.trade_amount = 0

        self.leverage = 0
        self.price = 0
        self.spread = 0

        self.r_usd = 0
        self.fee = 0
        self.deviation = 10

        self.positions = []

        self.table_manager = TableManager(self, self.ui.table)
        self.ui.table.itemChanged.connect(self.table_event)

        self.ui.b_long.clicked.connect(self.long)
        self.ui.b_short.clicked.connect(self.short)
        self.ui.b_web.clicked.connect(self.change_url)
        self.ui.web_path.returnPressed.connect(self.change_url)

        self.ui.b_price.clicked.connect(self.on_b_price)

        # -----------------------Build positions table ----------------

        self.build_positions_table()

        # ------------------- Connect to broker -------------------------
        log.debug('Trader.__init__() ==> connect to broker')
        self.broker = Broker()

        # --------------------- Get the pair list and types ----------------------------

        self.account = self.broker.account_info()

        log.info(f'Account Info: {self.account}')

        self.currency = self.account.currency

        if self.currency == 'USD':
            self.account_currency = "$"
        elif self.currency == 'EUR':
            self.account_currency = "€"

        log.debug('Trader.__init__() ==> get symbols from broker')

        self.data_thread = DataLoop(self)
        self.data_thread._signal.connect(self.update_data)

        self.pairs = self.account.pairs

        symbol_types = []

        for i in self.pairs:
            symbol_types.append(i['type'])

        symbol_types = list(set(symbol_types))
        symbol_types.sort()

        self.ui.combo_type.addItems(symbol_types)
        self.ui.combo_type.currentTextChanged.connect(self.set_pairs)
        self.set_pairs()

        # -------------------- Display the account Name -----------------------

        account = self.broker.account_info()
        account_details = str(account.server)
        font = self.ui.account.font()
        self.ui.account.setText(account_details)
        font.setPointSize(12)
        self.ui.account.setFont(font)

        # -----------------------  Display Tradingview -----------------------

        self.web = QWebEngineView()
        # self.web.load("https://fr.tradingview.com/chart/")
        print(self.web.load("https://www.google.fr"))

        self.web.page().settings().setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, True)
        self.web.page().settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.web.page().settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        self.web.page().settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        self.web.page().settings().setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        self.web.page().settings().setAttribute(QWebEngineSettings.AllowWindowActivationFromJavaScript, True)
        self.web.page().settings().setAttribute(QWebEngineSettings.JavascriptCanPaste, True)

        self.ui.view_layout.addWidget(self.web)

        # -----------------------  Google -----------------------

        self.web2 = QWebEngineView()
        self.web2.load("https://www.google.fr")

        self.web2.page().settings().setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, True)
        self.web2.page().settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        self.web2.page().settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        self.web2.page().settings().setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, True)
        self.web2.page().settings().setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        self.web2.page().settings().setAttribute(QWebEngineSettings.AllowWindowActivationFromJavaScript, True)
        self.web2.page().settings().setAttribute(QWebEngineSettings.JavascriptCanPaste, True)

        self.ui.view_layout_2.addWidget(self.web2)

        # ------------------------ Show ---------------------------------

        self.showMaximized()

        self.data_thread.start()

        self.ui.combo_pair.currentTextChanged.connect(self.set_pair)

        log.debug('Trader.__init__() ended')

    def set_pairs(self):
        print("MT5Trader.set_pair()")
        pair_type = self.ui.combo_type.currentText()
        selected_pair = []
        for i in self.pairs:
            if i['type'] == pair_type:
                selected_pair.append(i['pair'])

        self.ui.combo_pair.clear()
        self.ui.combo_pair.addItems(selected_pair)
        self.set_pair()

    def set_pair(self):
        log.debug('Trader.set_pair()')
        pair = self.ui.combo_pair.currentText()
        log.debug(f'Pair: {pair}')
        self.broker.symbol_select(pair)

        pair_data = self.broker.get_pair_data(pair)
        print(pair_data)
        self.lot_min = pair_data['volume_min']
        self.lot_max = pair_data['volume_max']
        self.lot_step = pair_data['volume_step']

        time.sleep(0.2)

        self.data_thread.update_symbol(pair)

        self.pair = pair

        self.leverage = self.broker.leverage(self.pair)

    def update_data(self, data):
        log.debug('Trader.update_data()')
        log.debug(f'Data: {str(data)}')
        # data = [[balance,profit],[spread,ask,bid,lot,min,max,step],positions]

        self.positions_updated = data[2]

        self.update_table()

        # ----------------------- Balance -----------------------

        float_balance = data[0][0]

        balance = str(data[0][0]).split(".")
        if len(balance[0]) > 3:
            balance = balance[0][-6:-3] + " " + balance[0][-3:] + "." + balance[1]
        else:
            balance = f'{balance[0]}.{balance[1]}'

        font = self.ui.balance.font()

        self.ui.balance.setText(balance + self.account_currency)

        font.setPointSize(12)
        self.ui.balance.setFont(font)

        self.ui.pnl.setText(str(data[0][1]) + self.account_currency)
        self.ui.pnl.setFont(font)

        # --------------- Computation of R in USD---------------

        try:

            r = float(self.ui.r.text())

            if r > 10.0:
                r = 0

            r_usd = float(float_balance) * r / 100
            r_usd = math.floor(r_usd)

            self.ui.risk_value.setText(str(r_usd) + self.account_currency)
            self.ui.risk_value.setFont(font)

        except:
            pass

        # ---------------- Update price and spread -------
        if not (data[1][1] is None or data[1][2] is None):
            ask = float(data[1][1])
            bid = float(data[1][2])
            price = round((ask + bid) / 2, 4)
            if self.ui.b_price.text() == "Market":
                self.trade_price = price
                self.ui.price_2.setText(str(self.trade_price))
                self.ui.price_2.setFont(font)
            else:
                self.trade_price = float(self.ui.price_2.text())

            self.ui.price.setText(str(price) + self.account_currency)
            self.ui.price.setFont(font)

            spread = abs(bid - ask)

            self.spread = spread
            if spread > 100:
                spread /= 10000

            spread = round(spread, 2)

            self.ui.spread.setText(str(spread))
            self.ui.spread.setFont(font)

        self.ui.TP.setFont(font)
        self.ui.SL.setFont(font)
        self.ui.r.setFont(font)
        self.ui.fee.setFont(font)

        # ----------------------- Lot size USD -------------------

        self.lot_size = self.broker.lot_size(self.pair)
        self.ui.lot_size.setText(str(round(self.lot_size)) + self.account_currency)
        self.ui.lot_size.setFont(font)

        # ------------------------- Max leverage --------------------
        leverage = self.leverage

        if leverage == 0.0:
            leverage = "--"
        else:
            leverage = "x" + str(leverage)

        self.ui.leverage.setText(leverage)
        self.ui.leverage.setFont(font)

        # ------------------ Computation of trade amount ---------------
        if self.ui.SL.text() != '':
            self.SL = float(self.ui.SL.text())
        else:
            self.SL = 0

        self.price = self.trade_price

        if self.ui.fee.text() != '':
            self.fee = float(self.ui.fee.text()) / 100
        else:
            self.fee = 0

        try:
            _float = float(self.ui.TP.text())

        except:
            _float = 0.0

        if self.ui.TP.text() != '' and _float != 0:

            self.TP = float(self.ui.TP.text())
        else:
            self.TP = 0.0

        if self.TP > 0 and self.SL > 0 and self.price > 0:
            risk = abs(self.price - self.SL)
            reward = abs(self.price - self.TP)
            RR = round(reward / risk, 2)

            r = float(self.ui.r.text()) / 100

            RR_usd = round(r * float_balance * RR, 2)
            RR_percent = round(r * RR * 100, 2)

        if (self.TP > self.price and self.SL > self.price) or (
                self.TP < self.price and self.SL < self.price) or self.TP == 0.0:
            # print(" RR = -")

            RR = "-"
            RR_usd = "-"
            RR_percent = "-"

        self.ui.rr_usd.setText(str(RR_usd) + self.account_currency)
        self.ui.rr_usd.setFont(font)
        self.ui.rr_percent.setText(str(RR_percent) + "%")
        self.ui.rr_percent.setFont(font)

        self.ui.RR.setText(str(RR))
        self.ui.RR.setFont(font)

        if self.SL > 0 and self.price > 0:

            delta = abs(price - self.SL)

            self.r_usd = r_usd - (self.spread / 2)

            percent = abs(delta / price) + self.fee

            self.trade_amount = math.floor(self.r_usd / percent)

            if self.trade_amount < 0:
                self.trade_amount = 0

        else:
            self.trade_amount = 0

        if self.trade_amount > 0:

            self.lot = math.floor(self.trade_amount / self.lot_size / self.lot_step) * self.lot_step

        else:
            self.lot = 0

        if self.lot < self.lot_min:
            self.lot = 0

        elif self.lot > self.lot_max:
            self.lot = self.lot_max

        if self.lot > 0:

            if not self.broker.check_order(self.pair, self.lot):
                self.lot = 0
                self.trade_amount = " Out of Margin"

            else:
                self.trade_amount = str(self.trade_amount)
                self.trade_amount += self.account_currency

        if type(self.trade_amount) != str():
            if self.trade_amount == 0:
                self.trade_amount = " - "

        self.ui.amount.setText(str(self.trade_amount))
        self.ui.amount.setFont(font)

        self.ui.lot.setText(str(self.lot) + " lot")
        self.ui.lot.setFont(font)

        # --------------- Enable LONG or SHORT ---------------------------

        if self.SL > self.price and (self.TP < self.price or self.TP == 0):
            self.ui.b_long.setEnabled(False)
            self.ui.b_short.setEnabled(True)

        elif self.SL < self.price and self.SL > 0.0 and (self.TP > self.price or self.TP == 0):
            self.ui.b_long.setEnabled(True)
            self.ui.b_short.setEnabled(False)

        else:
            self.ui.b_long.setEnabled(False)
            self.ui.b_short.setEnabled(False)

    def update_table(self):

        self.table_manager.load_positions(self.positions_updated)

    def build_positions_table(self):
        self.ui.table.setColumnCount(7)
        self.ui.table.setHorizontalHeaderLabels(["Symbol", "Volume", "Open", "SL", "TP", "Profit", "Close"])
        self.ui.table.setRowCount(0)
        self.ui.table.verticalHeader().hide()
        self.ui.table.setColumnWidth(0, 65)

        self.positions_displayed = []

    def long(self):
        print("long()")

        if type(self.lot) == float:

            lot = self.lot

            symbol = self.pair

            if self.SL != 0:
                sl = self.SL

                if self.TP != 0:
                    tp = self.TP

                else:
                    tp = None
            else:
                sl = None
                tp = None

            if self.ui.b_price.text() == "Market":
                self.broker.buy_market(symbol, lot, sl, tp)
            else:
                self.broker.buy_limit(symbol, lot, sl, tp)

    def short(self):
        print("short()")
        #
        # print(self.SL)
        # print(self.TP)

        if type(self.lot) == float:

            lot = self.lot

            symbol = self.pair

            if self.SL != 0:
                sl = self.SL

                if self.TP != 0:
                    tp = self.TP

                else:
                    tp = None
            else:
                sl = None
                tp = None

            if self.ui.b_price.text() == "Market":
                self.broker.sell_market(symbol, lot, sl, tp)
            else:
                self.broker.sell_limit(symbol, lot, sl, tp)

    def _clipboard(self):
        pass
        # print(QApplication.clipboard().text())

    def on_b_price(self):
        if self.ui.b_price.text() == "Market":
            self.ui.b_price.setText("Limit")
            self.ui.price_2.setEnabled(True)
        else:
            self.ui.b_price.setText("Market")
            self.ui.price_2.setEnabled(False)

    def change_url(self):
        path = self.ui.web_path.text()
        if path[0:4] != "http":
            if path[0:4] == "www.":
                path = "http://" + path
            else:
                if path[0] == '.':
                    path = path[1:]

                path = "http://www." + path

        self.web2.load(path)

    def check_signal(self):
        print("check signal from QWebEnginepage")

    def table_event(self, item):

        if isinstance(item, TableItem):

            try:
                value = float(item.text())

                for i in self.table_manager.input_table:
                    if i['ticket'] == item.ticket:
                        if i[item.cell_type] != value:
                            if item.cell_type == 'tp':
                                self.broker.edit_tp(item.ticket, value)

                            elif item.cell_type == 'sl':
                                self.broker.edit_sl(item.ticket, value)

                            self.table_manager.force_reload = True

            except:
                self.table_manager.force_reload = True
                print("wrong type input in position table")
                pass

    def last_focus(self, last, wid):

        if wid == self.ui.price_2 or wid == self.ui.TP or wid == self.ui.SL:
            print("last focus")
            self.last_widget = wid
            wid.clear()

    def handle_clipboard(self, clipboard):

        data = clipboard.text()

        try:
            data = float(data)

            self.last_widget.setText(str(data))

            clipboard.clear()

        except:
            pass


if __name__ == "__main__":
    app = QApplication([])
    app.setStyle("Fusion")

    # Now use a palette to switch to dark colors:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    widget = Trader(app)

    clipboard = app.clipboard()
    clipboard.dataChanged.connect(partial(widget.handle_clipboard, clipboard))

    app.focusChanged.connect(widget.last_focus)

    sys.exit(app.exec_())
