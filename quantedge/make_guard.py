# make_guard.py
import os

# Ensure folder exists
if not os.path.exists("risk"):
    os.makedirs("risk")

# Create __init__.py
with open("risk/__init__.py", "w") as f:
    f.write("")

# Create drawdown_guard.py
with open("risk/drawdown_guard.py", "w", encoding="utf-8") as f:
    f.write("""
class DrawdownGuard:
    def __init__(self, account_balance, max_daily_loss_percent=2.0):
        self.start_balance = account_balance
        self.max_loss = account_balance * (max_daily_loss_percent / 100)
        self.is_broken = False

    def check_status(self, current_equity):
        if self.is_broken:
            return True 

        pnl = current_equity - self.start_balance
        
        if pnl <= -self.max_loss:
            self.is_broken = True
            print(f"🚨 STOP-THE-BLEEDING TRIGGERED!")
            print(f"🚨 Starting Equity: {self.start_balance}")
            print(f"🚨 Current Equity: {current_equity}")
            print(f"🚨 Loss Limit: -${self.max_loss}")
            print(f"🚨 Bot is SHUTTING DOWN for the day.")
            return True
        
        return False

    def print_status(self, current_equity):
        pnl = current_equity - self.start_balance
        pnl_percent = (pnl / self.start_balance) * 100
        print(f"🛡️ Daily P&L: ${pnl:.2f} ({pnl_percent:+.2f}%) | Limit: -{self.max_loss:.2f}")
""")

print("✅ Created risk/drawdown_guard.py")