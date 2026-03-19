# utils/position_manager.py
import MetaTrader5 as mt5

class PositionManager:
    def __init__(self):
        self.open_trades = [] # List to track our orders: {ticket, symbol, entry, sl, tp, type}

    def add_trade(self, ticket, symbol, entry, sl, tp, type):
        """Store a new trade to manage"""
        self.open_trades.append({
            'ticket': ticket,
            'symbol': symbol,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'type': type
        })

    def manage_trades(self):
        """
        Checks all open trades for Breakeven and Trailing logic.
        Returns list of closed trades with their P&L.
        """
        if not self.open_trades:
            return []

        to_remove = []
        closed_trades = []

        for trade in self.open_trades:
            ticket = trade['ticket']
            symbol = trade['symbol']
            entry = trade['entry']
            trade_type = trade['type'] # 1 (Buy) or -1 (Sell)
            original_sl = trade['sl']
            original_tp = trade['tp']

            # Get Current Price
            tick = mt5.symbol_info_tick(symbol)
            if not tick: continue
            current_price = tick.ask if trade_type == 1 else tick.bid
            
            # Calculate Pips Profit (Rough approximation for most pairs)
            # Pips = (Current - Entry) * 10000
            pips_diff = (current_price - entry) * 10000

            # --- LOGIC 1: BREAKEVEN (+10 pips) ---
            if pips_diff > 10:
                # Check if SL is already at Breakeven
                # If Buy: SL should be >= Entry. If Sell: SL should be <= Entry.
                should_move_breakeven = False
                if trade_type == 1: # Buy
                    if original_sl < entry: should_move_breakeven = True
                else: # Sell
                    if original_sl > entry: should_move_breakeven = True

                if should_move_breakeven:
                    print(f"🛡️ [Ticket {ticket}] Breakeven Triggered. Moving SL to Entry.")
                    # Modify SL to Entry (plus a tiny buffer if desired, here exact entry)
                    request = {
                        "action": mt5.TRADE_ACTION_MODIFY,
                        "order": ticket,
                        "sl": entry, # Move SL to Entry Price
                        "tp": original_tp
                    }
                    # In Simulation mode (Paper Trading), mt5.order_send will fail on fake tickets.
                    # That's okay, we just want to see the LOGIC printed.
                    mt5.order_send(request) 
                    trade['sl'] = entry # Update local record

            # --- LOGIC 2: TRAILING STOP (+30 pips) ---
            if pips_diff > 30:
                # Trail SL by 5 pips "behind" current price
                trail_distance = 0.0005 # 5 pips
                new_sl = (current_price - trail_distance) if trade_type == 1 else (current_price + trail_distance)

                # Check if we need to update
                # Avoid spamming updates if close
                if abs(new_sl - trade['sl']) > 0.0001:
                    print(f"📈 [Ticket {ticket}] Trailing Triggered. New SL: {new_sl:.5f}")
                    request = {
                        "action": mt5.TRADE_ACTION_MODIFY,
                        "order": ticket,
                        "sl": new_sl,
                        "tp": original_tp
                    }
                    mt5.order_send(request)
                    trade['sl'] = new_sl

            # --- LOGIC 3: CHECK IF TRADE IS CLOSED ---
            # Query position status
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                # Trade was closed - get the deal history to calculate P&L
                from datetime import datetime, timedelta

                # Get deals for this ticket
                deals = mt5.history_deals_get(ticket=ticket)

                exit_price = current_price
                profit = 0.0

                if deals and len(deals) > 0:
                    # Last deal is the closing deal
                    closing_deal = deals[-1]
                    profit = closing_deal.profit
                    exit_price = closing_deal.price
                else:
                    # Estimate profit if deal history not available
                    profit = (exit_price - entry) * 10000 if trade_type == 1 else (entry - exit_price) * 10000

                print(f"✅ [Ticket {ticket}] Trade Closed. Profit: {profit:.2f}")

                # Record closed trade
                closed_trade = {
                    'ticket': ticket,
                    'symbol': symbol,
                    'entry': entry,
                    'exit': exit_price,
                    'signal': trade_type,
                    'profit': profit,
                    'time': datetime.now()
                }
                closed_trades.append(closed_trade)
                to_remove.append(trade)

        # Remove closed trades from tracking
        for trade in to_remove:
            self.open_trades.remove(trade)

        return closed_trades