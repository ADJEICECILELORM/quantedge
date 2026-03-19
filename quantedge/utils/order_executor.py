# utils/order_executor.py
import MetaTrader5 as mt5

class OrderExecutor:
    def __init__(self):
        # IMPORTANT: We DO NOT initialize MT5 here.
        # MT5Connector in bot.py handles initialization.
        # If we initialize it here, it crashes the connection pipe.
        pass

    def send_order(self, symbol, signal, lot, sl, tp):
        """Opens a new trade"""
        if lot <= 0:
            return False

        symbol_info = mt5.symbol_info_tick(symbol)
        if symbol_info is None:
            print(f"Symbol {symbol} not found")
            return False
            
        price = symbol_info.ask if signal == 1 else symbol_info.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 234000,
            "comment": "QuantEdge V3.0",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Order Failed: {result.retcode} - {result.comment}")
            return False
        else:
            print(f"Order Placed: {signal} {lot} lots at {price}")
            # Return ticket so we can modify it later (Trailing Stop)
            return result.order

    def modify_order(self, ticket, new_sl, new_tp):
        """Modifies an existing trade's SL/TP"""
        request = {
            "action": mt5.TRADE_ACTION_MODIFY,
            "order": ticket,
            "sl": new_sl,
            "tp": new_tp,
            "comment": "QuantEdge Trailing"
        }
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Order Modify Failed: {result.retcode} - {result.comment}")
            return False
        return True