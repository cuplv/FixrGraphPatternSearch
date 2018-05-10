The search is deployed on an AWS instance. Send me your public key, so you can login there.
I am filling Solr with data now.

# 1. Test on your local machine

I have prepared some mock data that you can use to test everything on your local machine:
- Get the archive here: https://drive.google.com/open?id=0B4gcRlSUsv5FWjFianY5dFJGQ0E
- Unzip the archive: `tar xzf test_env.tar.gz`
- Unzip the solr data: `cd test_env && tar xzf server.tar.gz`
- Download solr version 3.5.1: https://archive.apache.org/dist/lucene/solr/5.3.1/solr-5.3.1.tgz
Extract it somewhere on your local machine.
- Checkout the following github repos:
  - git checkout https://github.com/cuplv/FixrGraphPatternSearch
  - git checkout https://github.com/cuplv/FixrGraph
  - git checkout https://github.com/cuplv/FixrGraphIso
- Set your PYTHONPATH
  - export PYTHONPATH=$PYTHONPATH:<PATH-TO-FixrGraph-REPO>
  - export PYTHONPATH=$PYTHONPATH:<PATH-TO-FixrGraphPatternSearch-REPO>
- Build the fixrgraphiso tools (using the instruction in the repo)
  - You need to install the z3 solver: `https://github.com/Z3Prover/z3`
  - You need to install glpk (`brew install glpk` if you use brew on mac)
  - You have to compile the tool
```
cd FixrGraphIso 
mkdir build
cd build
cmake ../
make
```

To run the example solr must run:
- Start the local instance of solr as: <PATH-TO_SOLR>/solr start -d test_env/server/ -s test_env/server/solr
- Now you can try a search as follows:

```python <PATH-TO-FixrGraphPatternSearch-REPO>/fixrsearch/search.py -d /test_env/testextraction/graphs -u BarcodeEye -r BarcodeEye -z 0e59cf40d83d3da67413b0b20410d6c57cca0b9e -m com.google.zxing.client.android.camera.CameraConfigurationManager_setDesiredCameraParameters -c /test_env/testextraction/clusters -i <PATH-TO-FixrGraphIso-REPO>/build/src/fixrgraphiso/fixrgraphiso ```


# 2. Groum blackbox pipeline:
The search tool is implemented in the <PATH-TO-FixrGraphPatternSearch-REPO>/fixrsearch/search.py script.

INPUT:
The tool should be invoked by passing the following informations:
- -d path to the graph directory
- -c path to the clusters
- -i path to the isomorphism computation executable
NOTE: all the above are an input that you give when your service start!
- -r repo name
- -u user name
- -z hash (optional)
- -m fully qualified method name
NOTE: you get these information as input to the service.

Example:
```python <PATH-TO-FixrGraphPatternSearch-REPO>/fixrsearch/search.py -d /test_env/testextraction/graphs -u BarcodeEye -r BarcodeEye -z 0e59cf40d83d3da67413b0b20410d6c57cca0b9e -m com.google.zxing.client.android.camera.CameraConfigurationManager_setDesiredCameraParameters -c /test_env/testextraction/clusters -i <PATH-TO-FixrGraphIso-REPO>/build/src/fixrgraphiso/fixrgraphiso ```


OUTPUT:
The tool returns a JSON file as output.

An example of the output is the following:
```
{"patterns": [{"obj_val": "69.0", "pattern_key": "1/isolated/2"}, {"obj_val": "47.3333", "pattern_key": "1/isolated/4"}, {"obj_val": "29.5", "pattern_key": "1/isolated/1"}, {"obj_val": "29.5", "pattern_key": "1/isolated/3"}, {"obj_val": "15.0", "pattern_key": "1/isolated/5"}], "result_code": 0}
```

More formally the output is (following the edmund notation):
```
output : { "result_code" : <INT>,
           "patterns" : LIST {"obj_val" : <FLOAT>, "pattern_key" : <TEXT>}
           "error_messages": <TEXT>}
```
Result code is 0 if everything is ok, 1 in case of an error.
In case of an error, the "error_messages" will contains the error message.
"patterns" is a list of dictionaries that contains the value of the objective function (used to rank the results) and 
"pattern_key" is the ID to the solr document that contains the pattern.

This, after you get the the results from the "blackbox" you have to query Solr.
You can get get a document represented as JSON from solr just by knowing its ID:
E.g ```http://localhost:8983/solr/groums/get?id=1```

Solr will return you a json like this if the search succeed:
```
{
  "doc":
  {
    "groum_keys_t":["BarcodeEye/BarcodeEye/0e59cf40d83d3da67413b0b20410d6c57cca0b9e/com.google.zxing.client.android.camera.PreviewCallback/onPreviewFrame",
      "BarcodeEye/BarcodeEye/0e59cf40d83d3da67413b0b20410d6c57cca0b9e/com.google.zxing.client.android.camera.CameraManager/setManualFramingRect",
      "BarcodeEye/BarcodeEye/0e59cf40d83d3da67413b0b20410d6c57cca0b9e/com.google.zxing.client.android.camera.CameraConfigurationManager/findBestPreviewSizeValue",
      "BarcodeEye/BarcodeEye/0e59cf40d83d3da67413b0b20410d6c57cca0b9e/com.google.zxing.client.android.camera.CameraConfigurationManager/setDesiredCameraParameters",
      "BarcodeEye/BarcodeEye/0e59cf40d83d3da67413b0b20410d6c57cca0b9e/com.google.zxing.client.android.camera.CameraManager/getFramingRect"],
    "methods_in_cluster_t":["<get>.android.graphics.Point.x_int",
      "<get>.android.graphics.Point.y_int",
      "android.util.Log.d"],
    "doc_type_sni":"cluster",
    "id":"1",
    "patterns_keys_t":["1/isolated/1",
      "1/isolated/2",
      "1/isolated/3",
      "1/isolated/4",
      "1/isolated/5"],
    "_version_":1565242320501080065}}
```

If the search fails, you will get something like this:
```
{"doc":null}
```

You have to pack this results and send it as output of the service (see later)


# 3. Changes to the endpoints

## 3.1. /compute/method/groums

The output should be changed as follows:
output: { patterns: LIST { weight : <FLOAT>, pattern : <PATTERN_JSON_DOCUMENT>} }
where <PATTERN_JSON_DOCUMENT> is the json document obtained from Solr.

## 3.2. /query/provenance/groums
The endpoint takes as input the solr id of a groum document on solr and returns the associated solr document.
It is just a facade to Solr.
```
input: { id : <TEXT> }
output : { groum_document : <TEXT>}
```
You just need to call solr and retrieve the document http://localhost:8983/solr/groums/get?id=<GROUM_ID>

I would rename the endpoint as /compute/method/solrid and make it general for simplicity now.
This way we can retrieve also the other kind of documents we need (e.g. clusters).


## 3.3 I don't understand the secondary route of the service.

