import requests
import json

data = {"user" : "BarcodeEye",
        "repo" : "BarcodeEye",
#        "class" : "com.google.zxing.client.android.camera.CameraConfigurationManager",
        "class" : "com.github.barcodeeye.scan.ResultsActivity",
#        "method" : "setDesiredCameraParameters",
        "method" : "newIntent"
#,
#        "hash" : "0e59cf40d83d3da67413b0b20410d6c57cca0b9e"
}

# com.github.barcodeeye.scan.ResultsActivity.newIntent

r = requests.post("http://localhost:30072/compute/method/groums", json=data)
#r = requests.post("http://localhost:8081/compute/method/groums", json=data)
print(r.json)


# {user: "BarcodeEye", repo: "BarcodeEye", class: "com.github.barcodeeye.scan.ResultsActivity", method: "newIntent", url: "http://localhost:30072/compute/method/groums"}
