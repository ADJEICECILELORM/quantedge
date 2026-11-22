# features/label_generator.py
import pandas as pd
import numpy as np

class LabelGenerator:
    def __init__(self, forward_bars=5, volatility_lookback=14, vol_multiple=0.5):
        self.forward_bars = forward_bars
        self.volatility_lookback = volatility_lookback
        self.vol_multiple = vol_multiple

    def create_labels(self, df):
        df = df.copy()
        threshold = df['atr_14'] * self.vol_multiple
        future_close = df['close'].shift(-self.forward_bars)
        current_close = df['close']
        price_change = future_close - current_close
        df['target'] = np.where(price_change > threshold, 1, 0)
        df.loc[future_close.isna() | price_change.isna(), 'target'] = np.nan
        df.dropna(subset=['target'], inplace=True)
        df['target'] = df['target'].astype(int)
        return df

    def print_stats(self, df):
        counts = df['target'].value_counts()
        total = len(df)
        print(f"\n--- Label Statistics ---")
        print(f"Total samples: {total}")
        print(f"Buy Signals (1): {counts.get(1, 0)} ({(counts.get(1,0)/total)*100:.1f}%)")
        print(f"Flat/Sell Signals (0): {counts.get(0, 0)} ({(counts.get(0,0)/total)*100:.1f}%)")
        print(f"------------------------")
