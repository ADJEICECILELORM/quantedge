# utils/correlation_filter.py - Correlation Filter
import pandas as pd
import numpy as np
from typing import Dict, List

class CorrelationFilter:
    """
    Prevents trading highly correlated pairs simultaneously.
    Reduces portfolio risk and overexposure.
    """
    def __init__(self, max_correlation=0.7, lookback=100):
        self.max_correlation = max_correlation
        self.lookback = lookback
        self.correlation_matrix = {}
        self.open_positions = {}  # {symbol: direction}

    def calculate_correlation(self, df1: pd.DataFrame, df2: pd.DataFrame) -> float:
        """
        Calculate correlation between two price series.
        """
        if df1 is None or df2 is None:
            return 0

        if len(df1) < self.lookback or len(df2) < self.lookback:
            return 0

        # Use last N bars
        returns1 = df1['close'].pct_change().iloc[-self.lookback:]
        returns2 = df2['close'].pct_change().iloc[-self.lookback:]

        # Calculate correlation
        correlation = returns1.corr(returns2)

        return correlation if not np.isnan(correlation) else 0

    def update_correlation_matrix(self, mt5_connector, symbols: List[str]):
        """
        Update correlation matrix for all symbol pairs.
        """
        self.correlation_matrix = {}

        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                df1 = mt5_connector.get_latest_bars(sym1, 5, count=self.lookback)
                df2 = mt5_connector.get_latest_bars(sym2, 5, count=self.lookback)

                corr = self.calculate_correlation(df1, df2)
                self.correlation_matrix[f"{sym1}_{sym2}"] = corr

    def add_position(self, symbol: str, direction: int):
        """Record an open position"""
        self.open_positions[symbol] = direction

    def remove_position(self, symbol: str):
        """Remove a closed position"""
        if symbol in self.open_positions:
            del self.open_positions[symbol]

    def is_correlated_with_open_positions(self, symbol: str) -> Dict:
        """
        Check if symbol is highly correlated with any open position.

        Returns:
        - allowed: bool
        - reason: str
        - correlated_with: list of symbols
        - max_correlation: float
        """
        if not self.open_positions:
            return {'allowed': True, 'reason': 'No open positions', 'correlated_with': [], 'max_correlation': 0}

        correlated_symbols = []
        max_corr = 0

        for open_symbol in self.open_positions.keys():
            # Get correlation
            key1 = f"{symbol}_{open_symbol}"
            key2 = f"{open_symbol}_{symbol}"

            corr = self.correlation_matrix.get(key1, self.correlation_matrix.get(key2, 0))

            if abs(corr) > self.max_correlation:
                correlated_symbols.append(open_symbol)
                max_corr = max(max_corr, abs(corr))

        if correlated_symbols:
            return {
                'allowed': False,
                'reason': f'High correlation with {correlated_symbols}',
                'correlated_with': correlated_symbols,
                'max_correlation': max_corr
            }

        return {'allowed': True, 'reason': 'No correlation conflicts', 'correlated_with': [], 'max_correlation': max_corr}

    def get_correlation_report(self) -> Dict:
        """
        Get full correlation report.
        """
        if not self.correlation_matrix:
            return {'pairs': 0, 'high_correlation_count': 0, 'matrix': {}}

        high_corr_count = sum(1 for corr in self.correlation_matrix.values() if abs(corr) > self.max_correlation)

        return {
            'pairs': len(self.correlation_matrix),
            'high_correlation_count': high_corr_count,
            'max_correlation_threshold': self.max_correlation,
            'matrix': self.correlation_matrix,
            'open_positions': self.open_positions
        }

    def get_diversification_score(self) -> float:
        """
        Calculate portfolio diversification score (0-1).
        1 = perfectly diversified, 0 = highly correlated
        """
        if not self.open_positions or len(self.open_positions) < 2:
            return 1.0

        # Calculate average correlation between open positions
        correlations = []
        symbols = list(self.open_positions.keys())

        for i, sym1 in enumerate(symbols):
            for sym2 in symbols[i+1:]:
                key1 = f"{sym1}_{sym2}"
                key2 = f"{sym2}_{sym1}"
                corr = abs(self.correlation_matrix.get(key1, self.correlation_matrix.get(key2, 0)))
                correlations.append(corr)

        if not correlations:
            return 1.0

        avg_correlation = np.mean(correlations)

        # Convert to diversification score
        diversification_score = 1 - avg_correlation

        return max(0, min(1, diversification_score))
