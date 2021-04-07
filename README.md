# Collect and store URL check results
This is a system that monitors website availability over the network, produces metrics about this and passes these events through a Kafka instance into an PostgreSQL database.

# Documentation
Please see (WIP) specs in [documentation folder](documentation/README.md).

# Quick start
## Prerequisites
Only *docker* is needed to run this facility.

However, following configuration data will be required :
- Kafka  service
  - cert/key/CA files
  - servers hosts string
- postgresql service
  - username string (user must be allowed to access table)
  - password string
  - server host string
  - server port string

Finally, process can be configured with :
- URL checker : target URL and check period
- Metrics storage : number of workers to launch
## Prepare postgresql
> postgresql preparation step would be fully automatic soon, it's important that this facility does not use *admin* user...   
>   
### Create user
Create a user that has non-admin role, via *aiven* GUI or with *admin user*.      
This username will be passed as an argument on *docker run* time.   

> In instructions below we assume that this new username is *pguser*     

### Create schema and table
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
> *timescaledb* extension is activated, as this will help in our use case     

> From now on, *admin* user is NOT used anymore    
>  
## Build instructions
> Following commands should be issued when _PWD_ in _check\_url_ folder of sources

### Create Kafka topics
> This step would be fully automatic soon     

Before it's implemented, so far topics must be created in Kafka via *aiven* GUI :
- `url-check.metrics`
- `url-check.DLQ`

### Prepare Kafka credentials
> The Kafka certs files must be copied to the Dockerfile context.     

Copy the certs into a new _check\_url/certs_ folder ; it will be ignored by git.    
That way, docker images would be able to build with these (quite useful) files.
You'd end up with following files structure :
```
├── check_url
│   ├── certs
│   │   ├── ca.pem
│   │   ├── service.cert
│   │   └── service.key

```
### Build URL checker / producer
Build docker image (this step needs Kafka creds files as explained above) :
```bash
docker -D build -f measurement/Dockerfile -t ben_aiven/test_url_measurement .
```

### Build Metrics storage / consumer
Build docker image (this step needs Kafka creds files as explained above) :
```bash
docker -D build -f storage/Dockerfile -t ben_aiven/test_url_storage .
```

## Run it all
Components can be launched in any order, even if it's always smarter to start consumer first
### Metric storage / consumer
Run docker container with following command :
```bash
docker run -e WORKERS_COUNT=3 \
  -e CHECK_KAFKA_SERVERS='kafka-example.aivencloud.com:16031' \
  -e CHECK_PG_USER=pguser \
  -e CHECK_PG_PASSWORD=nonAdminUserPassword \
  -e CHECK_PG_HOST=pg-example-ben-1f9e.aivencloud.com \
  -e CHECK_PG_PORT=16029 \
  -it ben_aiven/test_url_storage
```
With :
- WORKERS_COUNT :       the number of consumer workers to start
- CHECK_KAFKA_SERVERS : the Kafka service URI, with appended port
- CHECK_PG_USER :       username of non-admin user
- CHECK_PG_PASSWORD :   password of non-admin user
- CHECK_PG_HOST :       database host URI
- CHECK_PG_PORT :       database host port

### URL checker / producer
Run docker container with following command :
```bash
docker run \
  -e CHECK_KAFKA_SERVERS='kafka-example.aivencloud.com:16031' \
  -e CHECK_PERIOD_SECONDS=60 \
  -e CHECK_TARGET_URL='http://soille.fr/hop.html' \
  -it ben_aiven/test_url_measurement
```
With :
- CHECK_KAFKA_SERVERS :   the Kafka service URI, with appended port
- CHECK_PERIOD_SECONDS :  time between checks, in seconds
- CHECK_TARGET_URL :      the URL to check after

# Yet to be done
- **Handle consumer sigterm correctly...**
- provide with automated bootstrap (create user, table in pg and topics in kafka)
- use logging instead of `print()`
- bind DLQ kafka topic to some email warn process or the like
- split postrges data into multiple tables, make table partitions, fine tune *timescaledb*
- implement some retry feature so that failed messages are retried a couple of times before DLQ
- implement some "consumer : more workers needed" alerting so that additional consumers can be launched
- provide with *makefiles* for easier setup