# FixrGraphPatternSearch
Implement the search of a pattern from a GROUM


# Spin up the service

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
