
class DrawdownGuard:
    def __init__(self, account_balance, max_daily_loss_percent=2.0):
        self.max_daily_loss_percent = max_daily_loss_percent
        self.start_balance = account_balance
        self.max_loss = account_balance * (max_daily_loss_percent / 100)
        self.is_broken = False
        self.current_equity = account_balance
        self.peak_equity = account_balance

    def observe(self, current_equity):
        """Record the latest equity so drawdown queries stay current."""
        self.current_equity = current_equity
        self.peak_equity = max(self.peak_equity, current_equity)

    @property
    def current_drawdown(self):
        """Peak-to-trough drawdown as a fraction in [0, 1]."""
        peak = max(self.peak_equity, self.start_balance)
        if peak <= 0:
            return 0.0
        return float(min(max((peak - self.current_equity) / peak, 0.0), 1.0))

    def reset_daily(self, new_balance):
        """Start a fresh daily loss window (call at each new trading day)."""
        self.start_balance = new_balance
        self.max_loss = new_balance * (self.max_daily_loss_percent / 100)
        self.is_broken = False
        self.peak_equity = new_balance
        self.current_equity = new_balance

    def check_status(self, current_equity):
        if self.is_broken:
            return True

        self.observe(current_equity)
        pnl = current_equity - self.start_balance

        if pnl <= -self.max_loss:
            self.is_broken = True
            print("🚨 STOP-THE-BLEEDING TRIGGERED!")
            print(f"🚨 Starting Equity: {self.start_balance}")
            print(f"🚨 Current Equity: {current_equity}")
            print(f"🚨 Loss Limit: -${self.max_loss}")
            print("🚨 Bot is SHUTTING DOWN for the day.")
            return True

        return False

    def print_status(self, current_equity):
        pnl = current_equity - self.start_balance
        pnl_percent = (pnl / self.start_balance) * 100
        print(f"🛡️ Daily P&L: ${pnl:.2f} ({pnl_percent:+.2f}%) | Limit: -{self.max_loss:.2f}")
