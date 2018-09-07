- build the image:
```docker build -t biggroum_search .```

- download the data for the biggroum_search
```bash download_data.bash```

- run the docker container:
```SEARCH_GROUM_DIR=`cd ../demo_meeting && pwd` && docker run -di -p 30072:8081 --mount type=bind,source=$SEARCH_GROUM_DIR,target=/persist --name=biggroum_search biggroum_search```


- test the search API (it takes some time)
```python test.py  -a localhost -p 30072```

