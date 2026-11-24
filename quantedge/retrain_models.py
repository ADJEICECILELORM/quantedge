# retrain_models.py - Automated Model Retraining System
"""
Automated retraining script that:
1. Fetches recent data from MT5
2. Creates enhanced features with V5 signals
3. Generates labels
4. Trains models with validation
5. Compares with existing models
6. Deploys if better
7. Can be scheduled to run periodically
"""

import sys
sys.path.append('.')

import MetaTrader5 as mt5
from datetime import datetime
import argparse

# Core components
from utils.mt5_connector import MT5Connector
from features.enhanced_feature_engineer import EnhancedFeatureEngineer
from features.label_generator import LabelGenerator
from models.advanced_model_trainer import AdvancedModelTrainer


def retrain_models(symbol: str = "EURUSD",
                  timeframe = mt5.TIMEFRAME_M5,
                  bars: int = 10000,
                  optimize_hyperparameters: bool = False,
                  walk_forward_validation: bool = True,
                  auto_deploy: bool = True,
                  challenger: bool = False):
    """
    Complete retraining pipeline.

    Args:
        symbol: Trading symbol to train on
        timeframe: MT5 timeframe
        bars: Number of historical bars to fetch
        optimize_hyperparameters: Whether to optimize hyperparameters (slow)
        walk_forward_validation: Whether to perform walk-forward validation
        auto_deploy: Automatically deploy if models are better
    """

    print("="*80)
    print(" QUANTEDGE V5 - AUTOMATED MODEL RETRAINING")
    print("="*80)
    print(f"Symbol: {symbol}")
    print("Timeframe: M5")
    print(f"Bars: {bars}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # ========== Step 1: Fetch Data ==========
    print("\n[1/7] FETCHING HISTORICAL DATA FROM MT5...")
    mt5_conn = MT5Connector()

    if not mt5_conn.connect():
        print("❌ Failed to connect to MT5. Exiting.")
        return False

    df_main = mt5_conn.get_historical_data(symbol, timeframe, bars=bars)

    if df_main is None or len(df_main) < 1000:
        print(f"❌ Insufficient data fetched: {len(df_main) if df_main is not None else 0} bars")
        mt5_conn.shutdown()
        return False

    print(f"✅ Fetched {len(df_main)} bars")

    # Fetch additional data for sentiment features (optional)
    print("\nFetching crypto data for sentiment features...")
    df_btc = mt5_conn.get_historical_data("BTCUSD", timeframe, bars=bars)
    df_eth = mt5_conn.get_historical_data("ETHUSD", timeframe, bars=bars)

    if df_btc is None:
        print("⚠️ BTC data not available")
    else:
        print(f"✅ Fetched {len(df_btc)} BTC bars")

    if df_eth is None:
        print("⚠️ ETH data not available")
    else:
        print(f"✅ Fetched {len(df_eth)} ETH bars")

    mt5_conn.shutdown()

    # ========== Step 2: Create Enhanced Features ==========
    print("\n[2/7] CREATING ENHANCED FEATURES...")
    fe = EnhancedFeatureEngineer()

    df = fe.create_features(
        df_main=df_main,
        df_crypto=df_btc,
        df_eth=df_eth,
        df_gold=None,
        lead_lag_data=None,  # TODO: Add actual lead-lag data
        news_calendar=None,  # TODO: Add actual news calendar
        probability_data=None  # TODO: Add actual probability data
    )

    print(f"✅ Created {len(df.columns)} features")
    print(f"✅ Final dataset: {len(df)} rows")

    if len(df) < 1000:
        print("❌ Insufficient data after feature engineering")
        return False

    # ========== Step 3: Generate Labels ==========
    print("\n[3/7] GENERATING LABELS...")
    lg = LabelGenerator(forward_bars=5, vol_multiple=0.5)
    df = lg.create_labels(df)

    print("✅ Labels generated")
    print("   Class distribution:")
    print(df['target'].value_counts())

    # ========== Step 4: Walk-Forward Validation (Optional) ==========
    if walk_forward_validation:
        print("\n[4/7] WALK-FORWARD VALIDATION...")
        trainer_validation = AdvancedModelTrainer(df)
        validation_scores = trainer_validation.walk_forward_validation(n_splits=5)
    else:
        print("\n[4/7] SKIPPING WALK-FORWARD VALIDATION")

    # ========== Step 5: Train Models ==========
    model_dir = "models/challenger" if challenger else "models/saved"
    print(f"\n[5/7] TRAINING MODELS (target: {model_dir})...")
    trainer = AdvancedModelTrainer(df, model_dir=model_dir)
    performance = trainer.train_models(optimize=optimize_hyperparameters)

    # ========== Step 6: Optimize Ensemble Weights ==========
    print("\n[6/7] OPTIMIZING ENSEMBLE WEIGHTS...")
    X_train, X_test, y_train, y_test, _ = trainer.prepare_data()
    ensemble_weights = trainer.optimize_ensemble_weights(X_test, y_test)

    # ========== Step 7: Compare & Deploy ==========
    if challenger:
        from models.championship import should_promote
        print("\n[7/7] CHALLENGER MODE - champion is untouched")
        trainer.save_models(with_backup=False)
        promote, details = should_promote()
        print(f"   Promotion decision: {'PROMOTE' if promote else 'KEEP CHAMPION'}")
        print(f"   {details['reason']}")
        print("\n   To promote manually: "
              "from models.championship import promote_challenger; promote_challenger()")
        return True

    print("\n[7/7] COMPARING WITH EXISTING MODELS...")
    is_better = trainer.compare_with_existing_models(X_test, y_test)

    if is_better and auto_deploy:
        print("\n✅ NEW MODELS ARE BETTER - DEPLOYING...")
        trainer.save_models(with_backup=True)
        print("✅ DEPLOYMENT COMPLETE")
    elif is_better and not auto_deploy:
        print("\n⚠️ NEW MODELS ARE BETTER BUT AUTO-DEPLOY IS OFF")
        print("Run with --deploy flag to deploy")
        trainer.save_models(with_backup=True)
    else:
        print("\n⚠️ NEW MODELS ARE NOT BETTER - KEEPING EXISTING MODELS")
        print("Existing models will continue to be used")

    # ========== Training Summary ==========
    trainer.print_training_summary()

    print("\n" + "="*80)
    print(" RETRAINING COMPLETE")
    print("="*80)
    print("\n📊 Performance Summary:")
    print(f"   RF Accuracy:  {performance['rf']['accuracy']:.4f}")
    print(f"   XGB Accuracy: {performance['xgb']['accuracy']:.4f}")
    print(f"   LR Accuracy:  {performance['lr']['accuracy']:.4f}")

    print("\n🔄 Ensemble Weights:")
    print(f"   RF:  {ensemble_weights['rf']:.2f}")
    print(f"   XGB: {ensemble_weights['xgb']:.2f}")
    print(f"   LR:  {ensemble_weights['lr']:.2f}")

    print("\n💾 Models saved to: models/saved/")
    print("📁 Backup saved to: models/backup/")
    print("📈 Performance history: models/performance/training_history.json")

    return True


def main():
    """Main entry point with command-line arguments"""
    parser = argparse.ArgumentParser(description='QuantEdge V5 Model Retraining')

    parser.add_argument('--symbol', type=str, default='EURUSD',
                       help='Trading symbol (default: EURUSD)')
    parser.add_argument('--bars', type=int, default=10000,
                       help='Number of historical bars (default: 10000)')
    parser.add_argument('--optimize', action='store_true',
                       help='Optimize hyperparameters (slow)')
    parser.add_argument('--no-validation', action='store_true',
                       help='Skip walk-forward validation')
    parser.add_argument('--no-deploy', action='store_true',
                       help='Do not auto-deploy even if better')
    parser.add_argument('--challenger', action='store_true',
                       help='Treat the new models as a challenger: train into '
                            'models/challenger and evaluate promotion rule; the '
                            'champion in models/saved stays untouched')

    args = parser.parse_args()

    success = retrain_models(
        symbol=args.symbol,
        bars=args.bars,
        optimize_hyperparameters=args.optimize,
        walk_forward_validation=not args.no_validation,
        auto_deploy=not args.no_deploy,
        challenger=args.challenger
    )

    if success:
        print("\n✅ Retraining successful!")
        return 0
    else:
        print("\n❌ Retraining failed!")
        return 1


if __name__ == "__main__":
    exit(main())
