
import os, time
from pathlib import Path
import sys
import math

from functools import partial

import MetaTrader5 as mt5
from PySide2.QtWidgets import QApplication, QWidget, QGraphicsView, QGraphicsItem, QGraphicsScene, QDesktopWidget,QGridLayout, QLineEdit, QLabel, QTableWidgetItem, QPushButton, QStyle
from PySide2.QtCore import QFile, QThread, QObject, Signal, Qt, QLineF, QPoint, QRect

from PySide2.QtUiTools import QUiLoader

from PySide2.QtWebEngineWidgets import *


class DataLoop(QThread):
    _signal = Signal(object)
    def __init__(self):
        super(DataLoop, self).__init__()
        self.symbol = None
        self.positions = []

    def __del__(self):
        self.wait()

    def update_symbol(self,sym):

        print("update:" + str(sym))
        self.symbol = sym

    def run(self):

        while True:

            time.sleep(0.3)

            account = mt5.account_info()
            balance = account.balance
            profit = account.profit

            account_data =[balance, profit]

            pair_data = None

            if self.symbol is not None:

                data = mt5.symbol_info(self.symbol)
                # print(data)
                try:
                    spread = data.spread
                    ask = data.ask
                    bid = data.bid
                    lot = data.trade_contract_size
                    min = data.volume_min
                    max = data.volume_max
                    step = data.volume_step

                    pair_data = [spread, ask, bid, lot, min, max, step]

                except:
                    pass

            self.get_positions()

            positions = self.positions
            self._signal.emit([account_data,pair_data,positions])
            # print("end of loop")

    def get_positions(self):

        pos = mt5.positions_get()
        positions = []

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
                "profit": round(i.profit,2),
                "side": side
            }

            positions.append(p)

        self.positions = positions

class Trader(QWidget):
    def __init__(self,parent):
        super(Trader, self).__init__()
        self.parent = parent
        self.setWindowTitle("TraderX")
        loader = QUiLoader()
        path = os.fspath(Path(__file__).resolve().parent / "form.ui")
        ui_file = QFile(path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)

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

        ui_file.close()

        self.ui.b_long.clicked.connect(self.long)
        self.ui.b_short.clicked.connect(self.short)

        self.ui.b_price.clicked.connect(self.on_b_price)

        # -----------------------Build positions table ----------------

        self.build_positions_table()

        # ------------------- Connect to MT5 -------------------------

        if not mt5.initialize():
            print("Connexion a mt5 echouée")
            mt5.shutdown()

        # --------------------- Get the pair list and types ----------------------------

        account = mt5.account_info()

        print(account)

        self.currency = account.currency

        if self.currency == 'USD':
            self.account_currency = "$"
        elif self.currency == 'EUR':
            self.account_currency = "€"


        symbols = mt5.symbols_get()

        self.data_thread = DataLoop()
        self.data_thread._signal.connect(self.update_data)


        self.pairs = []

        for i in symbols:
            symbol_type = str(i.path).split("\\")[0]
            self.pairs.append([i.name,symbol_type])

        symbol_types = []

        for i in self.pairs:
            symbol_types.append(i[1])

        symbol_types = list(set(symbol_types))
        symbol_types.sort()

        self.ui.combo_type.addItems(symbol_types)
        self.ui.combo_type.currentTextChanged.connect(self.set_pairs)
        self.set_pairs()


        # -------------------- Display the account Name -----------------------

        account = mt5.account_info()
        account_details = str(account.server)
        font = self.ui.account.font()
        self.ui.account.setText(account_details)
        font.setPointSize(12)
        self.ui.account.setFont(font)

        # -----------------------  Display Tradingview -----------------------

        self.web = QWebEngineView()
        self.web.load("https://fr.tradingview.com/chart/")

        self.ui.view_layout.addWidget(self.web)

        self.parent.clipboard().dataChanged.connect(self._clipboard)



        # ------------------------ Show ---------------------------------

        self.showMaximized()


        self.data_thread.start()


        self.ui.combo_pair.currentTextChanged.connect(self.set_pair)

    def set_pairs(self):
        print("MT5Trader.set_pair()")
        pair_type = self.ui.combo_type.currentText()
        selected_pair = []
        for i in self.pairs:
            if i[1] == pair_type:
                selected_pair.append(i[0])


        self.ui.combo_pair.clear()
        self.ui.combo_pair.addItems(selected_pair)
        self.set_pair()

    def set_pair(self):

        pair = self.ui.combo_pair.currentText()

        mt5.symbol_select(pair, True)

        pair_data = mt5.symbol_info(pair)

        # print(pair_data)

        self.lot_min = pair_data.volume_min
        self.lot_max = pair_data.volume_max
        self.lot_step = pair_data.volume_step

        time.sleep(0.2)

        self.data_thread.update_symbol(pair)

        self.pair = pair

        self.leverage = self._leverage(self.pair)

    def update_data(self,data):
        # data = [[balance,profit],[spread,ask,bid,lot,min,max,step],positions]

        self.positions_updated = data[2]

        self.update_table()

        # ----------------------- Balance -----------------------
        float_balance = data[0][0]

        balance = str(data[0][0]).split(".")

        balance =  balance[0][-6:-3] + " " + balance[0][-3:] + "." + balance[1]

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

            r_usd = float(float_balance)*r/100
            r_usd=math.floor(r_usd)

            self.ui.risk_value.setText(str(r_usd) + self.account_currency)
            self.ui.risk_value.setFont(font)

        except:
            pass


        # ---------------- Update price and spread -------

        ask = float( data[1][1])
        bid = float(data[1][2])
        price = round((ask+bid) /2,4)
        if self.ui.b_price.text() == "Market":
            self.trade_price = price
            self.ui.price_2.setText(str(self.trade_price))
            self.ui.price_2.setFont(font)
        else:
            self.trade_price = float(self.ui.price_2.text())



        self.ui.price.setText(str(price) + self.account_currency)
        self.ui.price.setFont(font)

        spread = abs(bid-ask)

        self.spread = spread
        if spread > 100 :
            spread /= 10000

        spread = round(spread,2)

        self.ui.spread.setText(str(spread))
        self.ui.spread.setFont(font)

        self.ui.TP.setFont(font)
        self.ui.SL.setFont(font)
        self.ui.r.setFont(font)
        self.ui.fee.setFont(font)

        # ----------------------- Lot size USD -------------------

        self.lot_size = self._lot_size(self.pair)
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
            self.fee = float(self.ui.fee.text())/100
        else:
            self.fee = 0

        try:
            _int = int(self.ui.TP.text())

        except:
            _int = 0


        if self.ui.TP.text() != '' and  _int != 0:

            self.TP = float(self.ui.TP.text())
        else:
            self.TP = 0.0


        if self.TP > 0 and self.SL  > 0 and self.price > 0:

            risk = abs(self.price-self.SL)
            reward = abs(self.price-self.TP)
            RR = round(reward/risk,2)

            r = float(self.ui.r.text())/100

            RR_usd = round(r * float_balance * RR,2)
            RR_percent = round(r * RR * 100,2)



        if (self.TP > self.price and self.SL > self.price) or (self.TP < self.price and self.SL < self.price) or self.TP == 0.0:
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


        if self.SL > 0 and self.price >0:

            delta = abs(price-self.SL)

            self.r_usd = r_usd - (self.spread/2)

            percent = abs(delta/price) + self.fee

            self.trade_amount = math.floor(self.r_usd/percent)

            if self.trade_amount < 0:
                self.trade_amount = 0

        else:
            self.trade_amount = 0


        if self.trade_amount > 0:

            self.lot = math.floor(self.trade_amount / self.lot_size / self.lot_step)*self.lot_step

        else:
            self.lot = 0

        if self.lot < self. lot_min:
            self.lot = 0

        elif self.lot > self.lot_max:
            self.lot = self.lot_max

        if self.lot > 0:

            if not self.mt5_check_order(self.pair,self.lot):
                self.lot = 0
                self.trade_amount = " Out of Margin"

            else:
                self.trade_amount = str(self.trade_amount)
                self.trade_amount += self.account_currency

        if type(self.trade_amount) != str():
            if self.trade_amount == 0:
                self.trade_amount = " - "

        self.ui.amount.setText(str(self.trade_amount) )
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

    def mt5_check_order(self,symbol, lot):
        # print("Check order for: " + str(symbol) + "  " + str(lot) + " lot")

        lot = float(lot)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY,
            "type_filling": mt5.ORDER_FILLING_FOK
        }

        result = mt5.order_check(request)

        # print(result)

        if result.margin_free > 0.01:
            return True
        else:
            return False

    def mt5_buy_market(self,symbol,lot,_sl=None,_tp=None):
        print("buy_market()")
        return self.mt5_order_market(symbol, lot, _type="buy", sl=_sl, tp=_tp)

    def mt5_sell_market(self,symbol,lot,_sl=None,_tp=None):
        print("sell_market()")
        return self.mt5_order_market(symbol, lot, _type="sell", sl=_sl, tp=_tp)

    def mt5_buy_limit(self,symbol,lot,_sl=None,_tp=None):
        print("buy limit")
        return self.mt5_order_limit(symbol, lot,self.trade_price, _type="buy", sl=_sl, tp=_tp)

    def mt5_sell_limit(self, symbol, lot, _sl=None, _tp=None):
        print("sell limit")
        return self.mt5_order_limit(symbol, lot, self.trade_price, _type="sell", sl=_sl, tp=_tp)


    def mt5_order_market(self, symbol, lot, _type="buy", sl=None, tp=None):
        # print("order_market()")

        if _type == "buy":
            _type = mt5.ORDER_TYPE_BUY

        elif _type == "sell":
            _type = mt5.ORDER_TYPE_SELL

        else:
            return False

        lot= float(lot)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": _type,
            "type_filling": mt5.ORDER_FILLING_FOK
        }

        if sl is not None:
            sl = float(sl)
            request["sl"] = sl

            if tp is not None:
                tp = float(tp)
                request["tp"] = tp

        print(request)

        result = mt5.order_send(request)
        print(result)
        return result

    def mt5_order_limit(self, symbol, lot, price,  _type="buy", sl=None, tp=None):
        print("order_market()")

        if _type == "buy":
            _type = mt5.ORDER_TYPE_BUY_LIMIT

        elif _type == "sell":
            _type = mt5.ORDER_TYPE_SELL_LIMIT

        else:
            return False

        lot= float(lot)

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": _type,
            "price": price,
            "type_filling": mt5.ORDER_FILLING_FOK
        }

        if sl is not None:
            sl = float(sl)
            request["sl"] = sl

            if tp is not None:
                tp = float(tp)
                request["tp"] = tp

        print(request)

        result = mt5.order_send(request)
        print(result)
        return result

    def mt5_close_position(self, ticket):
        ticket = str(ticket)
        # print("close " + str(ticket))

    def deprecated_update_table(self):

        # print(self.positions_updated)

        self.positions = self.positions_updated

        lines = len(self.positions)
        self.ui.table.setHorizontalHeaderLabels(["Symbol","Volume","Open","SL","TP","Profit","Close"])
        self.ui.table.setColumnCount(7)
        self.ui.table.setRowCount(lines)

        self.ui.table.verticalHeader().hide()

        self.ui.table.setColumnWidth(0,50)

        index = 0

        # p = {
        #     "symbol": i.symbol,
        #     "ticket": i.ticket,
        #     "volume": i.volume,
        #     "entry": i.price_open,
        #     "sl": i.sl,
        #     "tp": i.tp,
        #     "profit": i.profit
        # }
        #
        for i in self.positions:

            symbol = QLabel(str(i["symbol"]))
            symbol.setAlignment(Qt.AlignCenter)

            vol = str(i["volume"])
            if i["side"] == "LONG":
                vol = "+" + vol

            elif i["side"] == "SHORT":
                vol = "-" + vol

            volume = QLabel(vol)
            volume.setAlignment(Qt.AlignCenter)

            entry = QLabel(str(round(i["entry"],4)))
            entry.setAlignment(Qt.AlignCenter)

            profit = QLabel(str(i["profit"]))
            profit.setAlignment(Qt.AlignCenter)

            tp = QTableWidgetItem(str(i["tp"]))
            tp.setTextAlignment(Qt.AlignCenter)

            sl = QTableWidgetItem(str(i["sl"]))
            sl.setTextAlignment(Qt.AlignCenter)

            self.ui.table.setCellWidget(index,0,symbol)
            self.ui.table.setCellWidget(index, 1, volume)
            self.ui.table.setCellWidget(index, 2, entry)
            self.ui.table.setCellWidget(index, 5, profit)

            if i["sl"] > 0.0:
                self.ui.table.setItem(index, 3, sl)

            if i["tp"] > 0.0:
                self.ui.table.setItem(index, 4, tp)

            close_button = QPushButton()
            pixmapi = getattr(QStyle, 'SP_TitleBarCloseButton')
            icon = self.style().standardIcon(pixmapi)
            close_button.setIcon(icon)
            close_button.clicked.connect(partial(self.mt5_close_position, i["ticket"]))

            self.ui.table.setCellWidget(index, 6, close_button)



            index +=1

    def update_table(self):
        self.deprecated_update_table()
        pass

    def build_positions_table(self):
        self.ui.table.setColumnCount(7)
        self.ui.table.setHorizontalHeaderLabels(["Symbol", "Volume", "Open", "SL", "TP", "Profit", "Close"])
        self.ui.table.setRowCount(0)
        self.ui.table.verticalHeader().hide()
        self.ui.table.setColumnWidth(0, 65)

        self.positions_displayed = []

        # --------------

        # index = 0
        #
        # symbol = QLabel("BTCUSD")
        # symbol.setAlignment(Qt.AlignCenter)
        #
        # vol = "1.3"
        #
        # volume = QLabel(vol)
        # volume.setAlignment(Qt.AlignCenter)
        #
        # entry = QLabel("27542.5")
        # entry.setAlignment(Qt.AlignCenter)
        #
        # profit = QLabel("-25.3")
        # profit.setAlignment(Qt.AlignCenter)
        #
        # tp = QTableWidgetItem("35400")
        # tp.setTextAlignment(Qt.AlignCenter)
        #
        # sl = QTableWidgetItem("22350")
        # sl.setTextAlignment(Qt.AlignCenter)
        #
        # self.ui.table.setCellWidget(index, 0, symbol)
        # self.ui.table.setCellWidget(index, 1, volume)
        # self.ui.table.setCellWidget(index, 2, entry)
        # self.ui.table.setCellWidget(index, 5, profit)
        #
        # self.ui.table.setItem(index, 3, sl)
        #
        #
        # self.ui.table.setItem(index, 4, tp)
        #
        # close_button = QPushButton()
        # pixmapi = getattr(QStyle, 'SP_TitleBarCloseButton')
        # icon = self.style().standardIcon(pixmapi)
        # close_button.setIcon(icon)
        # close_button.clicked.connect(partial(self.mt5_close_position, 123456))
        #
        # self.ui.table.setCellWidget(index, 6, close_button)

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
                self.mt5_buy_market(symbol, lot, sl, tp)
            else:
                self.mt5_buy_limit(symbol, lot, sl, tp)

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
                self.mt5_sell_market(symbol, lot, sl, tp)
            else:
                self.mt5_sell_limit(symbol, lot, sl, tp)

    def _lot_size(self,symbol):
        if symbol == "":
            return 0.0

        # print("_lot_size symbol")
        # print(symbol)
        lot = 1
        lot = float(lot)
        price = mt5.symbol_info(symbol).ask

        if price == 0.0:
            return 0.0
        close = price * 2
        result = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, lot, price, close)

        return result

    def _leverage(self,symbol):
        if symbol == "":
            return 0

        # print("leverage: " + str(symbol))
        # print(type(symbol))
        lot_size = self._lot_size(symbol)

        price = mt5.symbol_info(symbol).ask
        if price == 0.0 or lot_size == 0.0:
            return 0
        margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol, 1.0, price)
        leverage = lot_size / margin
        # print(symbol)
        # print("Leverage: " + str(leverage))
        leverage = round(leverage)

        # print("Leverage: " + str(leverage))
        # print("---------------")

        return leverage

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



if __name__ == "__main__":
    app = QApplication([])
    widget = Trader(app)

    sys.exit(app.exec_())
