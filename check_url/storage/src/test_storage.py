import unittest
import pytest
from mock import patch
from storage import Storage

class TestStorage(unittest.TestCase):

  # Class should instantiate correctly when all is ok
  def test_instanciate_ok(self):
    classinst = Storage()
    self.assertIsInstance(classinst, Storage, "result is not an instance of Storage class")


  # Instanciation should return None if KafkaConsumer is error
  @patch('kafka.KafkaConsumer', side_effect=Exception("Test error"))
  def test_setup_consumer_ko(self, mock_kafka_consumer):

    classinst = Storage()
    prodRes = classinst.setup_consumer('kafkaservers')

    print(prodRes)
    self.assertIsNone(
      prodRes,
      'Should return None if consumer is ko'
    )


  # Instanciation should return None if KafkaProducer is error
  @patch('kafka.KafkaProducer', side_effect=Exception("Test error"))
  def test_setup_producer_ko(self, mock_kafka_consumer):

    classinst = Storage()
    prodRes = classinst.setup_producer('kafkaservers')

    print(prodRes)
    self.assertIsNone(
      prodRes,
      'Should return None if producer is ko'
    )    

  # Instanciation should return None if db connect is error
  @patch('psycopg2.connect', side_effect=Exception("Test error"))
  def test_setup_database_connection_ko(self, mock_kafka_consumer):

    classinst = Storage()
    prodRes = classinst.setup_database_connection('user', 'pass', 'host', 'port')

    print(prodRes)
    self.assertIsNone(
      prodRes,
      'Should return None if connection to postgres db is ko'
    )      


if __name__ == '__main__':
    unittest.main()