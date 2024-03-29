#!/bin/bash
# This script is used to deploy Autosketch

#check if docker-compose is installed
if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi
#check if curl is installed
if ! [ -x "$(command -v curl)" ]; then
  echo 'Error: curl is not installed.' >&2
  exit 1
fi

#create autosketch directory and etc
mkdir Autosketch
mkdir Autosketch/etc

#copy necessary files with curl, dont display stderr
config_url="https://raw.githubusercontent.com/autodfir/Autosketch/main/etc/example-config.yaml"
config_path="Autosketch/etc/config.yaml"
if curl -s -o /dev/null -I -w "%{http_code}" $config_url; then
    curl -s $config_url > $config_path
else
    echo "Error: Could not download config.yaml"
    exit 1
fi 

docker_compose_url="https://raw.githubusercontent.com/autodfir/Autosketch/main/docker-compose.yaml"
docker_compose_path="Autosketch/docker-compose.yaml"

if curl -s -o /dev/null -I -w "%{http_code}" $docker_compose_url; then
    curl -s $docker_compose_url > $docker_compose_path
else
    echo "Error: Could not download docker-compose.yaml"
    exit 1
fi

#read Timesketch IP address and port
echo "Please enter the IP address of the Timesketch server"
read TIMESKETCH_IP
echo "Please enter the port of the Timesketch server"
read TIMESKETCH_PORT

#ask if user wants to use continue if Timesketch is not running
if ! curl -s -o /dev/null -I -w "%{http_code}" http://$TIMESKETCH_IP:$TIMESKETCH_PORT; then
    echo "Timesketch is not running on $TIMESKETCH_IP:$TIMESKETCH_PORT"
    echo "Do you want to continue? (y/n)"
    read CONTINUE
    if [ $CONTINUE != "y" ]; then
        exit 1
    fi
fi

#replace Timesketch IP and port in config.yaml
sed -i "s/TS_IP_HERE/$TIMESKETCH_IP/g" Autosketch/etc/config.yaml
sed -i "s/TS_PORT_HERE/$TIMESKETCH_PORT/g" Autosketch/etc/config.yaml

#ask if user want to run docker-compose
echo "Do you want to run docker-compose? (y/n)"
read RUN
if [ $RUN == "y" ]; then
    cd Autosketch
    docker-compose up -d
fi

#inform user that Autosketch is running on localost:5001
echo "Autosketch is running visit"
echo "http://localhost:5001"




