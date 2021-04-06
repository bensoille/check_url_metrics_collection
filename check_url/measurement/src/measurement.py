import os, json, re
import time, threading, signal
from urllib.parse import urlparse

import requests 
from kafka import KafkaProducer


#  __  __                                                    _   
# |  \/  | ___  __ _ ___ _   _ _ __ ___ _ __ ___   ___ _ __ | |_ 
# | |\/| |/ _ \/ _` / __| | | | '__/ _ \ '_ ` _ \ / _ \ '_ \| __|
# | |  | |  __/ (_| \__ \ |_| | | |  __/ | | | | |  __/ | | | |_ 
# |_|  |_|\___|\__,_|___/\__,_|_|  \___|_| |_| |_|\___|_| |_|\__|
#  _        _                    _            
# | |_  ___| |_ __  ___ _ _   __| |__ _ ______
# | ' \/ -_) | '_ \/ -_) '_| / _| / _` (_-<_-<
# |_||_\___|_| .__/\___|_|   \__|_\__,_/__/__/
#            |_|                              
class Measurement:
  """
  Handles tools for response time measurement and metrics forwarding to Kafka topic
  """

  def __init__(self, url, period, contents_regexp=None):
    """
    Constructor sets up proerties from needed arguments :
    url: str
      The target URL to measure response time from
    period: int
      The time between 2 metrics, in seconds
    contents_regexp: str (optional)
      A regex string to use for text lookup in body
    """
    self.url = url
    self.period = period
    
    self.regexp = None
    if(contents_regexp):
      self.regexp = contents_regexp

    self.ticker = threading.Event()


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
    except:
      self.send_error_to_DLQ({'step':'measurement.__init__', 'error':'Could not instanciate Measurement helper kafka producer'})
      return None

    return self.producer


  def get_url_response_time(self):
    """
    Requests configured target URL 
    
    RETURNS metrics as a dict() :
    url: str
      The tested URL
    resptimems: float
      The response time, in milliseconds
    statuscode: int
      The response HTTP status code
    """
    try:
      # Beginning tick, then request
      begin = time.time_ns()
      #--------------------------------------------------
      r = requests.get(self.url, timeout=30, stream=True)
      #--------------------------------------------------
      # Response received tick
      inter = time.time_ns()

      # Store http request details
      if(r is not None):
        originip        = r.raw._original_response.fp.raw._sock.getsockname()[0]
        targetip        = r.raw._original_response.fp.raw._sock.getpeername()[0]
        statuscode      = r.status_code
        receivedtext    = r.text
      else:
        return r

    except :
      self.send_error_to_DLQ({'step':'measurement.get_url_response_time', 'error':'HTTP request had an error or data could not be extracted'})
      return None

    metricsDict = dict()
    metricsDict['url']          = self.url
    metricsDict['status_code']  = statuscode
    metricsDict['receivedtext'] = receivedtext
    metricsDict['targetip']     = targetip
    metricsDict['sourceip']     = originip
    metricsDict['logdate']      = r.headers['Date']
    # Ticks were in ns : convert to ms
    metricsDict['resptimems']   = (inter - begin) / 1000000 
    # Lookup text only if regex was given at instanciation time
    if(self.regexp is not None):
      metricsDict['regexfound'] = self.found_text_in_body(receivedtext)

    return metricsDict


  def found_text_in_body(self, text_to_search_in):
    """
    Lookup text in body contents, using a regexp in a perl way
    text_to_search_in: str
      The string to search pattern in, aka the body contents

    Returns None if NOT found, True if found
    """
    if(re.search(self.regexp, text_to_search_in) is not None):
      return True
    return None


  def start_periodic_requests(self):
    """
    Starts periodic requests loop, using config values from env variables.
    See method stop_periodic_requests for loop stop

    Returns None on error, is blocking otherwise
    """
    while not self.ticker.wait(self.period):
      #-----------------------------------------
      metrics = instance.get_url_response_time()
      #-----------------------------------------

      if(metrics is None):
        self.send_error_to_DLQ({'step':'measurement.start_periodic_requests', 'error':'HTTP request returned None'})
        # TODO should quit or not ?? Not specified
        return self.stop_periodic_requests()
        
      try:
        self.producer.send('url-check.metrics', metrics)
        print(metrics['logdate'] + ' : Sent message to Kafka')
      except:
        self.send_error_to_DLQ({'step':'measurement.start_periodic_requests', 'error':'Could not push message to Kafka', 'metrics':metrics})
        return self.stop_periodic_requests()


  def stop_periodic_requests(self):
    """
    Stops periodic requests loop, previously started with start_periodic_requests

    Returns None
    """    
    self.ticker.clear()
    return None
    

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
      return self.stop_periodic_requests()


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
  if not "CHECK_TARGET_URL" in os.environ or not "CHECK_PERIOD_SECONDS" in os.environ or not "CHECK_KAFKA_SERVERS" in os.environ :
    print("Some env vars are missing")
    exit(1)

  # Catch system calls and allow clean shutdown
  signal.signal(signal.SIGTERM, signal_handler)
  signal.signal(signal.SIGINT, signal_handler)

  try:
    instance = Measurement(
      os.environ['CHECK_TARGET_URL'], 
      int(os.environ['CHECK_PERIOD_SECONDS'])
    )
    if(instance is None):
      raise RuntimeError("Could not instanciate Measurement tool")

    producer = instance.setup_producer(os.environ['CHECK_KAFKA_SERVERS'])
    if(producer is None):
      raise RuntimeError("Could not instanciate Measurement tool's kafka producer")

    instance.start_periodic_requests()

  except ProgramKilled:
    # Caught system interrupt, stop loop
    print("Killing, please wait for clean shutdown")
    instance.stop_periodic_requests()
    # Wait a couple of seconds and exit with success return code
    time.sleep(2)
    exit(0)

  except:
    # No need to wait for clean shutdown, error was internal
    exit(1)