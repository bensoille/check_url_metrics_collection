import unittest
import pytest
from mock import patch
from measurement import Measurement

class TestMeasurement(unittest.TestCase):

  # Class should instantiate correctly when all is ok
  def test_instanciate_ok(self):
    classinst = Measurement("http://example.com", 5)
    self.assertIsInstance(classinst, Measurement, "result is not an instance of Measurement class")


  # Class should instantiate correctly when url proto is missing
  def test_instanciate_ok_not_so_badurl(self):
    classinst = Measurement("example.com", 5)
    self.assertIsInstance(classinst, Measurement, "result is not an instance of Measurement class")


  # Should return None on first try when URL is invalid
  @patch('requests.get')
  def test_instanciate_nok_badurl(self, mock_requests):
    classinst = Measurement("example com", 5)
    mock_requests.return_value = None
    
    ret = classinst.get_url_response_time()
    self.assertEqual(None, ret, "Bad URL given, failed")


  # Should be giving results with correct http response
  @patch('requests.get')
  def test_get_url_response_time_ok(self, mock_requests):
    # Mock correct response
    classinst = Measurement("http://example.com", 5)
    mock_requests.return_value.status_code = 200
    mock_requests.return_value.headers = {'Date': 'Wed, 31 Mar 2021 08:47:43 GMT'}
    mock_requests.return_value.text = "Mocked request response"
    
    ret = classinst.get_url_response_time()

    metricsDict = dict()
    metricsDict['url']          = "http://example.com"
    metricsDict['status_code']  = 200
    metricsDict['receivedtext'] = "Mocked request response"

    # do not use assertDictContainsSubset, deprecated
    self.assertEqual(dict(ret, **metricsDict), ret, "Wrong return from mock")
    self.assertIn("resptimems", ret, "No response time measurement in return from function when return code == 200")


  # Should be giving results event with error http response
  @patch('requests.get')
  def test_get_url_response_time_almostok(self, mock_requests):
    # Mock correct response
    classinst = Measurement("http://example.com", 5)
    mock_requests.return_value.status_code = 503
    mock_requests.return_value.headers = {'Date': 'Wed, 31 Mar 2021 08:47:43 GMT'}
    mock_requests.return_value.text = "Mocked request response gateway timeout"
    
    ret = classinst.get_url_response_time()

    metricsDict = dict()
    metricsDict['url']          = "http://example.com"
    metricsDict['status_code']  = 503
    metricsDict['receivedtext'] = "Mocked request response gateway timeout"

    # do not use assertDictContainsSubset, deprecated
    self.assertEqual(dict(ret, **metricsDict), ret, "Wrong return from mock")
    self.assertIn("resptimems", ret, "No response time measurement in return from function when return code != 200")


  # Should be returning None when Kafka Producer cannot get set up
  @patch('kafka.KafkaProducer', side_effect=Exception("Test error"))
  def test_setup_producer_get_none_if_producer_ko(self, mock_kafka_producer):

    classinst = Measurement("http://example.com", 5)
    prodRes = classinst.setup_producer('kafkaservers')
    self.assertEqual(prodRes, None, 'Should return None if producer cannot be set')


  # # Should call send with DLQ topic name argument
  # @patch('kafka.KafkaProducer')
  # @patch('requests.get')
  # def test_setup_producer_ok(self, mock_requests, mock_kafka_producer):

  #   classinst = Measurement("http://example.com", 5)
  #   prodRes = classinst.setup_producer('kafkaservers')

  #   print(prodRes)
  #   print(mock_kafka_producer.__class__.__name__)
  #   self.assertEqual(
  #     prodRes.__class__.__name__, 
  #     mock_kafka_producer.__class__.__name__,
  #     'Should return producer if ok'
  #   )


  def test_found_text_in_body_nothing(self):

    classinst = Measurement("http://example.com", 5, '^hop')
    found = classinst.found_text_in_body('fffhop')
    self.assertEqual(found, None, 'Should find nothing when looking up')

  def test_found_text_in_body_found(self):

    classinst = Measurement("http://example.com", 5, '^hop')
    found = classinst.found_text_in_body('hopffff')
    self.assertEqual(found, True, 'Should find text when looking up')

if __name__ == '__main__':
    unittest.main()