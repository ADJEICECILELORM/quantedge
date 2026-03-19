# dashboard/quant_metrics.py - Advanced Quantitative Metrics
import numpy as np
import pandas as pd
from typing import Dict, List

class QuantMetrics:
    """
    Professional quant metrics calculator.
    Includes all major risk/return measures used by hedge funds.
    """
    def __init__(self, returns: List[float], benchmark_returns: List[float] = None):
        self.returns = np.array(returns)
        self.benchmark_returns = np.array(benchmark_returns) if benchmark_returns else None
        self.risk_free_rate = 0.02  # 2% annual

    def total_return(self) -> float:
        """Cumulative return"""
        return (1 + self.returns).prod() - 1

    def annualized_return(self, periods_per_year=252) -> float:
        """Annualized return"""
        total_ret = self.total_return()
        n_periods = len(self.returns)
        years = n_periods / periods_per_year
        return (1 + total_ret) ** (1 / years) - 1

    def annualized_volatility(self, periods_per_year=252) -> float:
        """Annualized volatility (standard deviation)"""
        return self.returns.std() * np.sqrt(periods_per_year)

    def sharpe_ratio(self, periods_per_year=252) -> float:
        """
        Sharpe Ratio: (Return - Risk-Free) / Volatility
        Higher is better.
        """
        ann_return = self.annualized_return(periods_per_year)
        ann_vol = self.annualized_volatility(periods_per_year)
        return (ann_return - self.risk_free_rate) / ann_vol if ann_vol != 0 else 0

    def sortino_ratio(self, periods_per_year=252) -> float:
        """
        Sortino Ratio: Like Sharpe but only penalizes downside volatility.
        Higher is better.
        """
        ann_return = self.annualized_return(periods_per_year)
        downside_returns = self.returns[self.returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(periods_per_year) if len(downside_returns) > 0 else 0.0001
        return (ann_return - self.risk_free_rate) / downside_vol

    def calmar_ratio(self, periods_per_year=252) -> float:
        """
        Calmar Ratio: Return / Max Drawdown
        Higher is better.
        """
        ann_return = self.annualized_return(periods_per_year)
        max_dd = abs(self.max_drawdown())
        return ann_return / max_dd if max_dd != 0 else 0

    def max_drawdown(self) -> float:
        """
        Maximum Drawdown: Largest peak-to-trough decline
        Lower (more negative) is worse.
        """
        cumulative = (1 + self.returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    def value_at_risk(self, confidence=0.95) -> float:
        """
        VaR: Maximum loss at given confidence level
        e.g., VaR 95% = worst case loss in 95% of scenarios
        """
        return np.percentile(self.returns, (1 - confidence) * 100)

    def conditional_var(self, confidence=0.95) -> float:
        """
        CVaR (Expected Shortfall): Average loss beyond VaR
        Tail risk measure.
        """
        var = self.value_at_risk(confidence)
        return self.returns[self.returns <= var].mean()

    def omega_ratio(self, threshold=0) -> float:
        """
        Omega Ratio: Probability-weighted ratio of gains vs losses
        Higher is better.
        """
        gains = self.returns[self.returns > threshold].sum()
        losses = abs(self.returns[self.returns < threshold].sum())
        return gains / losses if losses != 0 else float('inf')

    def tail_ratio(self) -> float:
        """
        Tail Ratio: 95th percentile / 5th percentile
        Higher is better (more right-skewed).
        """
        p95 = np.percentile(self.returns, 95)
        p5 = np.percentile(self.returns, 5)
        return abs(p95 / p5) if p5 != 0 else 0

    def gain_to_pain_ratio(self) -> float:
        """
        Gain-to-Pain: Sum of returns / Sum of absolute losses
        Higher is better.
        """
        total_gain = self.returns.sum()
        total_pain = abs(self.returns[self.returns < 0].sum())
        return total_gain / total_pain if total_pain != 0 else 0

    def ulcer_index(self) -> float:
        """
        Ulcer Index: Measures depth and duration of drawdowns
        Lower is better.
        """
        cumulative = (1 + self.returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown_pct = ((cumulative - running_max) / running_max) * 100
        return np.sqrt((drawdown_pct ** 2).mean())

    def skewness(self) -> float:
        """
        Skewness: Asymmetry of return distribution
        Positive = more right-tail gains, Negative = more left-tail losses
        """
        return pd.Series(self.returns).skew()

    def kurtosis(self) -> float:
        """
        Kurtosis: "Fat tail" measure
        Higher = more extreme events
        """
        return pd.Series(self.returns).kurtosis()

    def beta(self) -> float:
        """
        Beta: Correlation with benchmark * (Vol_strategy / Vol_benchmark)
        1.0 = moves with market, >1.0 = more volatile, <1.0 = less volatile
        """
        if self.benchmark_returns is None or len(self.benchmark_returns) != len(self.returns):
            return 0

        covariance = np.cov(self.returns, self.benchmark_returns)[0][1]
        benchmark_variance = np.var(self.benchmark_returns)
        return covariance / benchmark_variance if benchmark_variance != 0 else 0

    def alpha(self, periods_per_year=252) -> float:
        """
        Alpha: Excess return vs benchmark (adjusted for beta)
        Positive = outperforming benchmark
        """
        if self.benchmark_returns is None:
            return 0

        strategy_return = self.annualized_return(periods_per_year)
        benchmark_return = (1 + self.benchmark_returns).prod() - 1
        benchmark_return_ann = (1 + benchmark_return) ** (periods_per_year / len(self.benchmark_returns)) - 1

        beta = self.beta()
        return strategy_return - (self.risk_free_rate + beta * (benchmark_return_ann - self.risk_free_rate))

    def information_ratio(self, periods_per_year=252) -> float:
        """
        Information Ratio: Alpha / Tracking Error
        Measures consistency of outperformance.
        """
        if self.benchmark_returns is None:
            return 0

        excess_returns = self.returns - self.benchmark_returns
        tracking_error = excess_returns.std() * np.sqrt(periods_per_year)
        alpha = self.alpha(periods_per_year)
        return alpha / tracking_error if tracking_error != 0 else 0

    def recovery_factor(self) -> float:
        """
        Recovery Factor: Total Return / Max Drawdown
        Higher is better.
        """
        total_ret = self.total_return()
        max_dd = abs(self.max_drawdown())
        return total_ret / max_dd if max_dd != 0 else 0

    def get_all_metrics(self) -> Dict:
        """
        Calculate all metrics and return as dictionary.
        """
        return {
            # Return Metrics
            'total_return': self.total_return(),
            'annualized_return': self.annualized_return(),
            'annualized_volatility': self.annualized_volatility(),

            # Risk-Adjusted Returns
            'sharpe_ratio': self.sharpe_ratio(),
            'sortino_ratio': self.sortino_ratio(),
            'calmar_ratio': self.calmar_ratio(),
            'omega_ratio': self.omega_ratio(),
            'information_ratio': self.information_ratio(),

            # Risk Metrics
            'max_drawdown': self.max_drawdown(),
            'var_95': self.value_at_risk(0.95),
            'var_99': self.value_at_risk(0.99),
            'cvar_95': self.conditional_var(0.95),
            'ulcer_index': self.ulcer_index(),

            # Distribution Metrics
            'skewness': self.skewness(),
            'kurtosis': self.kurtosis(),
            'tail_ratio': self.tail_ratio(),

            # Market Relative
            'beta': self.beta(),
            'alpha': self.alpha(),

            # Other
            'gain_to_pain': self.gain_to_pain_ratio(),
            'recovery_factor': self.recovery_factor(),
        }
