The docker compose runs the docker containers for the biggroum search.

To run the docker compose file, you should first download the search data:
```cd ../docker_solr && bash download_data.bash ```

```cd ../docker_search && bash download_data.bash ```

Then run docker compose to spin up the search:
```docker-compose up -d```

The services should be up. Run the tests to see if everything is ok:
```cd ../docker_solr && python test.py -a localhost -p 30071```

```cd ../docker_search && python test.py -a localhost -p 30072```


`docker-compose-global.yml` contains the setup used when using the images deployed on the HELICON inftrastructure.

To run it rename it to docker-compose.yml
