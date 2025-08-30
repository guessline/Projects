#!/usr/bin/env python3
"""
ML Analyzer for MT5 Bridge - Modern Python ML Version

Advanced machine learning analyzer using latest Python libraries:
- scikit-learn for ML models
- pandas for data processing  
- numpy for numerical computations
- Real-time model training and prediction
"""

import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
import warnings

# Suppress sklearn warnings for cleaner output
warnings.filterwarnings('ignore', category=FutureWarning)

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    print("⚠️  scikit-learn not available. Install with: pip install scikit-learn pandas numpy")
    SKLEARN_AVAILABLE = False

@dataclass
class MLConfig:
    """Configuration for ML Analyzer"""
    data_dir: Path
    model_file: Path
    scaler_file: Path
    min_samples: int = 100
    retrain_interval: int = 1000  # retrain every N samples
    feature_window: int = 10      # lookback window
    
class MLAnalyzer:
    """Advanced ML analyzer for trading signals"""
    
    def __init__(self, config: MLConfig):
        self.config = config
        self.model = None
        self.scaler = None
        self.sample_count = 0
        self.last_retrain = 0
        
        if SKLEARN_AVAILABLE:
            self.load_or_create_model()
    
    def load_or_create_model(self):
        """Load existing model or create new one"""
        try:
            if self.config.model_file.exists() and self.config.scaler_file.exists():
                with open(self.config.model_file, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.config.scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("✓ Loaded existing ML model")
            else:
                self.create_new_model()
        except Exception as e:
            print(f"⚠️  Model loading failed: {e}")
            self.create_new_model()
    
    def create_new_model(self):
        """Create new ML model"""
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        print("✓ Created new ML model")
    
    def save_model(self):
        """Save trained model to disk"""
        try:
            self.config.model_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config.model_file, 'wb') as f:
                pickle.dump(self.model, f)
            with open(self.config.scaler_file, 'wb') as f:
                pickle.dump(self.scaler, f)
            print("✓ Model saved successfully")
        except Exception as e:
            print(f"✗ Model save failed: {e}")
    
    def load_historical_data(self) -> Optional[pd.DataFrame]:
        """Load and prepare historical data"""
        features_file = self.config.data_dir / "features_bt.csv"
        
        if not features_file.exists():
            return None
            
        try:
            # Read CSV with proper parsing
            df = pd.read_csv(
                features_file, 
                sep=';', 
                names=['timestamp', 'close', 'ema', 'atr'],
                parse_dates=['timestamp'],
                date_parser=lambda x: pd.to_datetime(x, format='%Y.%m.%d %H:%M')
            )
            
            # Clean data
            df = df.dropna()
            df = df[df['close'] > 0]
            df = df[df['ema'] > 0]
            df = df[df['atr'] >= 0]
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            print(f"✓ Loaded {len(df)} historical samples")
            return df
            
        except Exception as e:
            print(f"✗ Failed to load historical data: {e}")
            return None
    
    def create_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Create ML features from market data"""
        features = []
        labels = []
        
        for i in range(self.config.feature_window, len(df)):
            # Current window
            window = df.iloc[i-self.config.feature_window:i]
            current = df.iloc[i]
            
            # Feature engineering
            feature_vector = [
                # Price features
                current['close'],
                current['ema'], 
                current['atr'],
                
                # Relative features
                current['close'] / current['ema'],
                current['atr'] / current['close'],
                
                # Technical indicators
                (current['close'] - window['close'].mean()) / window['close'].std(),
                (current['ema'] - window['ema'].mean()) / window['ema'].std(),
                window['close'].pct_change().mean(),
                window['close'].pct_change().std(),
                
                # Momentum features
                window['close'].iloc[-1] / window['close'].iloc[0] - 1,  # Return
                (window['close'] > window['ema']).sum() / len(window),    # EMA crosses
            ]
            
            # Label creation (future price movement)
            if i < len(df) - 1:
                future_price = df.iloc[i + 1]['close']
                price_change = (future_price - current['close']) / current['close']
                
                if price_change > 0.001:      # 0.1% threshold
                    label = 1  # BUY
                elif price_change < -0.001:
                    label = -1  # SELL
                else:
                    label = 0  # NONE
                    
                features.append(feature_vector)
                labels.append(label)
        
        return np.array(features), np.array(labels)
    
    def train_model(self, df: pd.DataFrame) -> Dict:
        """Train the ML model"""
        if not SKLEARN_AVAILABLE:
            return {"error": "scikit-learn not available"}
            
        try:
            # Create features
            X, y = self.create_features(df)
            
            if len(X) < self.config.min_samples:
                return {"error": f"Not enough samples: {len(X)} < {self.config.min_samples}"}
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Save model
            self.save_model()
            self.last_retrain = self.sample_count
            
            return {
                "accuracy": accuracy,
                "samples_used": len(X),
                "train_samples": len(X_train),
                "test_samples": len(X_test),
                "feature_importance": dict(zip(
                    [f"feature_{i}" for i in range(len(X[0]))],
                    self.model.feature_importances_
                ))
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def predict_signal(self, current_data: Dict) -> Tuple[str, float]:
        """Predict signal using ML model"""
        if not SKLEARN_AVAILABLE or self.model is None:
            # Fallback to simple EMA strategy
            close = current_data['close']
            ema = current_data['ema']
            
            if close > ema * 1.001:
                return "BUY", 0.7
            elif close < ema * 0.999:
                return "SELL", 0.7
            else:
                return "NONE", 0.0
        
        try:
            # Create feature vector (simplified for real-time)
            feature_vector = np.array([[
                current_data['close'],
                current_data['ema'],
                current_data['atr'],
                current_data['close'] / current_data['ema'],
                current_data['atr'] / current_data['close'],
                0, 0, 0, 0, 0, 0  # Placeholder for window-based features
            ]])
            
            # Scale and predict
            feature_scaled = self.scaler.transform(feature_vector)
            prediction = self.model.predict(feature_scaled)[0]
            confidence = self.model.predict_proba(feature_scaled)[0].max()
            
            signal_map = {-1: "SELL", 0: "NONE", 1: "BUY"}
            return signal_map[prediction], confidence
            
        except Exception as e:
            print(f"✗ ML prediction error: {e}")
            return "NONE", 0.0
    
    def should_retrain(self) -> bool:
        """Check if model should be retrained"""
        return (self.sample_count - self.last_retrain) >= self.config.retrain_interval

def main():
    """Main function for ML analyzer"""
    print("=" * 60)
    print("MT5 ML Analyzer - Latest Version")
    print("=" * 60)
    
    if not SKLEARN_AVAILABLE:
        print("Installing required packages...")
        os.system("pip install scikit-learn pandas numpy")
        print("Please restart the script after installation.")
        return
    
    # Configuration
    data_dir = Path.home() / "mt5_data"
    config = MLConfig(
        data_dir=data_dir,
        model_file=data_dir / "trading_model.pkl",
        scaler_file=data_dir / "feature_scaler.pkl"
    )
    
    # Create analyzer
    analyzer = MLAnalyzer(config)
    
    # Load and train on historical data
    df = analyzer.load_historical_data()
    if df is not None and len(df) >= config.min_samples:
        print("Training ML model on historical data...")
        result = analyzer.train_model(df)
        
        if "error" in result:
            print(f"✗ Training failed: {result['error']}")
        else:
            print(f"✓ Model trained successfully!")
            print(f"  Accuracy: {result['accuracy']:.3f}")
            print(f"  Samples: {result['samples_used']}")
    else:
        print("⚠️  Not enough historical data for ML training")
        print("Using simple EMA-based strategy")
    
    # Test prediction
    test_data = {
        "close": 1.0958,
        "ema": 1.0951,
        "atr": 0.0016
    }
    
    signal, confidence = analyzer.predict_signal(test_data)
    print(f"\n🧪 Test prediction:")
    print(f"  Data: {test_data}")
    print(f"  Signal: {signal} (confidence: {confidence:.3f})")
    
    print("\n✓ ML Analyzer ready for integration!")

if __name__ == "__main__":
    main()