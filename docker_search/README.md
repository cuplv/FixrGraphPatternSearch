- build the image:
```docker build -t biggroum_search .```


# Run the test service

- run the docker container (using the test data):
```SEARCH_GROUM_DIR=`cd ../fixrsearch/test/data && pwd` && docker run -di -p 30072:8081 --mount type=bind,source=$SEARCH_GROUM_DIR,target=/persist --name=biggroum_search biggroum_search```

- test the search API (it takes some time)
```python test.py  -a localhost -p 30072```


# Run the production service
- download the data for the biggroum_search
```bash download_data.bash```

- run the docker container:
```SEARCH_GROUM_DIR=`cd ../demo_meeting && pwd` && docker run -di -p 30072:8081 --mount type=bind,source=$SEARCH_GROUM_DIR,target=/persist --name=biggroum_search biggroum_search```


