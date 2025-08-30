//+------------------------------------------------------------------+
//|                                              MT5_Backtest_EA.mq5 |
//|                                  Copyright 2024, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, MetaQuotes Ltd."
#property link      "https://www.mql5.com"
#property version   "1.00"
#property description "EA для бэктестинга стратегии Python Bridge в Strategy Tester"

//--- Input parameters
input int      InpMagicNumber = 12345;        // Magic number
input double   InpLotSize = 0.1;              // Lot size
input int      InpStopLoss = 50;              // Stop Loss in points
input int      InpTakeProfit = 100;           // Take Profit in points
input int      InpEMAPeriod = 14;             // EMA Period
input int      InpATRPeriod = 14;             // ATR Period
input double   InpBuyThreshold = 1.001;      // Buy threshold (close > ema * threshold)
input double   InpSellThreshold = 0.999;     // Sell threshold (close < ema * threshold)
input double   InpMinDifference = 0.01;      // Minimum price difference
input bool     InpEnableLogging = false;     // Enable logging (отключено для скорости)

//--- Global variables
datetime g_lastBarTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    Print("=== MT5 Backtest EA Started ===");
    Print("Strategy: EMA + ATR Signal Generation");
    Print("EMA Period: ", InpEMAPeriod);
    Print("ATR Period: ", InpATRPeriod);
    Print("Lot Size: ", InpLotSize);
    Print("Stop Loss: ", InpStopLoss, " points");
    Print("Take Profit: ", InpTakeProfit, " points");
    
    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    Print("=== MT5 Backtest EA Finished ===");
    Print("Final Balance: $", AccountInfoDouble(ACCOUNT_BALANCE));
    Print("Total Profit: $", AccountInfoDouble(ACCOUNT_PROFIT));
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    // Работаем только на новых барах
    datetime currentBarTime = iTime(_Symbol, PERIOD_CURRENT, 0);
    if(currentBarTime == g_lastBarTime)
        return;
        
    g_lastBarTime = currentBarTime;
    
    // Получаем данные
    double close = iClose(_Symbol, PERIOD_CURRENT, 1);
    double ema = iMA(_Symbol, PERIOD_CURRENT, InpEMAPeriod, 0, MODE_EMA, PRICE_CLOSE);
    double atr = iATR(_Symbol, PERIOD_CURRENT, InpATRPeriod);
    
    // Проверяем валидность данных
    if(close <= 0 || ema <= 0 || atr <= 0)
        return;
    
    // Генерируем сигнал (ваша логика)
    string signal = GenerateSignal(close, ema);
    
    if(InpEnableLogging)
    {
        string timeStr = TimeToString(currentBarTime, TIME_DATE|TIME_MINUTES);
        Print(timeStr, " close=", close, " ema=", ema, " atr=", atr, " signal=", signal);
    }
    
    // Обрабатываем сигнал
    ProcessSignal(signal, close);
}

//+------------------------------------------------------------------+
//| Generate trading signal (ваша логика из Python)                 |
//+------------------------------------------------------------------+
string GenerateSignal(double close, double ema)
{
    // Точно ваша логика из Python
    if(MathAbs(close - ema) < InpMinDifference)
        return "NONE";
        
    if(close > ema * InpBuyThreshold)
        return "BUY";
    else if(close < ema * InpSellThreshold)
        return "SELL";
        
    return "NONE";
}

//+------------------------------------------------------------------+
//| Process trading signal                                           |
//+------------------------------------------------------------------+
void ProcessSignal(string signal, double currentPrice)
{
    // Проверяем есть ли открытые позиции
    int positions = CountPositions();
    
    if(signal == "BUY" && positions == 0)
    {
        OpenBuyPosition(currentPrice);
    }
    else if(signal == "SELL" && positions == 0)
    {
        OpenSellPosition(currentPrice);
    }
}

//+------------------------------------------------------------------+
//| Open Buy Position                                                |
//+------------------------------------------------------------------+
void OpenBuyPosition(double price)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double sl = ask - InpStopLoss * _Point;
    double tp = ask + InpTakeProfit * _Point;
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_BUY;
    request.price = ask;
    request.sl = sl;
    request.tp = tp;
    request.magic = InpMagicNumber;
    request.comment = "Backtest BUY";
    
    if(OrderSend(request, result))
    {
        if(InpEnableLogging)
            Print("🔵 BUY opened: ticket=", result.order, " price=", result.price);
    }
    else
    {
        Print("ERROR: BUY failed: ", result.retcode);
    }
}

//+------------------------------------------------------------------+
//| Open Sell Position                                               |
//+------------------------------------------------------------------+
void OpenSellPosition(double price)
{
    MqlTradeRequest request = {};
    MqlTradeResult result = {};
    
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
    double sl = bid + InpStopLoss * _Point;
    double tp = bid - InpTakeProfit * _Point;
    
    request.action = TRADE_ACTION_DEAL;
    request.symbol = _Symbol;
    request.volume = InpLotSize;
    request.type = ORDER_TYPE_SELL;
    request.price = bid;
    request.sl = sl;
    request.tp = tp;
    request.magic = InpMagicNumber;
    request.comment = "Backtest SELL";
    
    if(OrderSend(request, result))
    {
        if(InpEnableLogging)
            Print("🔴 SELL opened: ticket=", result.order, " price=", result.price);
    }
    else
    {
        Print("ERROR: SELL failed: ", result.retcode);
    }
}

//+------------------------------------------------------------------+
//| Count current positions                                          |
//+------------------------------------------------------------------+
int CountPositions()
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
```

## 🎯 **ДВА ВАРИАНТА ТЕСТИРОВАНИЯ:**

### **🚀 ВАРИАНТ 1: Быстрый Python тест**
```cmd
cd "C:\Users\AdmVps\AppData\Roaming\MetaQuotes\Terminal\Common\Files\python_bridge"
python quick_backtest.py
```

### **📊 ВАРИАНТ 2: Полный тест в MT5 Strategy Tester**

1. **Скопируйте код EA выше** в новый файл MetaEditor
2. **Сохраните как**: `MT5_Backtest_EA.mq5`
3. **Компилируйте** (F7)
4. **В MT5**: View → Strategy Tester
5. **Настройте**:
   - Expert: MT5_Backtest_EA
   - Symbol: EURUSD
   - Period: M1 или M5
   - Dates: последний месяц
6. **Start**

## 🎪 **КАКОЙ ТЕСТ ЗАПУСТИМ?**

**Рекомендую начать с быстрого Python теста:**
```cmd
python quick_backtest.py
```

Он покажет результаты за 30 секунд! 🚀

Какой вариант выберете? 🤔