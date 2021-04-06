import os, json, re
import time, datetime, signal
from urllib.parse import urlparse

from concurrent.futures import ThreadPoolExecutor
from threading import BoundedSemaphore

from kafka import KafkaProducer, KafkaConsumer
import psycopg2

#  ____  _                             
# / ___|| |_ ___  _ __ __ _  __ _  ___ 
# \___ \| __/ _ \| '__/ _` |/ _` |/ _ \
#  ___) | || (_) | | | (_| | (_| |  __/
# |____/ \__\___/|_|  \__,_|\__, |\___|
#                           |___/      
#  _        _                    _            
# | |_  ___| |_ __  ___ _ _   __| |__ _ ______
# | ' \/ -_) | '_ \/ -_) '_| / _| / _` (_-<_-<
# |_||_\___|_| .__/\___|_|   \__|_\__,_/__/__/
#            |_|                              
class Storage:
  """
  Handles tools for response time measurement and metrics forwarding to Kafka topic
  """

  def __init__(self):
    """
    Quite empty constructor
    """
    pass


  def setup_consumer(self, kafka_servers_string):
    """
    Sets up Kafka consumer, and keeps its reference in self property
    kafka_servers_string: str
      The kafka servers string, to connect to

    Returns a ref to consumer, or None on error
    """
    try:
      self.consumer = KafkaConsumer(
        'url-check.metrics',
        auto_offset_reset='earliest',
        group_id='check_url_group',
        enable_auto_commit=True,
        bootstrap_servers=kafka_servers_string,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        security_protocol='SSL',
        ssl_check_hostname=True,
        ssl_cafile='ca.pem',
        ssl_certfile='service.cert',
        ssl_keyfile='service.key'
      ) 
    except Exception as e:
      self.send_error_to_DLQ({'step':'storage.setup_consumer', 'error':'Could not instanciate Storage helper kafka consumer', 'exception':e})
      return None

    return self.consumer


  def setup_producer(self, kafka_servers_string):
    """
    Sets up Kafka producer, and keeps its reference in self property
    kafka_servers_string: str
      The kafka servers string, to connect to

    Returns a ref to producer, or None on error
    """
    try:
      self.producer = KafkaProducer(
        bootstrap_servers=kafka_servers_string,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        security_protocol='SSL',
        ssl_check_hostname=True,
        ssl_cafile='ca.pem',
        ssl_certfile='service.cert',
        ssl_keyfile='service.key'
      ) 
    except Exception as e:
      self.send_error_to_DLQ({'step':'storage.setup_producer', 'error':'Could not instanciate Storage helper kafka producer', 'exception':e})
      return None

    return self.producer


  def setup_database_connection(self, user, password, host, port):
    # Craft DSN from env variables
    # and then store ref to db and cursor as attribute
    try:

      self.pgdb = psycopg2.connect(
        host=host,
        port=port,
        database="check_url_metrics",
        user=user,
        password=password
      )
      self.dbcursor=self.pgdb.cursor()

    except Exception as e:
      self.send_error_to_DLQ({'step':'storage.setup_producer', 'error':'Could not connect to postgres DB', 'exception':e})
      return None

    return self.dbcursor


  def record_metric_to_db(self, messagein):
    """
    Records metric line to database
      messagein: object
        the metrics string to record to database
    """
    print(messagein)
    request_to_prepare="""
    INSERT INTO public.check_url_metrics(logdate, logtime, url, targetip, sourceip, statuscode, resptimems, regexfound) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
      if(messagein['regexfound'] is not None and messagein['regexfound'] == 'N/A'):
        messagein['regexfound']=None
    #     messagein['status_code']=messagein['statuscode']

      data= (
        messagein['logdate'],
        messagein['logtime'],
        messagein['url'],
        messagein['targetip'],
        messagein['sourceip'],
        messagein['status_code'],
        messagein['resptimems'],
        messagein['regexfound']
      )

      self.dbcursor.execute(request_to_prepare, data)
      self.pgdb.commit()

    except Exception as error:
      print(error)


  def start_consuming_loop(self):
    """
    Start consuming loop
    Is a blocking process
    """
    try:
      for message in self.consumer:
        self.record_metric_to_db(message.value)
    except Exception as error:
      print(error)
      exit(1)

    exit(0)


  def stop_consuming_loop(self):
    """
    Stop loop and close cleanly
    """
    print("Closing", self.consumer, self.pgdb)
    self.pgdb.close()
    return self.consumer.close()


  def send_error_to_DLQ(self, error_jsonizable_object):
    """
    Sends a message to DLQ topic
      error_jsonizable_object : any json serializable object

    Returns a reference to send result, None otherwise
    """
    try:
      sendRes = self.producer.send('url-check.DLQ', error_jsonizable_object)
      print('Sent message to DLQ : ' + error_jsonizable_object['error'])
      return sendRes
    except:
      return None


#     _      _                 
#  __(_)__ _| |_ ___ _ _ _ __  
# (_-< / _` |  _/ -_) '_| '  \ 
# /__/_\__, |\__\___|_| |_|_|_|
#      |___/                   
# Custom system signal handling for sys kill interrutions
class ProgramKilled(Exception):
    pass

def signal_handler(signum, frame):
    raise ProgramKilled

#                  _       
#  _ __ ___   __ _(_)_ __  
# | '_ ` _ \ / _` | | '_ \ 
# | | | | | | (_| | | | | |
# |_| |_| |_|\__,_|_|_| |_|

if(__name__) == '__main__':
  # Check that we got our env vars set and save resources on error
  if not "WORKERS_COUNT" in os.environ or not "CHECK_KAFKA_SERVERS" in os.environ or not "CHECK_PG_USER" in os.environ or not "CHECK_PG_PASSWORD" in os.environ or not "CHECK_PG_HOST" in os.environ or not "CHECK_PG_PORT" in os.environ :
    print("Some env vars are missing")
    exit(1)

  env_workers_count=int(os.environ['WORKERS_COUNT'])

  # Catch system calls and allow clean shutdown
  signal.signal(signal.SIGTERM, signal_handler)
  signal.signal(signal.SIGINT, signal_handler)

  try:
    # Setup PoolExecutor and useful vars
    executor = ThreadPoolExecutor(max_workers=env_workers_count)
    instances = []
    tasks = []

    # Instanciate as many times as wanted workers
    for i in range(env_workers_count):
      print('Setting up worker #',i)

      # Instanciate
      instances.append( Storage() )
      if(instances[i] is None):
        raise RuntimeError("Could not instanciate Storage tool")

      # Then setup kafka consumer
      if(instances[i].setup_consumer(os.environ['CHECK_KAFKA_SERVERS']) is None):
        print("Could not instanciate Storage tool's kafka consumer")
        raise RuntimeError("Could not instanciate Storage tool's kafka consumer")

      # Then setup kafka producer for DLQ
      if(instances[i].setup_producer(os.environ['CHECK_KAFKA_SERVERS']) is None):
        raise RuntimeError("Could not instanciate Storage tool's kafka producer")

      # Then setup connection to pgsql
      if(instances[i].setup_database_connection(os.environ['CHECK_PG_USER'], os.environ['CHECK_PG_PASSWORD'], os.environ['CHECK_PG_HOST'], os.environ['CHECK_PG_PORT']) is None):
        raise RuntimeError("Could not initiate Storage tool's postgres connection")

      # Finally, spawn a consumer loop
      tasks.append(executor.submit(instances[i].start_consuming_loop))
      print(tasks[i])

  except ProgramKilled:
    # Caught system interrupt, stop loop
    print("Killing, please wait for clean shutdown")
    executor.shutdown(wait=False)

    time.sleep(2)
    exit(0)

  except Exception as error:
    print(error)
    time.sleep(2)
    # No need to wait for clean shutdown, error was internal
    exit(1)