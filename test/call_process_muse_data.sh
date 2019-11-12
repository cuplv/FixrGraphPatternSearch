#!/bin/bash

curl -X POST -F src=@test_data/sources.zip -F graph=@test_data/graphs.zip http://localhost:8081/process_muse_data

