import yfinance as yf
import time
from common.database import SessionLocal
from common.models import FinancialData, User
from circuit_breaker import CircuitBreaker
import logging

logging.getLogger('yfinance').setLevel(logging.CRITICAL)
def get_stock_price(ticker):
    data = yf.Ticker(ticker)
    hist = data.history(period="1d")
    if not hist.empty:
        return float(hist['Close'][0])  
    else:
        raise ValueError(f"Nessun dato trovato per il ticker: {ticker}")

def main():
    circuit_breaker = CircuitBreaker()
    while True:
        print("Avvio ciclo di raccolta dati")
        with SessionLocal() as session:
            tickers = session.query(User.ticker).distinct()
            tickers = [t[0] for t in tickers]
            for ticker in tickers:
                try:
                    price = circuit_breaker.call(get_stock_price, ticker)
                    price = float(price)
                    financial_data = FinancialData(
                        ticker=ticker,
                        value=price
                    )
                    session.add(financial_data)
                    session.commit()
                    print(f"Dato salvato per ticker {ticker}: {price}")
                except Exception as e:
                    print(f"Errore nel recupero dei dati per ticker {ticker}: {e}")
        print("Ciclo di raccolta dati completato, attesa 3 minuti")
        time.sleep(180)

if __name__ == '__main__':
    main()