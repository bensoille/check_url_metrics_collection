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
- single or multiple consumers : each consumer uses **multiple workers** for throughput configuration
- high throughput, thanks to DB insertion process threading
- configurability
  
## Technical specifications
### Producer : URL check
#### Synopsis
_Producer_ is in charge of : 
- fetching remote target URL
- do the math on request chronology
- eventual string lookup in contents
- forward formatted metric string to Kafka topic
![Producer functional](assets/aiven_url_check_producer_functional.png)

#### Configuration items
The URL checker process accepts following **editable** configuration items :
- *CHECK_TARGET_URL* : the URL to check, may be on *http* or *https* proto
- *CHECK_PERIOD_SECONDS* : the time between each check, in seconds
- *CHECK_CONTENTS_REGEX* (optional) : the regular expression to lookup text with, in body contents

In addition, some internal configuration items are needed :
- kafka topic to send metrics to
- kafka topic used for DLQ
- kafka credentials

### Consumer : metrics record storage
#### Synopsis
_Consumer_ is in charge of :
- subscription to kafka topic
- checking incoming metrics string 
- store this record in Postgres database via one of available workers
![Consumer functional](assets/aiven_url_check_consumer_functional.png)

#### Configuration items
The metrics storage process accepts following **editable** configuration items :
- *WORKERS_COUNT* : the maximum allowed numbers of workers

In addition,  some internal configuration items are needed :
- kafka topic to consume
- kafka topic used for DLQ
- kafka credentials
- Postgres DSN

### Kafka topics
#### Metrics topic
This topic is named `url-check.metrics`
Is used for high throughput of metrics data messages between processes. 
#### DLQ topic
This topic is named `url-check.DLQ`
Is used for error handling : any runtime error would send a useful message in. 

### Postgres metrics data structure
Metrics data strings are stored in Postgres DB, using a single (partitioned) table :
```sql
-- Extension: timescaledb

-- DROP EXTENSION timescaledb;

CREATE EXTENSION timescaledb
    SCHEMA public
    VERSION "2.1.0";

-- Table: public.check_url_metrics

-- DROP TABLE public.check_url_metrics;

CREATE TABLE public.check_url_metrics
(
    url text COLLATE pg_catalog."default" NOT NULL,
    logdate date NOT NULL,
    logtime time without time zone,
    targetip inet NOT NULL,
    sourceip inet NOT NULL,
    statuscode integer NOT NULL,
    resptimems double precision NOT NULL,
    regexfound boolean
)

TABLESPACE pg_default;

ALTER TABLE public.check_url_metrics
    OWNER to pguser;
```
With :
- url : the target URL to check
- targetip : the target reached IP address
- sourceip : the originating IP address 
- logdate/logtime : the date and time the test was launched
- statuscode : the returned HTTP status code
- resptimems : the measured request time, in milli seconds
- regexfound : true if text was found in response body, false otherwise, NULL if not configured in url fetcher (producer)
## How to
See [this readme page](../README.md)