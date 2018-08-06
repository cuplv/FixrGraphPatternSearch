- build the image
```docker build -t biggroum_solr .```

- download the data for solr from google drive
```bash download_data.bash```

- run the docker container
```SOLR_GROUM_DIR=`cd ../solr_groum && pwd` && docker run -d -p 30071:8983 --mount type=bind,source=$SOLR_GROUM_DIR,target=/persist --name=biggroum_solr biggroum_solr```

- test the deployment
```python test.py -a localhost -p 30071```
