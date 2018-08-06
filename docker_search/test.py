import requests
import json
import optparse
import sys


def test(condition):
    if not condition:
        print "FAILURE!"
        sys.exit(1)

p = optparse.OptionParser()
p.add_option('-a', '--address', help="Ip address of the solr server")
p.add_option('-p', '--port', help="Port of the solr server")

opts, args = p.parse_args()
if (not opts.address):
    print "Server address not provided! (try localhost)"
    sys.exit(1)

if (not opts.port):
    print "Server port not provided! (try 30072)"
    sys.exit(1)

address="%s:%s" % (opts.address, opts.port)

# Delvison/Student-Handbook/77b4eb417abb95e0ed1258a39db02bcdb8b07945
# com.example.studentplanner.AssignmentActivity.clickHandler
# {user: "BarcodeEye", repo: "BarcodeEye", class: "com.github.barcodeeye.scan.ResultsActivity", method: "newIntent", url: "http://localhost:30072/compute/method/groums"}
# data = {
#     "user" : "BarcodeEye",
#     "repo" : "BarcodeEye",
#     "class" : "com.github.barcodeeye.scan.ResultsActivity",
#     "method" : "newIntent"
# }
# data = {
#     "user" : "BarcodeEye",
#     "repo" : "BarcodeEye",
#     "class" : "com.google.zxing.client.android.camera.CameraConfigurationManager",
#     "method" : "setDesiredCameraParameters",
# }
# data = {
#     "user" : "DroidPlanner",
#     "repo" : "Tower",
#     "class" : "org.droidplanner.android.droneshare.data.DroneShareDB",
#     "method" : "getDataToUpload",
# }
# data = {
#     "user" : "tommyd3mdi",
#     "repo" : "c-geo-opensource",
#     "class" : "cgeo.geocaching.apps.cache.navi.NavigonApp",
#     "method" : "invoke",
# }

# data = {
#     "user" : "hardikp888",
#     "repo" : "my-daily-quest",
#     "class" : "br.quest.PreferenceManager",
#     "method" : "savePreference",
# }

data = {
    "user" : "anyremote",
    "repo" : "anyremote-android-client",
    "commit_id" : "bc762d918fc38903daa55eaa8e481cd9c12b5bd9",
    "method" : "anyremote.client.android.TextScreen.commandAction"
}
#TextScreen.java
# 213


r = requests.post("http://%s/compute/method/groums" % address, json=data)

test(r.status_code == 200)
json_res = r.json()

with open("res_json.json", "w") as json_file:
    json.dump(json_res, json_file)
    json_file.close()

test(u"patterns" in json_res)
test(len(json_res[u"patterns"]) > 0)

print "SUCCESS"


