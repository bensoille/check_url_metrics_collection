# Check URL facility

This metrics collection facility is designed to : 
- periodically request some configured target URL
- measure round-trip time, until end of body contents reception
- store these metrics in some Postgres database

## The stack
This facility will leverage following services :
- Python as programming language, v3 is fine and leverage `ThreadPoolExecutor`
- Kafka for realtime messages distribution
- Postgres for collected metrics storage

## Required features
This facility is providing with :
- optional lookup for _regexped_ string in fetched target URL body contents
- computing of response times in _milliseconds_
- runtime errors warnings through some _DLQ topic_
- 
## Functional specifications
Simplified functional process can be represented with following schema :
![Simplified functional](assets/aiven_url_check_functional.png)

In addition to this (very) simplified functional workflow, this facility must enable :
- multiple producers : **multiple URL checkers** can be launched, both sending metrics to same data bus
- single consumer : **single DB storage process** is launched, which makes use **multiple workers**
- high throughput, thanks to DB insertion process threading
- configurability
  
## Technical specifications
### Consumer
Consumer is in charge of : 
- fetching remote target URL
- do the math about request chronology
- eventual string lookup in contents
- forward formatted metric string to Kafka topic
![Consumer functional](assets/aiven_url_check_consumer_functional.png)

### Producer
Producer is in charge of :
- checking metrics string 
- store this record in Postgres database
![Consumer functional](assets/aiven_url_check_producer_functional.png)
## How to

## Yet to be done
- 