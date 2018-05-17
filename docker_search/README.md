To build the image:
```docker build -t biggroum_search .```

To run the solr server:


```docker run -d --link=biggroum_solr --name=biggroum_search biggroum_search```

```docker run -d -p 10000:8081 -p 10001:5000 --link=biggroum_solr --name=biggroum_search biggroum_search```

docker run -di -p 10000:8081 -p 10001:5000 --link=biggroum_solr --name=biggroum_search biggroum_search

Notes:

Web proxy run on port 5000

Search runs on port 8081 by default
