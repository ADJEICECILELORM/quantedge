# models/lstm_model.py - Deep Learning LSTM Model
import numpy as np
import pandas as pd
from typing import Tuple
try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("⚠️ TensorFlow not installed. LSTM features disabled.")
    print("   Install with: pip install tensorflow")

class LSTMPredictor:
    """
    LSTM Neural Network for time series prediction.
    Better than tree models for capturing temporal dependencies.
    """
    def __init__(self, sequence_length=60, features=80):
        self.sequence_length = sequence_length
        self.features = features
        self.model = None
        self.scaler = None

    def create_model(self):
        """Build LSTM architecture"""
        if not TENSORFLOW_AVAILABLE:
            print("❌ Cannot create LSTM - TensorFlow not available")
            return None

        model = Sequential([
            LSTM(128, return_sequences=True, input_shape=(self.sequence_length, self.features)),
            Dropout(0.2),
            LSTM(64, return_sequences=True),
            Dropout(0.2),
            LSTM(32),
            Dropout(0.2),
            Dense(16, activation='relu'),
            Dense(3, activation='softmax')  # 3 classes: sell, hold, buy
        ])

        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )

        self.model = model
        return model

    def prepare_sequences(self, df: pd.DataFrame) -> Tuple:
        """
        Convert dataframe to LSTM sequences.
        X shape: (samples, sequence_length, features)
        y shape: (samples, 3) - one-hot encoded
        """
        if len(df) < self.sequence_length:
            return None, None

        # Extract features (exclude non-numeric columns)
        exclude_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume', 'target', 'regime_label']
        feature_cols = [c for c in df.columns if c not in exclude_cols]

        X_data = df[feature_cols].values
        y_data = df['target'].values if 'target' in df.columns else None

        # Create sequences
        X, y = [], []
        for i in range(len(X_data) - self.sequence_length):
            X.append(X_data[i:i+self.sequence_length])
            if y_data is not None:
                y.append(y_data[i+self.sequence_length])

        X = np.array(X)
        if y_data is not None:
            # Convert to one-hot (assuming binary: 0=sell/neutral, 1=buy)
            # Convert to 3-class: 0=sell, 1=hold, 2=buy
            y_3class = []
            for label in y:
                if label == 1:
                    y_3class.append([0, 0, 1])  # Buy
                else:
                    y_3class.append([1, 0, 0])  # Sell/Hold
            y = np.array(y_3class)
        else:
            y = None

        return X, y

    def train(self, df: pd.DataFrame, epochs=50, batch_size=32, validation_split=0.2):
        """Train LSTM model"""
        if not TENSORFLOW_AVAILABLE:
            print("❌ Cannot train - TensorFlow not available")
            return None

        X, y = self.prepare_sequences(df)
        if X is None:
            print("❌ Not enough data for training")
            return None

        if self.model is None:
            self.create_model()

        print(f"Training LSTM on {len(X)} sequences...")
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=1
        )

        return history

    def predict(self, latest_sequence: np.ndarray) -> dict:
        """
        Predict next direction.
        Returns: {'direction': -1/0/1, 'confidence': 0-1, 'probabilities': [sell, hold, buy]}
        """
        if not TENSORFLOW_AVAILABLE or self.model is None:
            return {'direction': 0, 'confidence': 0.5, 'probabilities': [0.33, 0.34, 0.33]}

        # Ensure correct shape
        if latest_sequence.shape != (1, self.sequence_length, self.features):
            latest_sequence = latest_sequence.reshape(1, self.sequence_length, self.features)

        probs = self.model.predict(latest_sequence, verbose=0)[0]

        # Interpret probabilities
        pred_class = np.argmax(probs)
        confidence = probs[pred_class]

        # Map to direction: 0=sell, 1=hold, 2=buy
        direction_map = {0: -1, 1: 0, 2: 1}
        direction = direction_map[pred_class]

        return {
            'direction': direction,
            'confidence': float(confidence),
            'probabilities': probs.tolist()
        }

    def save_model(self, filepath='models/saved/lstm_model.h5'):
        """Save trained model"""
        if self.model and TENSORFLOW_AVAILABLE:
            self.model.save(filepath)
            print(f"✅ LSTM model saved to {filepath}")

    def load_model(self, filepath='models/saved/lstm_model.h5'):
        """Load pre-trained model"""
        if not TENSORFLOW_AVAILABLE:
            print("❌ Cannot load - TensorFlow not available")
            return False

        try:
            self.model = keras.models.load_model(filepath)
            print(f"✅ LSTM model loaded from {filepath}")
            return True
        except Exception as e:
            print(f"❌ Failed to load LSTM: {e}")
            return False
