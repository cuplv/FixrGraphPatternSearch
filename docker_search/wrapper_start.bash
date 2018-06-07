#!/bin/bash

sudo service ssh start

# echo "starting services"
python /home/biggroum/biggroum/fixr_groum_search_frontend/app.py --host 0.0.0.0 &
(while true; do sleep 10000; done) | /home/biggroum/biggroum/FixrService-Backend/target/universal/stage/bin/fixrservice-backend &


while sleep 60; do
    echo "Monitoring..."
done
