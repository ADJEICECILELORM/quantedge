# utils/parallel_processor.py - Parallel Processing for Multi-Symbol Analysis
import concurrent.futures
from typing import List, Dict, Callable, Any
import logging
from functools import partial

logger = logging.getLogger(__name__)


class ParallelProcessor:
    """
    Parallel processor for analyzing multiple symbols simultaneously.

    Uses:
    - ThreadPoolExecutor for I/O-bound tasks (data fetching)
    - ProcessPoolExecutor for CPU-bound tasks (feature engineering)
    """

    def __init__(self, max_workers: int = None):
        """
        Initialize parallel processor.

        Args:
            max_workers: Maximum number of workers (default: CPU count)
        """
        self.max_workers = max_workers
        self.completed_tasks = 0
        self.failed_tasks = 0

    def process_symbols_parallel(
        self,
        symbols: List[str],
        analysis_func: Callable,
        *args,
        timeout: float = 30.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process multiple symbols in parallel using threading.

        Args:
            symbols: List of trading symbols
            analysis_func: Function to call for each symbol
            *args: Additional positional arguments for analysis_func
            timeout: Timeout per symbol in seconds
            **kwargs: Additional keyword arguments for analysis_func

        Returns:
            Dict mapping symbol -> result
        """
        results = {}

        if not symbols:
            logger.warning("No symbols provided for parallel processing")
            return results

        try:
            # Use ThreadPoolExecutor for I/O-bound operations
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Create partial function with fixed args
                func = partial(analysis_func, *args, **kwargs)

                # Submit all tasks
                future_to_symbol = {
                    executor.submit(func, symbol): symbol
                    for symbol in symbols
                }

                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_symbol, timeout=timeout * len(symbols)):
                    symbol = future_to_symbol[future]
                    try:
                        result = future.result(timeout=timeout)
                        results[symbol] = result
                        self.completed_tasks += 1
                    except concurrent.futures.TimeoutError:
                        logger.error(f"Timeout analyzing {symbol}")
                        results[symbol] = None
                        self.failed_tasks += 1
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol}: {e}")
                        results[symbol] = None
                        self.failed_tasks += 1

        except Exception as e:
            logger.exception(f"Parallel processing failed: {e}")

        return results

    def process_batch_parallel(
        self,
        items: List[Any],
        process_func: Callable,
        *args,
        use_processes: bool = False,
        timeout: float = 30.0,
        **kwargs
    ) -> List[Any]:
        """
        Process a batch of items in parallel.

        Args:
            items: List of items to process
            process_func: Function to call for each item
            *args: Additional positional arguments
            use_processes: Use ProcessPoolExecutor instead of threads (for CPU-bound tasks)
            timeout: Timeout per item in seconds
            **kwargs: Additional keyword arguments

        Returns:
            List of results (same order as input)
        """
        if not items:
            return []

        results = [None] * len(items)

        try:
            # Choose executor based on task type
            Executor = (
                concurrent.futures.ProcessPoolExecutor
                if use_processes
                else concurrent.futures.ThreadPoolExecutor
            )

            with Executor(max_workers=self.max_workers) as executor:
                # Create partial function
                func = partial(process_func, *args, **kwargs)

                # Submit all tasks with index tracking
                future_to_index = {
                    executor.submit(func, item): idx
                    for idx, item in enumerate(items)
                }

                # Collect results
                for future in concurrent.futures.as_completed(future_to_index, timeout=timeout * len(items)):
                    idx = future_to_index[future]
                    try:
                        result = future.result(timeout=timeout)
                        results[idx] = result
                        self.completed_tasks += 1
                    except Exception as e:
                        logger.error(f"Error processing item {idx}: {e}")
                        self.failed_tasks += 1

        except Exception as e:
            logger.exception(f"Batch parallel processing failed: {e}")

        return results

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        total = self.completed_tasks + self.failed_tasks
        success_rate = (self.completed_tasks / total * 100) if total > 0 else 0

        return {
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'total_tasks': total,
            'success_rate_pct': success_rate
        }

    def reset_stats(self):
        """Reset statistics counters"""
        self.completed_tasks = 0
        self.failed_tasks = 0


# Helper function for parallel symbol analysis
def analyze_symbol_wrapper(
    symbol: str,
    bot_instance,
    current_time
) -> Dict:
    """
    Wrapper function for parallel symbol analysis.

    Args:
        symbol: Trading symbol
        bot_instance: QuantEdge bot instance
        current_time: Current datetime

    Returns:
        Analysis result dict or None if failed
    """
    try:
        return bot_instance.analyze_market_v5(symbol, current_time)
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None


# Helper function for parallel correlation matrix calculation
def calculate_pairwise_correlation(
    pair: tuple,
    mt5_connector,
    timeframe,
    lookback: int = 100
) -> tuple:
    """
    Calculate correlation between two symbols.

    Args:
        pair: Tuple of (symbol1, symbol2)
        mt5_connector: MT5 connector instance
        timeframe: MT5 timeframe
        lookback: Number of bars to analyze

    Returns:
        Tuple of (symbol1, symbol2, correlation)
    """
    symbol1, symbol2 = pair

    try:
        df1 = mt5_connector.get_latest_bars(symbol1, timeframe, count=lookback)
        df2 = mt5_connector.get_latest_bars(symbol2, timeframe, count=lookback)

        if df1 is None or df2 is None or len(df1) < lookback or len(df2) < lookback:
            return (symbol1, symbol2, 0.0)

        # Calculate correlation on returns
        returns1 = df1['close'].pct_change().dropna()
        returns2 = df2['close'].pct_change().dropna()

        # Align lengths
        min_len = min(len(returns1), len(returns2))
        correlation = returns1.iloc[-min_len:].corr(returns2.iloc[-min_len:])

        return (symbol1, symbol2, float(correlation))

    except Exception as e:
        logger.error(f"Error calculating correlation for {symbol1} vs {symbol2}: {e}")
        return (symbol1, symbol2, 0.0)
