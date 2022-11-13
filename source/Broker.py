import os
import logging as log
if os.name == 'nt':
    import pymt5adapter as mt5
    # import MetaTrader5 as mt5


class AccountData():

    def __init__(self):
        # All the init data are for test purpose without connexion to broker
        self.currency ='USD'
        self.server = 'trderX'
        self.balance = 0.001
        self.profit = 0
        self.pairs = [
            {'pair': 'BTCUSD', 'type': 'Crypto', 'volume_min': 0.01, 'volume_max': 100000000, 'volume_step': 0.01},
            {'pair': 'ETH   USD', 'type': 'Crypto', 'volume_min': 0.01, 'volume_max': 100000000, 'volume_step': 0.01},
            {'pair': 'SOLUSD', 'type': 'Crypto', 'volume_min': 0.01, 'volume_max': 100000000, 'volume_step': 0.01},
            {'pair': 'GBPUSD', 'type': 'Forex', 'volume_min': 0.01, 'volume_max': 100000000, 'volume_step': 0.01},
            {'pair': 'EURUSD', 'type': 'Forex', 'volume_min': 0.01, 'volume_max': 100000000, 'volume_step': 0.01},
        ]

    def add_pair(self,pair, type, vol_min = 0.01, vol_max = 100000000, vol_step = 0.01):
        data = {
            'pair': pair,
            'type': type,
            'volume_min': vol_min,
            'volume_max': vol_max,
            'volume_step': vol_step
        }
        self.pairs.append(data)

    def __str__(self):
        return f'[ {self.currency}, {self.server},{self.balance} ]'


class PriceData():
    def __init__(self, parent):
        self.pair = None
        self.parent = parent
        self.spread = None
        self.bid = None
        self.ask = None
        self.trade_contract_size = 1
        self.volume_min = None
        self.volume_max = None
        self.volume_step = None

    def get_data(self,symbol):
        self.pair = symbol
        if self.parent.broker == 'mt5':
            data = self.parent.mt5_symbol_info(self.pair)
            self.spread = data.spread
            self.bid = data.bid
            self.ask = data.ask
            self.trade_contract_size = data.trade_contract_size
            self.volume_min = data.volume_min
            self.volume_max = data.volume_max
            self.volume_step = data.volume_step

    def __str__(self):

        return str([self.pair, self.spread, self. bid, self.ask, self.trade_contract_size, self. volume_min, self.volume_max, self.volume_step])

class Broker():

    def __init__(self, broker=None, api=None, key=None, account=None, password=None):

        self.broker = broker
        self.api = api
        self.key = key
        self.account = account
        self.password = password

        self.info = AccountData()
        self.price_data = PriceData(self)

        if broker == 'mt5':
            self.mt5_connect()

    def account_info(self):

        if self.broker == 'mt5':
            mt5_info =  mt5.account_info()
            symbols = mt5.symbols_get()


            self.info = AccountData()
            self.info.currency = mt5_info.currency
            self.info.server = mt5_info.server
            self.info.balance = mt5_info.balance
            self.info.profit = mt5_info.profit
            self.info.pairs = []

            for i in symbols:
                symbol_type = str(i.path).split("\\")[0]
                symbol = i.name
                pair_data = self.broker.symbol_info(pair)

                vol_min = pair_data.volume_min
                vol_max = pair_data.volume_max
                vol_step = pair_data.volume_step

                self.info.add_pair(symbol, symbol_type, vol_min, vol_max, vol_step )

            return self.info

        else :
            info = AccountData()
            return info

    def get_pair_data(self, symbol):
        for i in self.info.pairs:
            if i['pair'] == symbol:
                return i

    def symbols_get(self):

        if self.broker == 'mt5':
            return mt5.symbols_get()

    def symbol_select(self,symbol):
        if self.broker == 'mt5':
            return mt5.symbols_select(symbol,True)

    def symbol_info(self, symbol):
        self.price_data.get_data(symbol)
        return self.price_data

    def buy_market(self, symbol, lot, sl, tp):

        if self.broker == 'mt5':
            return self.mt5_buy_market(symbol, lot, sl, tp)

    def buy_limit(self, symbol, lot, sl, tp):

        if self.broker == 'mt5':
            return self.mt5_buy_limit(symbol, lot, sl, tp)

    def sell_market(self, symbol, lot, sl, tp):

        if self.broker == 'mt5':
            return self.mt5_sell_market(symbol, lot, sl, tp)

    def sell_limit(self, symbol, lot, sl, tp):

        if self.broker == 'mt5':
            return self.mt5_sell_limit(symbol, lot, sl, tp)

    def order_market(self, symbol, lot, _type="buy", sl=None, tp=None):
        if self.broker == 'mt5':
            return self.mt5_order_market( symbol, lot, _type="buy", sl=None, tp=None)

    def order_limit(self, symbol, lot, _type="buy", sl=None, tp=None):
        if self.broker == 'mt5':
            return self.mt5_order_limit( symbol, lot, _type="buy", sl=None, tp=None)

    def edit_tp(self, ticket, tp):
        if self.broker == 'mt5':
            return self.mt5_edit_tp(ticket, tp)

    def edit_sl(self, ticket, sl):
        if self.broker == 'mt5':
            return self.mt5_edit_sl(ticket, sl)

    def mt5_close_position(self, ticket):
        if self.broker == 'mt5':
            return self.mt5_close_position(ticket)

    def lot_size(self,symbol):

        if self.broker == 'mt5':
            return self.mt5_lot_size(symbol)

        else : return 1

    def leverage(self,symbol):

        if self.broker == 'mt5':
            return self.mt5_leverage(symbol)

    def positions_get(self):
        if self.broker == 'mt5':
            self.mt5_position_get()


    # -------------------------------------------- MT5 methods ------------------------------------------

    def mt5_connect(self):

        if not mt5.initialize():
            log.warning("Connexion a mt5 echouée")
            mt5.shutdown()

    def mt5_check_order(self, symbol, lot):
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

    def mt5_buy_market(self, symbol, lot, _sl=None, _tp=None):
        print("buy_market()")
        return self.mt5_order_market(symbol, lot, _type="buy", sl=_sl, tp=_tp)

    def mt5_sell_market(self, symbol, lot, _sl=None, _tp=None):
        print("sell_market()")
        return self.mt5_order_market(symbol, lot, _type="sell", sl=_sl, tp=_tp)

    def mt5_buy_limit(self, symbol, lot, _sl=None, _tp=None):
        print("buy limit")
        return self.mt5_order_limit(symbol, lot, self.trade_price, _type="buy", sl=_sl, tp=_tp)

    def mt5_sell_limit(self, symbol, lot, _sl=None, _tp=None):
        print("sell limit")
        return self.mt5_order_limit(symbol, lot, self.trade_price, _type="sell", sl=_sl, tp=_tp)

    def mt5_order_market(self, symbol, lot, _type="buy", sl=None, tp=None):
        print(
            "  ----------------------------------  order_market()  --------------------------------------------------------------------")

        if _type == "buy":
            _type = mt5.ORDER_TYPE_BUY

        elif _type == "sell":
            _type = mt5.ORDER_TYPE_SELL

        else:
            return False

        lot = float(lot)

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

    def mt5_order_limit(self, symbol, lot   , price, _type="buy", sl=None, tp=None):
        print("order_market()")

        if _type == "buy":
            _type = mt5.ORDER_TYPE_BUY_LIMIT

        elif _type == "sell":
            _type = mt5.ORDER_TYPE_SELL_LIMIT

        else:
            return False

        lot = float(lot)

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

    def mt5_edit_tp(self, ticket, tp):
        # print("edit_tp()")

        pos = mt5.positions_get(ticket=ticket)

        sl = pos[0].sl
        symbol = pos[0].symbol

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "tp": tp,
            "sl": sl,
        }

        # print(request)
        result = mt5.order_send(request)
        # print(result)
        return result

    def mt5_edit_sl(self, ticket, sl):
        # print("edit_tp()")

        pos = mt5.positions_get(ticket=ticket)

        tp = pos[0].tp
        symbol = pos[0].symbol

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": symbol,
            "position": ticket,
            "tp": tp,
            "sl": sl,
        }

        # print(request)
        result = mt5.order_send(request)
        # print(result)
        return result

    def mt5_close_position(self, ticket):
        print("close position " + str(ticket))

        pos = mt5.positions_get(ticket=ticket)
        symbol = pos[0].symbol

        print(mt5.Close(ticket))

        print(pos)
        #

        volume = pos[0].volume
        _type = pos[0].type

        if _type == mt5.ORDER_TYPE_BUY:
            print('sell')
            _type = mt5.ORDER_TYPE_SELL
        elif _type == mt5.ORDER_TYPE_SELL:
            print('buy')
            _type = mt5.ORDER_TYPE_BUY
        else:
            return None

        request = {
            # "action": mt5.TRADE_ACTION_CLOSE_BY,
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": volume,
            "type": _type,
            "type_filling": mt5.ORDER_FILLING_FOK

        }

        print(request)
        result = mt5.order_send(request)
        print(result)
        return result

    def mt5_lot_size(self, symbol):
        if symbol == "":
            return 0.0

        # print("_lot_size symbol")
        # print(symbol)
        lot = 1
        lot = float(lot)
        price = self.broker.symbol_info(symbol).ask

        if price == 0.0:
            return 0.0
        close = price * 2
        result = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, lot, price, close)

        return result

    def mt5_leverage(self, symbol):
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

    def mt5_position_get(self):
        return mt5.positions_get()



