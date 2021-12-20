FROM python:3.10.0b2

# set the working directory in the container
WORKDIR /measure

# copy the dependencies file to the working directory
COPY  measurement/requirements.txt .

# install dependencies
RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY measurement/src/measurement.py .

# Copy Kafka creds and certs
ARG KAFKA_CA=certs/ca.pem
ARG KAFKA_KEY=certs/service.key
ARG KAFKA_CERT=certs/service.cert

COPY $KAFKA_CA .
COPY $KAFKA_KEY .
COPY $KAFKA_CERT .

# command to run on container start
CMD [ "python", "measurement.py" ]