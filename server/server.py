from concurrent import futures
import grpc
import time
import re
import threading
from cachetools import TTLCache
import logging
from common.database import SessionLocal, engine
from common import models
import service_pb2
import service_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

class UserService(service_pb2_grpc.UserServiceServicer):
    def __init__(self):
        self.request_cache = TTLCache(maxsize=10000, ttl=600)  
        self.cache_lock = threading.Lock()

    def is_valid_email(self, email):
        regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return re.match(regex, email) is not None

    def RegisterUser(self, request, context):
        if not request.request_id:
            context.set_details("Non esiste nessun request id in cache per questa richiesta")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return service_pb2.RegisterUserResponse()


        with self.cache_lock:
            if request.request_id in self.request_cache:
                logger.info(f"Ho trovato una richiesta con request id duplicato: {request.request_id}")
                message = self.request_cache[request.request_id]
                return service_pb2.RegisterUserResponse(message=message)


        if not self.is_valid_email(request.email):
            logger.info(f"Formato email non valido: {request.email}")
            message = "Formato email non valido."
            with self.cache_lock:
                self.request_cache[request.request_id] = message
            return service_pb2.RegisterUserResponse(message=message)

        session = SessionLocal()
        try:
            existing_user = session.query(models.User).filter_by(email=request.email).first()
            if existing_user:
                message = "L'utente è già registrato!"
                logger.info(f"L'utente è già registrato!: {request.email}")
            else:
                new_user = models.User(email=request.email, ticker=request.ticker)
                session.add(new_user)
                session.commit()
                message = "Registrazione avvenuta con successo!"
                logger.info(f"User registered: {request.email}")
                
            with self.cache_lock:
                self.request_cache[request.request_id] = message

            return service_pb2.RegisterUserResponse(message=message)
        except Exception as e:
            session.rollback()
            logger.error(f"Errore nella registrazione utente: {e}")
            context.set_details(f'Error: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.RegisterUserResponse()
        finally:
            session.close()

    def UpdateUser(self, request, context):
        if not request.request_id:
            context.set_details("Non esiste nessun request id in cache per questa richiesta")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return service_pb2.UpdateUserResponse()

        with self.cache_lock:
            if request.request_id in self.request_cache:
                logger.info(f"Ho trovato una richiesta con request id duplicato: {request.request_id}")
                message = self.request_cache[request.request_id]
                return service_pb2.UpdateUserResponse(message=message)


        if not self.is_valid_email(request.email):
            logger.info(f"Formato email non valido: {request.email}")
            message = "Formato email non valido."
            with self.cache_lock:
                self.request_cache[request.request_id] = message
            return service_pb2.UpdateUserResponse(message=message)

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if user:
                if user.ticker == request.ticker:
                    message = "Il ticker è già settato a questo valore!"
                    logger.info(f"Il ticker è già settato a questo valore per l'utente: {request.email}")
                else:
                    user.ticker = request.ticker
                    session.commit()
                    message = "Utente aggiornato correttamente!"
                    logger.info(f"Utente aggiornato: {request.email}")
            else:
                message = "Utente non trovato."
                logger.info(f"Utente non trovato: {request.email}")

            with self.cache_lock:
                self.request_cache[request.request_id] = message

            return service_pb2.UpdateUserResponse(message=message)
        except Exception as e:
            session.rollback()
            logger.error(f"Errore nell'aggiornare l'utente: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.UpdateUserResponse()
        finally:
            session.close()

    def DeleteUser(self, request, context):

        if not request.request_id:
            context.set_details("Non esiste nessun request id in cache per questa richiesta")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            return service_pb2.DeleteUserResponse()

        with self.cache_lock:
            if request.request_id in self.request_cache:
                logger.info(f"Ho trovato una richiesta con request id duplicato: {request.request_id}")
                message = self.request_cache[request.request_id]
                return service_pb2.DeleteUserResponse(message=message)

        if not self.is_valid_email(request.email):
            logger.info(f"Formato email non valido: {request.email}")
            message = "Formato email non valido."
            with self.cache_lock:
                self.request_cache[request.request_id] = message
            return service_pb2.DeleteUserResponse(message=message)

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if user:
                session.delete(user)
                session.commit()
                message = "Utente cancellato correttamente"
                logger.info(f"Utente cancellato: {request.email}")
            else:
                message = "Utente non trovato"
                logger.info(f"Utente non trovato: {request.email}")

            with self.cache_lock:
                self.request_cache[request.request_id] = message

            return service_pb2.DeleteUserResponse(message=message)
        except Exception as e:
            session.rollback()
            logger.error(f"Errore nel cancellare l'utente: {e}")
            context.set_details(f'Error: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.DeleteUserResponse()
        finally:
            session.close()

    def LoginUser(self, request, context):
        """
        Gestisce il login dell'utente. Non modifica lo stato, quindi non richiede request_id.
        """
        if not self.is_valid_email(request.email):
            logger.info(f"Formato email non valido: {request.email}")
            return service_pb2.LoginUserResponse(message="Formato email non valido.", success=False)

        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if user:
                message = "Login avvenuto con successo!"
                logger.info(f"L'utente ha acceduto come: {request.email}")
                success = True
            else:
                message = "Utente non trovato!"
                logger.info(f"Utente non trovaot: {request.email}")
                success = False
            return service_pb2.LoginUserResponse(message=message, success=success)
        except Exception as e:
            logger.error(f"Errore nel login!: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.LoginUserResponse(message="Internal error.", success=False)
        finally:
            session.close()

    def GetLatestValue(self, request, context):
        """
        Recupera l'ultimo valore finanziario disponibile per l'utente.
        """
        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if not user:
                return service_pb2.GetLatestValueResponse(
                    email=request.email,
                    ticker="",
                    value=0.0,
                    timestamp=""
                )
            ticker = user.ticker
            latest_data = session.query(models.FinancialData)\
                .filter_by(ticker=ticker)\
                .order_by(models.FinancialData.timestamp.desc())\
                .first()
            if latest_data:
                return service_pb2.GetLatestValueResponse(
                    email=request.email,
                    ticker=latest_data.ticker,
                    value=latest_data.value,
                    timestamp=latest_data.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                )
            else:
                context.set_details(f"Nessun dato disponibile per il ticker: {ticker}. Il data collector potrebbe non essere aggiornato.")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return service_pb2.GetLatestValueResponse()
        except Exception as e:
            logger.error(f"Errore nel passare l'ultimo valore: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.GetLatestValueResponse()
        finally:
            session.close()

    def GetAverageValue(self, request, context):
        """
        Calcola la media degli ultimi X valori finanziari per l'utente.
        """
        session = SessionLocal()
        try:
            user = session.query(models.User).filter_by(email=request.email).first()
            if not user:
                context.set_details("Utente non trovato.")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return service_pb2.GetAverageValueResponse()

            ticker = user.ticker

            data = session.query(models.FinancialData)\
                .filter_by(ticker=ticker)\
                .order_by(models.FinancialData.timestamp.desc())\
                .limit(request.count)\
                .all()

            if data and len(data) > 0:
                average_value = sum(entry.value for entry in data) / len(data)
                return service_pb2.GetAverageValueResponse(
                    email=request.email,
                    ticker=ticker,
                    average_value=average_value
                )
            else:

                context.set_details(f"Nessun valore disponibile per il ticker: {ticker}. Il data collector potrebbe non essere aggiornato.")
                context.set_code(grpc.StatusCode.NOT_FOUND)
                return service_pb2.GetAverageValueResponse()
        except Exception as e:
            logger.error(f"Errore nel calcolare la media degli ultimi valori: {e}")
            context.set_details(f'Errore: {str(e)}')
            context.set_code(grpc.StatusCode.INTERNAL)
            return service_pb2.GetAverageValueResponse()
        finally:
            session.close()

def serve():
    """
    Avvia il server gRPC e lo mantiene in esecuzione.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    logger.info("gRPC Server sta funzionando nella porta 50051...")
    try:
        while True:
            time.sleep(86400) 
    except KeyboardInterrupt:
        server.stop(0)
        logger.info("Hai fermato il server gRPC")

if __name__ == '__main__':
    serve()
