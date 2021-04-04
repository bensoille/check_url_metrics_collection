import requests 
import time
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
      r = requests.get(self.url)
      # Response received tick
      inter = time.time_ns()

      statuscode = r.status_code
      receivedtext = r.text

    except :
      print("Should send message to DLQ")
      return None

    metricsDict = dict()
    metricsDict['url']          = self.url
    metricsDict['status_code']  = statuscode
    # Ticks were in ns : convert to ms
    metricsDict['resptimems']   = (inter - begin) / 1000000 
    metricsDict['receivedtext'] = receivedtext

    return metricsDict


if(__name__) == '__main__':
  instance = Measurement('http://soille.fr/hop.html', 5)
  print(instance.get_url_response_time())