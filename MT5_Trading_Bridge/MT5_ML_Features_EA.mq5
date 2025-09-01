//+------------------------------------------------------------------+
//|                                           MT5_ML_Features_EA.mq5 |
//|                          ML Feature Collection Expert Advisor    |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, ML Trading System"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "Расширенный сбор признаков для машинного обучения"

//--- Input parameters
input string   InpFeaturesFile = "ml_features.csv";     // ML Features output file
input string   InpPredictionsFile = "ml_predictions.txt"; // ML Predictions input file
input int      InpMagicNumber = 54321;                   // Magic number for ML
input double   InpLotSize = 0.1;                        // Lot size
input bool     InpCollectOnly = false;                  // Only collect data (no trading)
input bool     InpEnableLogging = true;                 // Enable detailed logging
input int      InpMinBarsForML = 100;                   // Minimum bars before ML starts

//--- Technical indicator parameters
input int      InpRSIPeriod = 14;        // RSI Period
input int      InpMACDFast = 12;         // MACD Fast EMA
input int      InpMACDSlow = 26;         // MACD Slow EMA
input int      InpMACDSignal = 9;        // MACD Signal
input int      InpBBPeriod = 20;         // Bollinger Bands Period
input double   InpBBDeviation = 2.0;    // Bollinger Bands Deviation
input int      InpStochK = 5;            // Stochastic %K
input int      InpStochD = 3;            // Stochastic %D
input int      InpStochSlowing = 3;      // Stochastic Slowing

//--- Global variables
datetime g_lastBarTime = 0;
int g_barsCollected = 0;
string g_lastMLSignal = "";
datetime g_lastMLSignalTime = 0;

//--- Indicator handles
int h_rsi, h_macd, h_bb_upper, h_bb_lower, h_bb_middle, h_stoch;
int h_ema_9, h_ema_21, h_ema_50, h_sma_200, h_atr;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== ML Features Collection EA Started ===");
    Print("Features file: ", InpFeaturesFile);
    Print("Predictions file: ", InpPredictionsFile);
    Print("Collect only mode: ", InpCollectOnly ? "YES" : "NO");
    
    // Initialize indicators
    if(!InitializeIndicators())
    {
        Print("ERROR: Failed to initialize indicators");
        return INIT_FAILED;
    }
    
    // Create CSV header
    CreateCSVHeader();
    
    Print("=== ML EA Initialization completed ===");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Initialize all technical indicators                              |
//+------------------------------------------------------------------+
bool InitializeIndicators()
{
    // RSI
    h_rsi = iRSI(_Symbol, PERIOD_CURRENT, InpRSIPeriod, PRICE_CLOSE);
    if(h_rsi == INVALID_HANDLE) { Print("ERROR: RSI indicator failed"); return false; }
    
    // MACD
    h_macd = iMACD(_Symbol, PERIOD_CURRENT, InpMACDFast, InpMACDSlow, InpMACDSignal, PRICE_CLOSE);
    if(h_macd == INVALID_HANDLE) { Print("ERROR: MACD indicator failed"); return false; }
    
    // Bollinger Bands
    h_bb_upper = iBands(_Symbol, PERIOD_CURRENT, InpBBPeriod, 0, InpBBDeviation, PRICE_CLOSE);
    h_bb_middle = h_bb_upper;
    h_bb_lower = h_bb_upper;
    if(h_bb_upper == INVALID_HANDLE) { Print("ERROR: Bollinger Bands failed"); return false; }
    
    // Stochastic
    h_stoch = iStochastic(_Symbol, PERIOD_CURRENT, InpStochK, InpStochD, InpStochSlowing, MODE_SMA, STO_LOWHIGH);
    if(h_stoch == INVALID_HANDLE) { Print("ERROR: Stochastic failed"); return false; }
    
    // Moving Averages
    h_ema_9 = iMA(_Symbol, PERIOD_CURRENT, 9, 0, MODE_EMA, PRICE_CLOSE);
    h_ema_21 = iMA(_Symbol, PERIOD_CURRENT, 21, 0, MODE_EMA, PRICE_CLOSE);
    h_ema_50 = iMA(_Symbol, PERIOD_CURRENT, 50, 0, MODE_EMA, PRICE_CLOSE);
    h_sma_200 = iMA(_Symbol, PERIOD_CURRENT, 200, 0, MODE_SMA, PRICE_CLOSE);
    
    // ATR
    h_atr = iATR(_Symbol, PERIOD_CURRENT, 14);
    if(h_atr == INVALID_HANDLE) { Print("ERROR: ATR indicator failed"); return false; }
    
    Print("✓ All indicators initialized successfully");
    return true;
}

//+------------------------------------------------------------------+
//| Create CSV header for ML features                                |
//+------------------------------------------------------------------+
void CreateCSVHeader()
{
    int handle = FileOpen(InpFeaturesFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot create features file header");
        return;
    }
    
    // ML Features header
    string header = "timestamp;open;high;low;close;volume;spread;" +
                   "rsi;macd_main;macd_signal;macd_histogram;" +
                   "bb_upper;bb_middle;bb_lower;bb_position;" +
                   "stoch_main;stoch_signal;" +
                   "ema_9;ema_21;ema_50;sma_200;" +
                   "atr;volatility;" +
                   "price_change_1;price_change_5;price_change_15;" +
                   "volume_ratio;time_hour;time_dow;" +
                   "target\n";
    
    FileWriteString(handle, header);
    FileClose(handle);
    
    Print("✓ CSV header created with ML features");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Work only on new bars
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(currentBarTime == g_lastBarTime)
        return;
        
    g_lastBarTime = currentBarTime;
    g_barsCollected++;
    
    // Collect ML features
    if(!CollectMLFeatures())
    {
        if(InpEnableLogging)
            Print("Failed to collect ML features");
        return;
    }
    
    // If not in collect-only mode and have enough data
    if(!InpCollectOnly && g_barsCollected > InpMinBarsForML)
    {
        // Small delay for Python ML processing
        Sleep(300);
        
        // Read ML prediction
        string signal;
        double confidence;
        datetime signalTime;
        
        if(ReadMLPrediction(signal, confidence, signalTime))
        {
            ProcessMLSignal(signal, confidence, signalTime);
        }
    }
}

//+------------------------------------------------------------------+
//| Collect comprehensive ML features                                |
//+------------------------------------------------------------------+
bool CollectMLFeatures()
{
    // Basic OHLCV data
    double open = iOpen(_Symbol, PERIOD_CURRENT, 1);
    double high = iHigh(_Symbol, PERIOD_CURRENT, 1);
    double low = iLow(_Symbol, PERIOD_CURRENT, 1);
    double close = iClose(_Symbol, PERIOD_CURRENT, 1);
    long volume = iVolume(_Symbol, PERIOD_CURRENT, 1);
    double spread = (SymbolInfoDouble(_Symbol, SYMBOL_ASK) - SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point;
    
    // Technical indicators
    double rsi = GetIndicatorValue(h_rsi, 0, 1);
    double macd_main = GetIndicatorValue(h_macd, 0, 1);
    double macd_signal = GetIndicatorValue(h_macd, 1, 1);
    double macd_histogram = macd_main - macd_signal;
    
    double bb_upper = GetIndicatorValue(h_bb_upper, 1, 1);
    double bb_middle = GetIndicatorValue(h_bb_middle, 0, 1);
    double bb_lower = GetIndicatorValue(h_bb_lower, 2, 1);
    double bb_position = (close - bb_lower) / (bb_upper - bb_lower); // 0-1 position in BB
    
    double stoch_main = GetIndicatorValue(h_stoch, 0, 1);
    double stoch_signal = GetIndicatorValue(h_stoch, 1, 1);
    
    double ema_9 = GetIndicatorValue(h_ema_9, 0, 1);
    double ema_21 = GetIndicatorValue(h_ema_21, 0, 1);
    double ema_50 = GetIndicatorValue(h_ema_50, 0, 1);
    double sma_200 = GetIndicatorValue(h_sma_200, 0, 1);
    
    double atr = GetIndicatorValue(h_atr, 0, 1);
    double volatility = (high - low) / close;
    
    // Price changes
    double price_1 = iClose(_Symbol, PERIOD_CURRENT, 2);
    double price_5 = iClose(_Symbol, PERIOD_CURRENT, 6);
    double price_15 = iClose(_Symbol, PERIOD_CURRENT, 16);
    
    double price_change_1 = (close - price_1) / price_1;
    double price_change_5 = (close - price_5) / price_5;
    double price_change_15 = (close - price_15) / price_15;
    
    // Volume analysis
    long avg_volume = 0;
    for(int i = 2; i <= 11; i++)
        avg_volume += iVolume(_Symbol, PERIOD_CURRENT, i);
    avg_volume /= 10;
    double volume_ratio = (double)volume / (double)avg_volume;
    
    // Time features
    MqlDateTime dt;
    TimeToStruct(iTime(_Symbol, PERIOD_CURRENT, 1), dt);
    int time_hour = dt.hour;
    int time_dow = dt.day_of_week;
    
    // Target variable (future price movement)
    double future_price = iClose(_Symbol, PERIOD_CURRENT, 0); // current price
    double target = (future_price - close) / close; // price change
    
    // Validate all data
    if(close <= 0 || ema_21 <= 0 || atr <= 0 || rsi <= 0)
    {
        Print("ERROR: Invalid indicator data");
        return false;
    }
    
    // Format timestamp
    datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
    string timeStr = TimeToString(barTime, TIME_DATE|TIME_MINUTES);
    
    // Create ML features line
    string featuresLine = StringFormat(
        "%s;%.5f;%.5f;%.5f;%.5f;%d;%.2f;" +           // timestamp, OHLCV, spread
        "%.2f;%.5f;%.5f;%.5f;" +                      // RSI, MACD
        "%.5f;%.5f;%.5f;%.3f;" +                      // Bollinger Bands
        "%.2f;%.2f;" +                                // Stochastic
        "%.5f;%.5f;%.5f;%.5f;" +                      // Moving Averages
        "%.5f;%.5f;" +                                // ATR, Volatility
        "%.5f;%.5f;%.5f;" +                           // Price changes
        "%.2f;%d;%d;" +                               // Volume ratio, time
        "%.5f\n",                                     // Target
        
        timeStr, open, high, low, close, volume, spread,
        rsi, macd_main, macd_signal, macd_histogram,
        bb_upper, bb_middle, bb_lower, bb_position,
        stoch_main, stoch_signal,
        ema_9, ema_21, ema_50, sma_200,
        atr, volatility,
        price_change_1, price_change_5, price_change_15,
        volume_ratio, time_hour, time_dow,
        target
    );
    
    // Write to file
    int handle = FileOpen(InpFeaturesFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open ML features file: ", GetLastError());
        return false;
    }
    
    FileSeek(handle, 0, SEEK_END);
    uint bytesWritten = FileWriteString(handle, featuresLine);
    FileFlush(handle);
    FileClose(handle);
    
    if(bytesWritten > 0)
    {
        if(InpEnableLogging && g_barsCollected % 10 == 0)
            Print("✓ ML Features collected: bar ", g_barsCollected, " RSI=", rsi, " MACD=", macd_main);
        return true;
    }
    
    return false;
}

//+------------------------------------------------------------------+
//| Get indicator value safely                                       |
//+------------------------------------------------------------------+
double GetIndicatorValue(int handle, int buffer, int index)
{
    double value[];
    if(CopyBuffer(handle, buffer, index, 1, value) <= 0)
    {
        Print("ERROR: Failed to get indicator value");
        return 0.0;
    }
    return value[0];
}

//+------------------------------------------------------------------+
//| Read ML prediction from Python                                   |
//+------------------------------------------------------------------+
bool ReadMLPrediction(string &signal, double &confidence, datetime &signalTime)
{
    signal = "";
    confidence = 0.0;
    signalTime = 0;
    
    int handle = FileOpen(InpPredictionsFile, FILE_READ|FILE_TXT|FILE_ANSI);
    if(handle == INVALID_HANDLE)
        return false;
    
    string line = FileReadString(handle);
    FileClose(handle);
    
    if(StringLen(line) == 0)
        return false;
    
    // Parse ML prediction: "SIGNAL;CONFIDENCE;TIMESTAMP"
    string parts[];
    int numParts = StringSplit(line, ';', parts);
    
    if(numParts < 3)
    {
        Print("ERROR: Invalid ML prediction format: ", line);
        return false;
    }
    
    signal = parts[0];
    confidence = StringToDouble(parts[1]);
    signalTime = StringToTime(parts[2]);
    
    if(InpEnableLogging)
        Print("✓ ML Prediction: ", signal, " (conf: ", confidence, ") for ", TimeToString(signalTime));
    
    return true;
}

//+------------------------------------------------------------------+
//| Process ML signal with confidence filtering                      |
//+------------------------------------------------------------------+
void ProcessMLSignal(string signal, double confidence, datetime signalTime)
{
    // Avoid duplicate signals
    if(signal == g_lastMLSignal && signalTime == g_lastMLSignalTime)
        return;
        
    g_lastMLSignal = signal;
    g_lastMLSignalTime = signalTime;
    
    // Check signal freshness (within 2 minutes)
    if(TimeCurrent() - signalTime > 120)
    {
        if(InpEnableLogging)
            Print("ML signal too old, ignoring");
        return;
    }
    
    // Confidence filtering
    double min_confidence = 0.7; // Minimum 70% confidence
    if(confidence < min_confidence)
    {
        if(InpEnableLogging)
            Print("ML signal confidence too low: ", confidence, " < ", min_confidence);
        return;
    }
    
    // Count current positions
    int positions = CountMLPositions();
    
    if(signal == "BUY" && positions == 0)
    {
        OpenMLBuyPosition(confidence);
    }
    else if(signal == "SELL" && positions == 0)
    {
        OpenMLSellPosition(confidence);
    }
    else if(signal == "CLOSE_ALL")
    {
        CloseAllMLPositions();
    }
}

//+------------------------------------------------------------------+
//| Open ML Buy Position with dynamic SL/TP                         |
//+------------------------------------------------------------------+
void OpenMLBuyPosition(double confidence)
{
    if(!IsTradingAllowed())
        return;
        
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double atr_value = GetIndicatorValue(h_atr, 0, 1);
    
    // Dynamic SL/TP based on ATR and confidence
    double atr_pips = atr_value / _Point;
    double sl_pips = MathMax(20, atr_pips * 1.5); // Minimum 20 pips or 1.5*ATR
    double tp_pips = sl_pips * (1 + confidence); // Higher confidence = higher TP
    
    double sl = ask - sl_pips * _Point;
    double tp = ask + tp_pips * _Point;
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.magic = InpMagicNumber;
    request.comment = StringFormat("ML_BUY_%.2f", confidence);
    
    if(OrderSend(request, result))
    {
        Print("🤖 ML BUY opened: ticket=", result.order, " price=", result.price, 
              " conf=", confidence, " SL=", sl_pips, "pips TP=", tp_pips, "pips");
    }
    else
    {
        Print("ERROR: ML BUY failed: ", result.retcode);
    }
}

//+------------------------------------------------------------------+
//| Open ML Sell Position                                            |
//+------------------------------------------------------------------+
void OpenMLSellPosition(double confidence)
{
    if(!IsTradingAllowed())
        return;
        
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double atr_value = GetIndicatorValue(h_atr, 0, 1);
    
    // Dynamic SL/TP
    double atr_pips = atr_value / _Point;
    double sl_pips = MathMax(20, atr_pips * 1.5);
    double tp_pips = sl_pips * (1 + confidence);
    
    double sl = bid + sl_pips * _Point;
    double tp = bid - tp_pips * _Point;
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.magic = InpMagicNumber;
    request.comment = StringFormat("ML_SELL_%.2f", confidence);
    
    if(OrderSend(request, result))
    {
        Print("🤖 ML SELL opened: ticket=", result.order, " price=", result.price,
              " conf=", confidence, " SL=", sl_pips, "pips TP=", tp_pips, "pips");
    }
    else
    {
        Print("ERROR: ML SELL failed: ", result.retcode);
    }
}

//+------------------------------------------------------------------+
//| Count ML positions                                               |
//+------------------------------------------------------------------+
int CountMLPositions()
{
    int count = 0;
    int total = PositionsTotal();
    
    for(int i = 0; i < total; i++)
    {
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol && 
               PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
            {
                count++;
            }
        }
    }
    return count;
}

//+------------------------------------------------------------------+
//| Close all ML positions                                           |
//+------------------------------------------------------------------+
void CloseAllMLPositions()
{
    int total = PositionsTotal();
    
    for(int i = total - 1; i >= 0; i--)
    {
        ulong ticket = PositionGetTicket(i);
        if(PositionSelectByTicket(ticket))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol && 
               PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
            {
                MqlTradeRequest request = {};
                MqlTradeResult result = {};
                
                request.action = TRADE_ACTION_DEAL;
                request.symbol = _Symbol;
                request.volume = PositionGetDouble(POSITION_VOLUME);
                request.type = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 
                              ORDER_TYPE_SELL : ORDER_TYPE_BUY;
                request.price = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? 
                               SymbolInfoDouble(_Symbol, SYMBOL_BID) : 
                               SymbolInfoDouble(_Symbol, SYMBOL_ASK);
                request.magic = InpMagicNumber;
                request.position = ticket;
                request.comment = "ML_CLOSE";
                
                if(OrderSend(request, result))
                {
                    Print("✓ ML Position closed: ticket=", ticket);
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Check if trading is allowed                                      |
//+------------------------------------------------------------------+
bool IsTradingAllowed()
{
    return TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) && 
           MQLInfoInteger(MQL_TRADE_ALLOWED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== ML Features EA stopped ===");
    Print("Bars collected: ", g_barsCollected);
    Print("Reason: ", reason);
}