#!/bin/bash

sudo service ssh start

# echo "starting services"
(while true; do sleep 10000; done) | /home/biggroum/biggroum/FixrService-Backend/target/universal/stage/bin/fixrservice-backend &


while sleep 60; do
    echo "Monitoring..."
done
