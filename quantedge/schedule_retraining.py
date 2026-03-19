# schedule_retraining.py - Scheduled Automatic Retraining
"""
Schedule periodic model retraining.
Can be run as a background task or scheduled via Windows Task Scheduler / cron.
"""

import sys
sys.path.append('.')

import schedule
import time
from datetime import datetime
import argparse
from retrain_models import retrain_models


def scheduled_retrain_job(symbol: str = "EURUSD", bars: int = 10000):
    """
    Job to run on schedule.
    """
    print(f"\n{'='*80}")
    print(f"SCHEDULED RETRAINING TRIGGERED")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    try:
        success = retrain_models(
            symbol=symbol,
            bars=bars,
            optimize_hyperparameters=False,  # Don't optimize on scheduled runs (too slow)
            walk_forward_validation=True,
            auto_deploy=True  # Auto-deploy if better
        )

        if success:
            print("\n✅ Scheduled retraining completed successfully")
        else:
            print("\n❌ Scheduled retraining failed")

    except Exception as e:
        print(f"\n❌ Error during scheduled retraining: {e}")
        import traceback
        traceback.print_exc()


def run_scheduler(interval: str = "daily", time_str: str = "02:00", symbol: str = "EURUSD"):
    """
    Run the scheduler.

    Args:
        interval: 'daily', 'weekly', or 'monthly'
        time_str: Time to run (HH:MM format)
        symbol: Symbol to retrain on
    """
    print(f"\n{'='*80}")
    print(f"QUANTEDGE V5 - SCHEDULED RETRAINING SERVICE")
    print(f"{'='*80}")
    print(f"Interval: {interval}")
    print(f"Time: {time_str}")
    print(f"Symbol: {symbol}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")

    # Schedule the job
    if interval == "daily":
        schedule.every().day.at(time_str).do(scheduled_retrain_job, symbol=symbol)
        print(f"✅ Scheduled to run daily at {time_str}")

    elif interval == "weekly":
        # Run every Sunday at specified time
        schedule.every().sunday.at(time_str).do(scheduled_retrain_job, symbol=symbol)
        print(f"✅ Scheduled to run weekly (Sundays) at {time_str}")

    elif interval == "monthly":
        # Run on the 1st of each month
        schedule.every().day.at(time_str).do(
            lambda: scheduled_retrain_job(symbol) if datetime.now().day == 1 else None
        )
        print(f"✅ Scheduled to run monthly (1st of month) at {time_str}")

    else:
        print(f"❌ Unknown interval: {interval}")
        return

    print("\n📅 Next scheduled run:", schedule.next_run())
    print("\nScheduler running... Press Ctrl+C to stop.\n")

    # Run the scheduler
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print("\n\n🛑 Scheduler stopped by user")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='QuantEdge V5 Scheduled Retraining')

    parser.add_argument('--interval', type=str, default='weekly',
                       choices=['daily', 'weekly', 'monthly'],
                       help='Retraining interval (default: weekly)')
    parser.add_argument('--time', type=str, default='02:00',
                       help='Time to run in HH:MM format (default: 02:00)')
    parser.add_argument('--symbol', type=str, default='EURUSD',
                       help='Trading symbol (default: EURUSD)')
    parser.add_argument('--run-now', action='store_true',
                       help='Run immediately before starting scheduler')

    args = parser.parse_args()

    # Optionally run immediately
    if args.run_now:
        print("Running immediate retraining before starting scheduler...\n")
        scheduled_retrain_job(symbol=args.symbol)

    # Start scheduler
    run_scheduler(
        interval=args.interval,
        time_str=args.time,
        symbol=args.symbol
    )


if __name__ == "__main__":
    main()
