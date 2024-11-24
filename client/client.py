import grpc
import service_pb2
import service_pb2_grpc
import yfinance as yf
import datetime
import random
import string
from time import sleep

session_email = None

def generate_request_id():
    """
    Genera un request_id univoco basato su timestamp e caratteri casuali.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d%H%M%S%f')
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    return f"{timestamp}_{random_str}"

def ticker_verifier(ticker):
    """
    Verifica se il ticker è valido utilizzando yfinance.
    """
    try:
        dati = yf.download(ticker, period="1d", progress=False)
        if not dati.empty:
            print(f"Il ticker '{ticker}' è valido.")
            return True
        else:
            print(f"Il ticker '{ticker}' non è valido.")
            return False
    except Exception as e:
        print(f"Errore durante la verifica del ticker: {e}")
        return False

def send_request_with_retry(stub_method, request, max_retries=5):
    """
    Funzione generica per inviare richieste con ritentativi utilizzando lo stesso request_id.
    """
    attempts = 0
    while attempts < max_retries:
        try:
            response = stub_method(request, timeout=5)  
            return response
        except grpc.RpcError as e:
            if e.code() in [grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNAVAILABLE]:
                attempts += 1
                print(f"Tentativo {attempts} di {max_retries} fallito. Riprovo...")
                sleep(5) 
            else:
                print(f"Errore durante la richiesta: {e}")
                break
    print("Impossibile contattare il server dopo diversi tentativi.")
    return None

def run():
    global session_email
    with grpc.insecure_channel('localhost:50051') as canale:
        stub = service_pb2_grpc.UserServiceStub(canale)
        while True:
            print("\n--- Menù di avvio ---")
            print("1. Login")
            print("2. Registrazione")
            print("3. Esci")
            scelta = input("Inserisci il numero dell'operazione desiderata: ")

            if scelta == '1':
                email = input("Inserisci la tua email: ")
                request = service_pb2.LoginUserRequest(email=email)
                response = send_request_with_retry(stub.LoginUser, request)
                if response and response.success:
                    print(response.message)
                    session_email = email
                    user_session(stub)
                elif response:
                    print(response.message)
                else:
                    print("Errore durante il login.")
            elif scelta == '2':
                email = input("Inserisci l'email dell'utente: ")
                ticker = input("Inserisci il ticker di interesse: ")
                if ticker_verifier(ticker):
                    request_id = generate_request_id()
                    request = service_pb2.RegisterUserRequest(email=email, ticker=ticker, request_id=request_id)
                    response = send_request_with_retry(stub.RegisterUser, request)
                    if response:
                        print(response.message)
                        if "success" in response.message.lower():
                            session_email = email
                            user_session(stub)
                    else:
                        print("Errore durante la registrazione.")
                else:
                    print("Ticker non valido. Registrazione annullata.")
            elif scelta == '3':
                print("Uscita dal programma... Alla prossima!")
                break
            else:
                print("Scelta non valida. Riprova.")


def user_session(stub):
    """
    Gestisce le operazioni utente dopo il login.
    """
    global session_email
    while True:
        print(f"\n--- BENVENUTO {session_email} ---")
        print("\nSeleziona un'operazione:")
        print("1. Aggiornamento Ticker")
        print("2. Cancellazione Account")
        print("3. Recupero dell'ultimo valore disponibile")
        print("4. Calcolo della media degli ultimi X valori")
        print("5. Logout")
        scelta = input("Inserisci il numero dell'operazione desiderata: ")

        if scelta == '1':
            ticker = input("Inserisci il nuovo ticker: ")
            if ticker_verifier(ticker):
                request_id = generate_request_id()
                request = service_pb2.UpdateUserRequest(
                    email=session_email,
                    ticker=ticker,
                    request_id=request_id
                )
                response = send_request_with_retry(stub.UpdateUser, request)
                if response:
                    print(response.message)
                else:
                    print("Errore durante l'aggiornamento del ticker.")
            else:
                print("Ticker non valido. Aggiornamento annullato.")
        elif scelta == '2':
            request_id = generate_request_id()
            request = service_pb2.DeleteUserRequest(email=session_email, request_id=request_id)
            response = send_request_with_retry(stub.DeleteUser, request)
            if response:
                print(response.message)
                if "cancellato" in response.message.lower():
                    session_email = None
                    print("Sei stato disconnesso.")
                    break
            else:
                print("Errore durante la cancellazione dell'account.")
        elif scelta == '3':
            request = service_pb2.GetLatestValueRequest(email=session_email)
            try:
                response = stub.GetLatestValue(request, timeout=5)  
                if response.ticker:
                    print(f"Ultimo valore per {response.ticker}: {response.value} (Timestamp: {response.timestamp})")
                else:
                    print("Nessun dato disponibile.")
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    print("Nessun valore disponibile. Potrebbe essere che il data collector non sia aggiornato.")
                else:
                    print(f"Errore durante il recupero dell'ultimo valore: {e.details()}")
        elif scelta == '4':
            try:
                count = int(input("Quanti valori vuoi considerare per la media? "))
                request = service_pb2.GetAverageValueRequest(email=session_email, count=count)
                response = None

                try:
                    response = stub.GetAverageValue(request, timeout=5)  
                    if response and response.ticker:
                        print(f"Valore medio per {response.ticker}: {response.average_value}")
                    elif response:
                        print("Nessun dato disponibile per l'utente specificato.")
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.NOT_FOUND:
                        print("Nessun valore disponibile. Potrebbe essere che il data collector non sia aggiornato.")
                    else:
                        print(f"Errore durante il calcolo della media: {e.details()}")

            except ValueError:
                print("Per favore, inserisci un numero intero valido.")


        elif scelta == '5':
            print("Logout effettuato.")
            session_email = None
            break
        else:
            print("Scelta non valida. Riprova.")

if __name__ == '__main__':
    run()
