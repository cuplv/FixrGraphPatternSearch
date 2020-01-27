# FixrGraphPatternSearch
Implement the search of a pattern from a GROUM


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

# Unit test

Run the test with:
```nosetests```

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
