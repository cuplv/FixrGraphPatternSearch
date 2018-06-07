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
    print "Server port not provided! (try 30071)"
    sys.exit(1)

address="%s:%s" % (opts.address, opts.port)

r = requests.get("http://%s/solr/groums/get?id=69/popular/1" % address)

assert r.status_code == 200
json_res = r.json()

test(u"doc" in json_res)
test("doc_type_sni" in json_res[u"doc"])
test(json_res[u"doc"][u"doc_type_sni"] == "pattern")
test("type_sni" in json_res[u"doc"])
test(json_res[u"doc"][u"type_sni"] == "popular")


print "SUCCESS"
