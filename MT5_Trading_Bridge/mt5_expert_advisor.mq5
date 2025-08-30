//+------------------------------------------------------------------+
//|                                           MT5_Python_Bridge.mq5 |
//|                                  Copyright 2024, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "2.00"
#property description "MT5 Python Bridge Expert Advisor - Latest Version"

//--- Input parameters
input string   InpFeaturesFile = "features_bt.csv";     // Features output file
input string   InpPredictionsFile = "prediction_bt.txt"; // Predictions input file
input int      InpMagicNumber = 12345;                   // Magic number
input double   InpLotSize = 0.1;                        // Lot size
input int      InpSlippage = 3;                         // Slippage in points
input bool     InpUseStopLoss = true;                   // Use Stop Loss
input int      InpStopLoss = 50;                        // Stop Loss in points
input bool     InpUseTakeProfit = true;                 // Use Take Profit
input int      InpTakeProfit = 100;                     // Take Profit in points
input int      InpMaxPositions = 1;                     // Maximum positions
input bool     InpEnableLogging = true;                 // Enable detailed logging

//--- Global variables
datetime g_lastBarTime = 0;
string g_lastSignal = "";
datetime g_lastSignalTime = 0;
int g_featuresHandle = INVALID_HANDLE;
int g_predictionHandle = INVALID_HANDLE;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== MT5 Python Bridge EA v2.0 Started ===");
    Print("Features file: ", InpFeaturesFile);
    Print("Predictions file: ", InpPredictionsFile);
    Print("Magic number: ", InpMagicNumber);
    Print("Lot size: ", InpLotSize);
    
    // Validate input parameters
    if(InpLotSize <= 0)
    {
        Print("ERROR: Invalid lot size");
        return INIT_PARAMETERS_INCORRECT;
    }
    
    if(InpMagicNumber <= 0)
    {
        Print("ERROR: Invalid magic number");
        return INIT_PARAMETERS_INCORRECT;
    }
    
    // Test file access
    if(!TestFileAccess())
    {
        Print("WARNING: File access test failed, but continuing...");
    }
    
    Print("=== Initialization completed successfully ===");
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== MT5 Python Bridge EA stopped ===");
    Print("Reason: ", reason);
    
    // Close any open file handles
    if(g_featuresHandle != INVALID_HANDLE)
    {
        FileClose(g_featuresHandle);
        g_featuresHandle = INVALID_HANDLE;
    }
    
    if(g_predictionHandle != INVALID_HANDLE)
    {
        FileClose(g_predictionHandle);
        g_predictionHandle = INVALID_HANDLE;
    }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Check for new bar
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(currentBarTime == g_lastBarTime)
        return;
        
    g_lastBarTime = currentBarTime;
    
    // Write features to file
    if(!WriteFeaturesToFile())
    {
        if(InpEnableLogging)
            Print("Failed to write features");
        return;
    }
    
    // Small delay to allow Python to process
    Sleep(100);
    
    // Read prediction from file
    string signal;
    datetime signalTime;
    
    if(ReadPredictionFromFile(signal, signalTime))
    {
        ProcessSignal(signal, signalTime);
    }
}

//+------------------------------------------------------------------+
//| Write current market features to CSV file                        |
//+------------------------------------------------------------------+
bool WriteFeaturesToFile()
{
    // Get current market data
    double close = iClose(_Symbol, PERIOD_CURRENT, 1);
    double ema = iMA(_Symbol, PERIOD_CURRENT, 14, 0, MODE_EMA, PRICE_CLOSE, 1);
    double atr = iATR(_Symbol, PERIOD_CURRENT, 14, 1);
    
    // Validate data
    if(close <= 0 || ema <= 0 || atr < 0)
    {
        Print("ERROR: Invalid market data - close:", close, " ema:", ema, " atr:", atr);
        return false;
    }
    
    // Format timestamp
    datetime barTime = iTime(_Symbol, PERIOD_CURRENT, 1);
    string timeStr = TimeToString(barTime, TIME_DATE|TIME_MINUTES);
    StringReplace(timeStr, ".", ".");  // Ensure dot separator
    
    // Format data line
    string dataLine = StringFormat("%s;%.5f;%.5f;%.5f\n", 
                                   timeStr, close, ema, atr);
    
    // Write to file (append mode)
    int handle = FileOpen(InpFeaturesFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot open features file for writing: ", GetLastError());
        return false;
    }
    
    // Move to end of file and write
    FileSeek(handle, 0, SEEK_END);
    uint bytesWritten = FileWriteString(handle, dataLine);
    FileFlush(handle);
    FileClose(handle);
    
    if(bytesWritten > 0)
    {
        if(InpEnableLogging)
            Print("✓ Features written: ", StringSubstr(dataLine, 0, 50), "...");
        return true;
    }
    else
    {
        Print("ERROR: Failed to write features data");
        return false;
    }
}

//+------------------------------------------------------------------+
//| Read prediction from Python bridge                               |
//+------------------------------------------------------------------+
bool ReadPredictionFromFile(string &signal, datetime &signalTime)
{
    signal = "";
    signalTime = 0;
    
    int handle = FileOpen(InpPredictionsFile, FILE_READ|FILE_TXT|FILE_ANSI);
    if(handle == INVALID_HANDLE)
    {
        // File may not exist yet - not an error
        return false;
    }
    
    // Read the last line
    string line = "";
    while(!FileIsEnding(handle))
    {
        line = FileReadString(handle);
    }
    FileClose(handle);
    
    if(StringLen(line) == 0)
        return false;
    
    // Parse signal line: "SIGNAL;TIMESTAMP"
    string parts[];
    int numParts = StringSplit(line, ';', parts);
    
    if(numParts < 2)
    {
        Print("ERROR: Invalid prediction format: ", line);
        return false;
    }
    
    signal = parts[0];
    
    // Parse timestamp
    string timeStr = parts[1];
    StringReplace(timeStr, ".", ".");
    signalTime = StringToTime(timeStr);
    
    if(InpEnableLogging)
        Print("✓ Read signal: ", signal, " for ", TimeToString(signalTime));
    
    return true;
}

//+------------------------------------------------------------------+
//| Process trading signal from Python                               |
//+------------------------------------------------------------------+
void ProcessSignal(string signal, datetime signalTime)
{
    // Avoid processing the same signal twice
    if(signal == g_lastSignal && signalTime == g_lastSignalTime)
        return;
        
    g_lastSignal = signal;
    g_lastSignalTime = signalTime;
    
    // Check if signal is recent (within last 2 minutes)
    if(TimeCurrent() - signalTime > 120)
    {
        if(InpEnableLogging)
            Print("Signal too old, ignoring: ", TimeToString(signalTime));
        return;
    }
    
    // Count current positions
    int currentPositions = CountPositions();
    
    if(signal == "BUY")
    {
        if(currentPositions < InpMaxPositions)
        {
            OpenBuyPosition();
        }
        else
        {
            Print("Max positions reached, skipping BUY signal");
        }
    }
    else if(signal == "SELL")
    {
        if(currentPositions < InpMaxPositions)
        {
            OpenSellPosition();
        }
        else
        {
            Print("Max positions reached, skipping SELL signal");
        }
    }
    else if(signal == "CLOSE_ALL")
    {
        CloseAllPositions();
    }
    // NONE signal - do nothing
}

//+------------------------------------------------------------------+
//| Open Buy Position                                                |
//+------------------------------------------------------------------+
void OpenBuyPosition()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = InpUseStopLoss ? ask - InpStopLoss * _Point : 0;
    double tp = InpUseTakeProfit ? ask + InpTakeProfit * _Point : 0;
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.deviation = InpSlippage;
    request.magic = InpMagicNumber;
    request.comment = "Python ML Signal";
    
    if(OrderSend(request, result))
    {
        Print("🔵 BUY order opened: ticket=", result.order, " price=", result.price);
    }
    else
    {
        Print("ERROR: Failed to open BUY position: ", result.retcode, " - ", result.comment);
    }
}

//+------------------------------------------------------------------+
//| Open Sell Position                                               |
//+------------------------------------------------------------------+
void OpenSellPosition()
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = InpUseStopLoss ? bid + InpStopLoss * _Point : 0;
    double tp = InpUseTakeProfit ? bid - InpTakeProfit * _Point : 0;
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.deviation = InpSlippage;
    request.magic = InpMagicNumber;
    request.comment = "Python ML Signal";
    
    if(OrderSend(request, result))
    {
        Print("🔴 SELL order opened: ticket=", result.order, " price=", result.price);
    }
    else
    {
        Print("ERROR: Failed to open SELL position: ", result.retcode, " - ", result.comment);
    }
}

//+------------------------------------------------------------------+
//| Count current positions                                          |
//+------------------------------------------------------------------+
int CountPositions()
{
    int count = 0;
    for(int i = 0; i < PositionsTotal(); i++)
    {
        if(PositionSelectByIndex(i))
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
//| Close all positions                                              |
//+------------------------------------------------------------------+
void CloseAllPositions()
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        if(PositionSelectByIndex(i))
        {
            if(PositionGetString(POSITION_SYMBOL) == _Symbol && 
               PositionGetInteger(POSITION_MAGIC) == InpMagicNumber)
            {
                ulong ticket = PositionGetInteger(POSITION_TICKET);
                
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
                request.deviation = InpSlippage;
                request.magic = InpMagicNumber;
                request.position = ticket;
                request.comment = "Python Close Signal";
                
                if(OrderSend(request, result))
                {
                    Print("✓ Position closed: ticket=", ticket);
                }
                else
                {
                    Print("ERROR: Failed to close position ", ticket, ": ", result.retcode);
                }
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Test file access capabilities                                    |
//+------------------------------------------------------------------+
bool TestFileAccess()
{
    // Test writing features file
    int handle = FileOpen(InpFeaturesFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
    if(handle == INVALID_HANDLE)
    {
        Print("ERROR: Cannot create features file: ", GetLastError());
        return false;
    }
    
    string testLine = "2024.01.01 00:00;1.0000;1.0000;0.0010\n";
    FileWriteString(handle, testLine);
    FileClose(handle);
    
    // Test reading predictions file (may not exist yet)
    handle = FileOpen(InpPredictionsFile, FILE_READ|FILE_TXT|FILE_ANSI);
    if(handle != INVALID_HANDLE)
    {
        FileClose(handle);
        Print("✓ Predictions file accessible");
    }
    else
    {
        Print("INFO: Predictions file not found (will be created by Python)");
    }
    
    Print("✓ File access test completed");
    return true;
}

//+------------------------------------------------------------------+
//| Get current spread in points                                     |
//+------------------------------------------------------------------+
int GetCurrentSpread()
{
    return (int)((SymbolInfoDouble(_Symbol, SYMBOL_ASK) - 
                  SymbolInfoDouble(_Symbol, SYMBOL_BID)) / _Point);
}

//+------------------------------------------------------------------+
//| Check if trading is allowed                                      |
//+------------------------------------------------------------------+
bool IsTradingAllowed()
{
    if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
    {
        Print("ERROR: Trading is not allowed in terminal");
        return false;
    }
    
    if(!MQLInfoInteger(MQL_TRADE_ALLOWED))
    {
        Print("ERROR: Trading is not allowed for EA");
        return false;
    }
    
    if(!SymbolInfoInteger(_Symbol, SYMBOL_TRADE_MODE))
    {
        Print("ERROR: Trading is not allowed for symbol ", _Symbol);
        return false;
    }
    
    return true;
}

//+------------------------------------------------------------------+
//| Enhanced error handling for file operations                      |
//+------------------------------------------------------------------+
string GetFileErrorDescription(int errorCode)
{
    switch(errorCode)
    {
        case 5001: return "File not found";
        case 5002: return "File cannot be opened";
        case 5003: return "File cannot be written";
        case 5004: return "File cannot be read";
        case 5005: return "File cannot be deleted";
        case 5006: return "Invalid file handle";
        case 5007: return "File end reached";
        default:   return "Unknown file error: " + IntegerToString(errorCode);
    }
}

//+------------------------------------------------------------------+
//| Timer function for periodic tasks                                |
//+------------------------------------------------------------------+
void OnTimer()
{
    // Periodic cleanup or maintenance tasks can be added here
    static datetime lastCleanup = 0;
    
    if(TimeCurrent() - lastCleanup > 3600) // Every hour
    {
        // Clean up old log entries or perform maintenance
        lastCleanup = TimeCurrent();
        Print("INFO: Periodic maintenance completed");
    }
}

//+------------------------------------------------------------------+
//| Chart event handler                                              |
//+------------------------------------------------------------------+
void OnChartEvent(const int id,
                  const long &lparam,
                  const double &dparam,
                  const string &sparam)
{
    // Handle chart events if needed
    if(id == CHARTEVENT_KEYDOWN)
    {
        if(lparam == 27) // ESC key
        {
            Print("INFO: ESC pressed - EA status check");
            Print("Current positions: ", CountPositions());
            Print("Last signal: ", g_lastSignal, " at ", TimeToString(g_lastSignalTime));
        }
    }
}