import requests
import json

data = {"user" : "BarcodeEye",
        "repo" : "BarcodeEye",
        "class" : "Groums",
        "method" : "com.google.zxing.client.android.camera.CameraConfigurationManager_setDesiredCameraParameters",
        "hash" : "0e59cf40d83d3da67413b0b20410d6c57cca0b9e"}


r = requests.post("http://localhost:10000/compute/method/groums", json=data)

print(r.json)

