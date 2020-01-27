# FixrGraphPatternSearch
Implement the search of a pattern from a GROUM (both a service and a command line util)


# Spin up the service

You need to run the source code service before (in `../fixr_source_code_service/` if you are in the `biggroum` repository, or alternatively clone `https://github.com/cuplv/fixr_source_code_service`) using `sbt run`.

Also, the command line above assumes you are in the `biggroum` repository and you have compiled the graph isomorphism.


```python fixrsearch/search_service.py -a localhost -p 8081 -g ./fixrsearch/test/data/graphs -c ./fixrsearch/test/data/clusters -i ../FixrGraphIso/build/src/fixrgraphiso/searchlattice -d -l 8080 -z localhost
```

```
python ./fixrsearch/search_service.py \
  -c ~/works/projects/muse/repos/test_clusters/clusters \
  -i /Users/sergiomover/works/projects/muse/repos/FixrGraphIso/build/src/fixrgraphiso/searchlattice \
  -g ~/works/projects/muse/repos/test_clusters/graphs -d - 5008
```

# Run the search from the command line command line

```bash
python fixrsearch/search_script/search_script.py -d /mnt/BigGroumData19/fdroid_out_012519/graphs \
  -c /mnt/BigGroumData19/fdroid_out_012519/clusters \
  -i ../FixrGraphIso/build/src/fixrgraphiso/searchlattice \
  -t 10 \
  -a /tmp/tmpapk/MapboxAndroidDemo-global-debug.apk \
  -e ../FixrGraphExtractor/target/scala-2.12/fixrgraphextractor_2.12-0.1.0-one-jar.jar \
  -s /home/ubuntu/local_search/mapbox-android-demo/MapboxAndroidDemo/src/global \
  -o mapbox.json \
  -p mapbox.html
```

# Unit test

Run the test with:
```nosetests```

You need to have a [source code server running on localhost](https://github.com/cuplv/fixr_source_code_service)  and have compiled the searchlattice executable in [FixrGraphIso](https://github.com/cuplv/FixrGraphIso)

# Test
```
curl -d "" -X POST http://localhost:5000/search
```

```
curl -X GET http://localhost:5000/get_apps

curl -d '{"app_key" : "Dagwaging/RoseWidgets/7848e367734f462a085a72c9d6323262aef29900"}' -X POST http://localhost:5000/get_groums

```



# Other dependencies
- httplib: pip install httplib2
