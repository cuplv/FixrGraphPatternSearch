To build the image:
    ```docker build -t biggroum_solr .```

To run the solr server:

```docker run -d -p 30071:8983 --name=biggroum_solr biggroum_solr```

```docker run -d -p 30071:8983 --mount type=bind,source=/Users/sergiomover/works/projects/muse/bck/solr_groum,target=/persistent --name=biggroum_solr biggroum_solr```
