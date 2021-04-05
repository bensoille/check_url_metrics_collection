import os
import requests 
import time, threading, signal
from urllib.parse import urlparse

class Measurement:
  """
  Handles tools for response time measurement
  """

  def __init__(self, url, period):
    """
    Constructor sets up proerties from needed arguments :
    url: str
      The target URL to measure response time from
    period: int
      The time between 2 metrics, in seconds
    """
    self.url = url
    self.period = period
    #self.originip = os.environ['']


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
      r = requests.get(self.url, timeout=30, stream=True)
      # Response received tick
      inter = time.time_ns()

      # Store http request details
      originip        = r.raw._original_response.fp.raw._sock.getsockname()[0]
      targetip        = r.raw._original_response.fp.raw._sock.getpeername()[0]
      statuscode      = r.status_code
      receivedtext    = r.text

    except :
      print("Should send message to DLQ")
      return None

    metricsDict = dict()
    metricsDict['url']          = self.url
    metricsDict['status_code']  = statuscode
    # Ticks were in ns : convert to ms
    metricsDict['resptimems']   = (inter - begin) / 1000000 
    metricsDict['receivedtext'] = receivedtext
    metricsDict['targetip']     = targetip
    metricsDict['sourceip']     = originip
    metricsDict['logdate']      = r.headers['Date']
    return metricsDict


  def start_periodic_requests(self):
    """
    Starts periodic requests loop, using config values from env variables.
    See method stop_periodic_requests for loop stop
    """
    self.ticker = threading.Event()
    while not self.ticker.wait(self.period):
      metrics = instance.get_url_response_time()
      print(metrics)


  def stop_periodic_requests(self):
    """
    Stops periodic requests loop, previously started with start_periodic_requests
    """    
    self.ticker.clear()


# Custom error for sys kill interrutions
class ProgramKilled(Exception):
    pass

def signal_handler(signum, frame):
    raise ProgramKilled


if(__name__) == '__main__':
  # Check that we got our env vars set and save resources on error
  if not "CHECK_TARGET_URL" in os.environ or not "CHECK_PERIOD_SECONDS" in os.environ :
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
    instance.start_periodic_requests()

  except ProgramKilled:
    # Caught system interrupt, stop loop
    print("Killing, please wait for clean shutdown")
    instance.stop_periodic_requests()
    # Wait a couple of seconds and exit with success return code
    time.sleep(2)
    exit(0)