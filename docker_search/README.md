- build the image:
```docker build -t biggroum_search .```

- download the data for the biggroum_search
```bash download_data.bash```

- run the docker container:
```docker run -di -p 30072:8081 -p 30073:5000 --link=biggroum_solr --mount type=bind,source=./sitevisit_extraction,target=/persist --name=biggroum_search biggroum_search```


- test the search API (it takes some time)
```python test.py  -a localhost -p 30072```


- test the web search:

Open the browser at `http://localhost:30073`

Insert the GitHub username and repository name: `tommyd3mdi/c-geo-opensource`

Insert the method name: `cgeo.geocaching.apps.cache.navi.NavigonApp.invoke`

Press the `Search` button
