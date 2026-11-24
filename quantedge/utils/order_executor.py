# utils/order_executor.py
import MetaTrader5 as mt5

class OrderExecutor:
    def __init__(self):
        # IMPORTANT: We DO NOT initialize MT5 here.
        # MT5Connector in bot.py handles initialization.
        # If we initialize it here, it crashes the connection pipe.
        pass

    def execute_order(self, symbol, order_type, lot_size, sl_price, tp_price, deviation=20):
        """
        Open a market order. `order_type` accepts 1/-1 or 'buy'/'sell'.

        Returns a dict: {'success': bool, 'ticket', 'fill_price',
        'requested_price', 'error'} so callers can journal the trade and
        compare requested vs actual fills for slippage tracking.
        """
        if order_type in (1, "buy", "BUY", "Buy"):
            signal = 1
            order_kind = mt5.ORDER_TYPE_BUY
        elif order_type in (-1, "sell", "SELL", "Sell"):
            signal = -1
            order_kind = mt5.ORDER_TYPE_SELL
        else:
            return {"success": False, "error": f"Invalid order_type: {order_type}"}

        if not lot_size or lot_size <= 0:
            return {"success": False, "error": f"Invalid lot size: {lot_size}"}

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "error": f"No tick data for {symbol}"}

        price = tick.ask if signal == 1 else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_kind,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": deviation,
            "magic": 234000,
            "comment": "QuantEdge",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "error": "order_send returned None (terminal connection lost?)"}

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return {
                "success": False,
                "error": f"Order rejected: retcode {result.retcode} - {getattr(result, 'comment', '')}",
            }

        fill_price = getattr(result, "price", None) or price
        return {
            "success": True,
            "ticket": result.order,
            "fill_price": float(fill_price),
            "requested_price": float(price),
        }

    def send_order(self, symbol, signal, lot, sl, tp):
        """Backward-compatible wrapper returning just the ticket (or False)."""
        result = self.execute_order(symbol, 1 if signal == 1 else -1, lot, sl, tp)
        if not result["success"]:
            print(f"Order Failed: {result['error']}")
            return False
        return result["ticket"]

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
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error = "order_send returned None" if result is None else f"retcode {result.retcode}"
            print(f"Order Modify Failed: {error}")
            return False
        return True
