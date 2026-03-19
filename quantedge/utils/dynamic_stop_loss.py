# utils/dynamic_stop_loss.py - Enhanced Stop Loss Management
import numpy as np
from typing import Dict

class DynamicStopLoss:
    """
    Advanced Stop Loss Management System.
    Features:
    - ATR-based dynamic stops
    - Volatility-adjusted stops
    - Time-based stops (cut losers early)
    - Parabolic SAR integration
    """
    def __init__(self, base_atr_multiplier=1.5):
        self.base_atr_multiplier = base_atr_multiplier

    def calculate_atr_stop(self, entry_price: float, atr: float, direction: int) -> float:
        """
        Basic ATR stop loss.
        direction: 1 (buy) or -1 (sell)
        """
        if direction == 1:
            return entry_price - (atr * self.base_atr_multiplier)
        else:
            return entry_price + (atr * self.base_atr_multiplier)

    def calculate_volatility_adjusted_stop(self, entry_price: float, atr: float,
                                           current_vol: float, target_vol: float,
                                           direction: int) -> float:
        """
        Adjust stop loss based on current volatility vs normal volatility.

        Logic:
        - High volatility → Wider stop
        - Low volatility → Tighter stop
        """
        vol_ratio = current_vol / target_vol if target_vol > 0 else 1.0

        # Clamp ratio between 0.5 and 2.0
        vol_ratio = max(0.5, min(2.0, vol_ratio))

        adjusted_multiplier = self.base_atr_multiplier * vol_ratio

        if direction == 1:
            return entry_price - (atr * adjusted_multiplier)
        else:
            return entry_price + (atr * adjusted_multiplier)

    def calculate_time_based_stop(self, entry_price: float, atr: float,
                                   bars_held: int, direction: int) -> float:
        """
        Tighten stop loss the longer we hold the trade.

        Logic:
        - 0-5 bars: Normal stop (1.5 ATR)
        - 5-10 bars: Tighter (1.2 ATR)
        - 10+ bars: Very tight (1.0 ATR) - "Cut losers early"
        """
        if bars_held <= 5:
            multiplier = self.base_atr_multiplier
        elif bars_held <= 10:
            multiplier = self.base_atr_multiplier * 0.8
        else:
            multiplier = self.base_atr_multiplier * 0.65

        if direction == 1:
            return entry_price - (atr * multiplier)
        else:
            return entry_price + (atr * multiplier)

    def calculate_chandelier_stop(self, df, period=22, multiplier=3.0) -> float:
        """
        Chandelier Stop: Uses highest high (for long) or lowest low (for short).
        More dynamic than fixed ATR.
        """
        if len(df) < period:
            return 0

        highest_high = df['high'].iloc[-period:].max()
        lowest_low = df['low'].iloc[-period:].min()
        atr = df['atr_14'].iloc[-1] if 'atr_14' in df.columns else df['close'].iloc[-1] * 0.02

        long_stop = highest_high - (atr * multiplier)
        short_stop = lowest_low + (atr * multiplier)

        return {'long_stop': long_stop, 'short_stop': short_stop}

    def calculate_parabolic_sar(self, df, acceleration=0.02, maximum=0.2):
        """
        Parabolic SAR: Trailing stop that accelerates as trend continues.
        """
        if len(df) < 5:
            return None

        high = df['high'].values
        low = df['low'].values
        close = df['close'].values

        # Simplified SAR calculation (last value)
        trend = 1 if close[-1] > close[-5] else -1

        if trend == 1:
            ep = max(high[-5:])  # Extreme point
            sar = min(low[-5:])
        else:
            ep = min(low[-5:])
            sar = max(high[-5:])

        return sar

    def get_optimal_stop(self, entry_price: float, atr: float, current_vol: float,
                        target_vol: float, direction: int, bars_held: int,
                        df=None, strategy='hybrid') -> Dict:
        """
        Main function: Calculate optimal stop loss using multiple methods.

        strategy options:
        - 'atr': Basic ATR stop
        - 'volatility': Volatility-adjusted stop
        - 'time': Time-based stop
        - 'chandelier': Chandelier stop
        - 'hybrid': Combine multiple methods (BEST)
        """
        results = {}

        # Calculate all stop types
        atr_stop = self.calculate_atr_stop(entry_price, atr, direction)
        vol_stop = self.calculate_volatility_adjusted_stop(entry_price, atr, current_vol, target_vol, direction)
        time_stop = self.calculate_time_based_stop(entry_price, atr, bars_held, direction)

        results['atr_stop'] = atr_stop
        results['volatility_stop'] = vol_stop
        results['time_stop'] = time_stop

        if df is not None and len(df) >= 22:
            chandelier = self.calculate_chandelier_stop(df)
            results['chandelier_stop'] = chandelier['long_stop'] if direction == 1 else chandelier['short_stop']

            sar = self.calculate_parabolic_sar(df)
            if sar is not None:
                results['sar_stop'] = sar

        # Select strategy
        if strategy == 'atr':
            final_stop = atr_stop
        elif strategy == 'volatility':
            final_stop = vol_stop
        elif strategy == 'time':
            final_stop = time_stop
        elif strategy == 'chandelier' and 'chandelier_stop' in results:
            final_stop = results['chandelier_stop']
        elif strategy == 'hybrid':
            # Hybrid: Use the TIGHTEST stop (most conservative)
            stops = [atr_stop, vol_stop, time_stop]
            if 'chandelier_stop' in results:
                stops.append(results['chandelier_stop'])

            if direction == 1:
                # For long, tightest = highest stop
                final_stop = max(stops)
            else:
                # For short, tightest = lowest stop
                final_stop = min(stops)
        else:
            final_stop = atr_stop

        results['final_stop'] = final_stop
        results['strategy_used'] = strategy

        return results

    def calculate_risk_amount(self, entry_price: float, stop_loss: float,
                             lot_size: float, point_value: float) -> float:
        """
        Calculate dollar risk for a trade.
        """
        price_diff = abs(entry_price - stop_loss)
        risk = price_diff * lot_size * point_value
        return risk

    def should_tighten_stop(self, entry_price: float, current_price: float,
                           current_stop: float, direction: int) -> Dict:
        """
        Determine if we should tighten stop loss (move to breakeven or trail).

        Returns: {'should_tighten': bool, 'new_stop': float, 'reason': str}
        """
        pips_profit = (current_price - entry_price) * 10000 if direction == 1 else (entry_price - current_price) * 10000

        # Rule 1: Move to breakeven at +10 pips
        if pips_profit >= 10:
            if direction == 1 and current_stop < entry_price:
                return {
                    'should_tighten': True,
                    'new_stop': entry_price,
                    'reason': 'Moving to breakeven (+10 pips)'
                }
            elif direction == -1 and current_stop > entry_price:
                return {
                    'should_tighten': True,
                    'new_stop': entry_price,
                    'reason': 'Moving to breakeven (+10 pips)'
                }

        # Rule 2: Trail at +30 pips
        if pips_profit >= 30:
            trail_distance = 0.0005  # 5 pips
            new_stop = (current_price - trail_distance) if direction == 1 else (current_price + trail_distance)

            return {
                'should_tighten': True,
                'new_stop': new_stop,
                'reason': 'Trailing stop activated (+30 pips)'
            }

        return {'should_tighten': False, 'new_stop': current_stop, 'reason': 'No tightening needed'}
