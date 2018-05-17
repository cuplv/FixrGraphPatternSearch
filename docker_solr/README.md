To build the image:
```docker build -t biggroum_solr .```

To run the solr server:

```docker run -d -p 9999:8983 --name=biggroum_solr biggroum_solr```
