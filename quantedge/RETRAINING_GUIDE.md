# QuantEdge V5 - Model Retraining Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Manual Retraining](#manual-retraining)
4. [Scheduled Retraining](#scheduled-retraining)
5. [Advanced Options](#advanced-options)
6. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

QuantEdge V5 includes a comprehensive model retraining system that:

✅ **Fetches fresh data** from MT5
✅ **Creates 100+ enhanced features** (including V5 signals)
✅ **Trains 3 models** (Random Forest, XGBoost, Logistic Regression)
✅ **Validates performance** with walk-forward validation
✅ **Compares with existing models** before deployment
✅ **Auto-deploys** if new models are better
✅ **Backs up old models** automatically
✅ **Tracks performance history** over time

---

## 🚀 Quick Start

### **Option 1: Windows Quick Retrain (Easiest)**

Simply double-click: `quick_retrain.bat`

This will:
1. Fetch 10,000 bars of EURUSD data
2. Train all models with enhanced features
3. Compare with existing models
4. Deploy if better

**Duration**: ~5-10 minutes

---

### **Option 2: Command Line**

```bash
# Basic retraining (recommended)
python retrain_models.py

# Custom symbol and data size
python retrain_models.py --symbol GBPUSD --bars 15000

# With hyperparameter optimization (slower, better results)
python retrain_models.py --optimize

# Skip validation (faster)
python retrain_models.py --no-validation

# Don't auto-deploy (review first)
python retrain_models.py --no-deploy
```

---

## 📖 Manual Retraining

### **Step-by-Step Process**

#### **1. Prepare Your Environment**

```bash
# Navigate to quantedge folder
cd "C:\Users\ADJEI CECIL ELORM\OneDrive\quantedge"

# Activate virtual environment (if using one)
venv\Scripts\activate

# Ensure MT5 is running and logged in
```

#### **2. Run Basic Retraining**

```bash
python retrain_models.py --symbol EURUSD --bars 10000
```

**What Happens:**

```
[1/7] FETCHING HISTORICAL DATA FROM MT5...
✅ Fetched 10000 bars

[2/7] CREATING ENHANCED FEATURES...
✅ Created 106 features

[3/7] GENERATING LABELS...
✅ Labels generated

[4/7] WALK-FORWARD VALIDATION...
✅ Validation complete

[5/7] TRAINING MODELS...
✅ Models trained

[6/7] OPTIMIZING ENSEMBLE WEIGHTS...
✅ Optimal weights found

[7/7] COMPARING WITH EXISTING MODELS...
✅ New models are BETTER - Deploying
```

#### **3. Review Results**

After retraining, check:
- `models/saved/` - New models (deployed if better)
- `models/backup/` - Old models (backed up automatically)
- `models/performance/training_history.json` - Performance over time

---

## ⏰ Scheduled Retraining

### **Option 1: Python Scheduler (Recommended)**

Run the scheduler to automatically retrain models periodically:

```bash
# Weekly retraining (every Sunday at 2 AM)
python schedule_retraining.py --interval weekly --time 02:00

# Daily retraining (every day at 3 AM)
python schedule_retraining.py --interval daily --time 03:00

# Monthly retraining (1st of month at 2 AM)
python schedule_retraining.py --interval monthly --time 02:00

# Run immediately, then start scheduler
python schedule_retraining.py --interval weekly --run-now
```

**Keep it running:**
- Run in a terminal/command prompt
- Or use a process manager like `pm2` or `nssm`
- Or set up as a Windows Service

---

### **Option 2: Windows Task Scheduler**

#### **Create Scheduled Task:**

1. Open **Task Scheduler** (Windows Key → "Task Scheduler")
2. Click **Create Basic Task**
3. Name: "QuantEdge Model Retraining"
4. Trigger: **Weekly** (or Daily/Monthly)
5. Action: **Start a Program**
   - Program: `C:\Users\ADJEI CECIL ELORM\OneDrive\quantedge\venv\Scripts\python.exe`
   - Arguments: `retrain_models.py --symbol EURUSD --bars 10000`
   - Start in: `C:\Users\ADJEI CECIL ELORM\OneDrive\quantedge`
6. Finish

---

### **Option 3: Linux Cron Job**

```bash
# Edit crontab
crontab -e

# Add line (runs every Sunday at 2 AM)
0 2 * * 0 cd /path/to/quantedge && /path/to/python retrain_models.py

# Weekly on Sunday at 2 AM
0 2 * * 0 /path/to/python /path/to/quantedge/retrain_models.py
```

---

## 🔧 Advanced Options

### **1. Hyperparameter Optimization**

```bash
# Enable hyperparameter tuning (takes 30-60 minutes)
python retrain_models.py --optimize
```

**What it does:**
- Tests different parameter combinations for each model
- Uses Grid Search with Time Series Cross-Validation
- Finds optimal settings for your data

**When to use:**
- Monthly or quarterly (not every retrain)
- When performance degrades
- After major market regime changes

---

### **2. Multiple Symbols**

Train models for different symbols:

```bash
# Train EURUSD
python retrain_models.py --symbol EURUSD --bars 10000

# Train GBPUSD
python retrain_models.py --symbol GBPUSD --bars 10000

# Train BTCUSD
python retrain_models.py --symbol BTCUSD --bars 10000
```

---

### **3. Custom Data Size**

```bash
# More data (better for ML, takes longer)
python retrain_models.py --bars 20000

# Less data (faster, good for testing)
python retrain_models.py --bars 5000
```

**Recommendations:**
- **5,000 bars**: Quick test (~2-3 minutes)
- **10,000 bars**: Standard retrain (~5-7 minutes)
- **20,000 bars**: Deep retrain (~10-15 minutes)
- **50,000+ bars**: Full historical (~30+ minutes)

---

### **4. Walk-Forward Validation**

```bash
# Enable walk-forward validation (default)
python retrain_models.py

# Disable for faster training
python retrain_models.py --no-validation
```

**Walk-Forward Validation:**
- Tests model on multiple time windows
- More realistic performance estimates
- Detects overfitting
- Adds ~2-3 minutes to training time

---

### **5. Manual Review Before Deployment**

```bash
# Train but don't auto-deploy
python retrain_models.py --no-deploy

# Review performance
cat models/performance/training_history.json

# Manually deploy if satisfied
cp models/saved/*.pkl models/backup/  # Backup first
# Models are already in models/saved/
```

---

## 📊 Understanding Output

### **Performance Metrics Explained**

```
Random Forest Performance:
  Accuracy:  0.6234    # Overall correct predictions (62.34%)
  Precision: 0.6421    # % of predicted trades that were correct
  Recall:    0.6123    # % of actual good trades that were caught
  F1 Score:  0.6269    # Harmonic mean of precision & recall
  ROC AUC:   0.7156    # Area under curve (0.5=random, 1.0=perfect)
```

**What to look for:**
- **Accuracy > 60%**: Good
- **Accuracy > 65%**: Excellent
- **ROC AUC > 0.70**: Strong predictive power
- **F1 Score**: Balance between precision and recall

---

### **Model Comparison**

```
Existing XGB Accuracy: 0.6234
New XGB Accuracy:      0.6456
Improvement:           +2.22%

✅ New models are BETTER - Will deploy
```

**Deployment Decision:**
- If new accuracy > old accuracy: **Deploy** ✅
- If new accuracy ≤ old accuracy: **Keep existing** ⚠️

---

## 🐛 Troubleshooting

### **Issue: "Failed to connect to MT5"**

**Solution:**
1. Ensure MT5 terminal is running
2. Ensure you're logged into an account
3. Check `utils/mt5_connector.py` has correct path:
   ```python
   self.terminal_path = r"C:\quantedge\terminal64.exe"
   ```

---

### **Issue: "Insufficient data fetched"**

**Solution:**
1. Check symbol exists in MT5 Market Watch
2. Try a different symbol: `--symbol GBPUSD`
3. Reduce bars: `--bars 5000`
4. Check broker provides historical data

---

### **Issue: "New models are WORSE"**

**Solution:**
- **Normal!** Market regimes change
- Old models may be better for current conditions
- System will automatically keep better models
- Try retraining with more data: `--bars 20000`
- Try with optimization: `--optimize`

---

### **Issue: Training takes too long**

**Solutions:**
- Skip validation: `--no-validation`
- Reduce bars: `--bars 5000`
- Don't optimize hyperparameters (default)
- Close other applications

**Expected Times:**
- Basic retrain: 5-10 minutes
- With validation: 7-12 minutes
- With optimization: 30-60 minutes

---

### **Issue: "Out of memory" or crashes**

**Solutions:**
- Reduce bars: `--bars 5000`
- Close other applications
- Restart MT5
- Upgrade RAM (8GB+ recommended)

---

## 📅 Recommended Retraining Schedule

### **Conservative (Recommended for beginners)**
- **Weekly**: Basic retrain with validation
- **Monthly**: Retrain with hyperparameter optimization

### **Aggressive (For active traders)**
- **Daily**: Basic retrain (automated)
- **Weekly**: With hyperparameter optimization

### **Balanced (Recommended for most)**
- **Bi-weekly**: Basic retrain with validation
- **Quarterly**: Full retrain with optimization

---

## 📈 Performance Tracking

### **View Training History**

```bash
# View all training sessions
cat models/performance/training_history.json

# View latest model metadata
cat models/saved/model_metadata.json
```

### **Key Metrics to Track Over Time**

1. **Accuracy trend**: Should stay above 60%
2. **Model improvement**: New > Old?
3. **Feature importance**: Which features matter most?
4. **Ensemble weights**: How models are balanced

---

## 🎯 Best Practices

### **DO:**
✅ Retrain regularly (weekly or bi-weekly)
✅ Let system auto-deploy if models are better
✅ Keep backups (automatic)
✅ Monitor performance trends
✅ Use validation for production retrains
✅ Train on multiple symbols

### **DON'T:**
❌ Retrain too frequently (daily is overkill unless automated)
❌ Skip validation in production
❌ Delete backups manually
❌ Force deploy worse models
❌ Train on insufficient data (<5000 bars)
❌ Optimize hyperparameters every time (too slow)

---

## 🔄 Complete Retraining Workflow

```
1. Schedule Retraining
   ↓
2. Fetch Fresh Data from MT5 (10,000 bars)
   ↓
3. Create Enhanced Features (100+)
   ↓
4. Generate Labels (Buy/Sell/Hold)
   ↓
5. Walk-Forward Validation (5 folds)
   ↓
6. Train 3 Models (RF, XGB, LR)
   ↓
7. Optimize Ensemble Weights
   ↓
8. Compare with Existing Models
   ↓
9. Deploy if Better (auto-backup old models)
   ↓
10. Save Performance History
   ↓
11. Bot Uses New Models Automatically! ✅
```

---

## 📞 Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Review error messages carefully
3. Check MT5 connection and data availability
4. Verify file paths in `mt5_connector.py`
5. Try with fewer bars: `--bars 5000`

---

## 🎓 Quick Reference

```bash
# Basic retrain
python retrain_models.py

# Custom symbol
python retrain_models.py --symbol GBPUSD

# More data
python retrain_models.py --bars 20000

# With optimization (slow)
python retrain_models.py --optimize

# No auto-deploy
python retrain_models.py --no-deploy

# Scheduled weekly
python schedule_retraining.py --interval weekly --time 02:00
```

---

**Happy Retraining! 🚀📈**
