"""
Implement the services for the BigGroum tools.

The endpoints are:
- search: search for the similar patterns to a groum
- get_apps: get all the apps (repos) existing in the dataset
- get_groums: get all the groums in the dataset
- process_graphs_pull_request: process a pull request and finds the similar pattern
- inspect_anomaly: provides the suggested fix for the anomaly
- explain_anomaly: provides the pattern violated by the anomaly
- view_examples: provides the examples of patterns explaining the anomaly

TODO:
- add a service that receives an apk + metadata and extract the graph,
  adding them to the filesystem and the index


"""

from flask import Flask, request, Response, render_template, current_app
import json
import optparse
import logging
import os
import sys
import copy



from search import (
    Search,
    get_cluster_file
)
from index import ClusterIndex
from groum_index import GroumIndex
from db import SQLiteConfig, Db
from src_service_client import SrcClient, SrcClientMock, SrcClientService
from process_pr import PrProcessor
from utils import PullRequestRef, RepoRef, CommitRef

CLUSTER_PATH = "cluster_path"
ISO_PATH = "iso_path"
CLUSTER_INDEX = "cluster_index"
GROUM_INDEX = "groum_index"
DB_NAME = "service_db"
DB_CONFIG="db_config"
SRC_CLIENT ="src_client"
TIMEOUT = 10

def get_new_db(config, create=False):
    db = Db(config)
    if create:
        db.connect_or_create()
    else:
        db.connect()
    return db

def get_malformed_request(error = None):
    if error is None:
       error = "Malformed request"
    else:
       error = "Malformed request (%s)" % error


    logging.error(error)

    reply_json = {"status": 1, "error" : "Malformed requests"}
    return Response(json.dumps(reply_json),
                    status=400,
                    mimetype='application/json')

def get_apps():
    groum_index = current_app.config[GROUM_INDEX]
    apps = groum_index.get_apps()
    return Response(json.dumps(apps),
                    status=200,
                    mimetype='application/json')

def get_groums():
    content = request.get_json(force=True)
    if (not content is None) and ("app_key" in content):
        app_key = content["app_key"]

        groum_index = current_app.config[GROUM_INDEX]
        groums = groum_index.get_groums(app_key)

        return Response(json.dumps(groums),
                        status=200,
                        mimetype='application/json')
    else:
        return get_malformed_request("no app key provided")


def search_pattern():
    content = request.get_json(force=True)

    if (not content is None) and ("groum_key" in content):
        groum_id = content["groum_key"]
        groum_index = current_app.config[GROUM_INDEX]
        groum_file = groum_index.get_groum_path(groum_id)

        if groum_file is None:
            error_msg = "Cannot find groum for %s" % groum_id
            reply_json = {"status" : 1,
                          "error" : error_msg}

            return Response(json.dumps(reply_json),
                            status=404,
                            mimetype='application/json')

        else:
            search = Search(current_app.config[CLUSTER_PATH],
                            current_app.config[ISO_PATH],
                            current_app.config[CLUSTER_INDEX],
                            current_app.config[GROUM_INDEX],
                            current_app.config[TIMEOUT])

            results = search.search_from_groum(groum_file)

            reply_json = {"status" : 0,
                          "results" : results}

            return Response(json.dumps(reply_json),
                            status=200,
                            mimetype='application/json')
    else:
        return get_malformed_request()



def process_graphs_in_pull_request():
    """
    Process a pull request and finds the anomalies
    """
    content = request.get_json(force=True)
    if (content is None):
        return get_malformed_request()

    fields = ["user", "repo", "commitHashes",
              "modifiedFiles", "pullRequestId"]
    for f in fields:
        if f not in content:
            return get_malformed_request("%s not in the request" % f)

    user_name = content["user"]
    repo_name = content["repo"]
    pull_request_id = content["pullRequestId"]

    commitHash = content["commitHashes"]
    data = commitHash["data"]
    commit_hash = data[0]["sha"]
    modifiedFiles = content["modifiedFiles"]


    logging.info(str(modifiedFiles))

    logging.info("Processing pull request for:\n" \
                 "%s\n%s\n%s\n%s\n" %
                 (user_name,
                  repo_name,
                  str(pull_request_id),
                  commit_hash))

    try:
        db = get_new_db(current_app.config[DB_CONFIG])
        pr_processor = PrProcessor(current_app.config[GROUM_INDEX],
                                   db,
                                   Search(current_app.config[CLUSTER_PATH],
                                          current_app.config[ISO_PATH],
                                          current_app.config[CLUSTER_INDEX],
                                          current_app.config[GROUM_INDEX],
                                          current_app.config[TIMEOUT]),
                                   current_app.config[SRC_CLIENT])

        logging.info("Searching for anomalies...")
        pr_ref = PullRequestRef(RepoRef(repo_name, user_name), pull_request_id,
                                CommitRef(RepoRef(repo_name, user_name),
                                          commit_hash))

        anomalies = pr_processor.process_graphs_from_pr(pr_ref)

        # produce the json output for the anomalies

        json_data = []

        for anomaly in anomalies:
            json_anomaly = {"id" : anomaly.numeric_id,
                            "error" : "",
                            "packageName" : anomaly.method_ref.package_name,
                            "className" : anomaly.method_ref.class_name,
                            "methodName" : anomaly.method_ref.method_name,
                            "fileName" : anomaly.git_path,
                            "line" : anomaly.method_ref.start_line_number}

            logging.info("Found anomaly %s: " % str(json_anomaly))

            json_data.append(json_anomaly)

        db.disconnect()

        logging.info("Generating the response for %d anomalies..." % (len(anomalies)))

        response = Response(json.dumps(json_data),
                            status=200,
                            mimetype='application/json')
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(str(e))

        response = Response(json.dumps({"status": 1,
                                        "error" : "Generic error"}),
                            status=500,
                            mimetype='application/json')

    return response


def _lookup_anomaly(current_app, content):
    for f in ["anomalyId", "pullRequest"]:
        if f not in content:
            return (None, None, get_malformed_request("%s not in the request" % f))
    for f in ["user","repo","id"]:
        if f not in content["pullRequest"]:
            return (None, None, get_malformed_request("%s not in the pull request" % f))

    user_name = content["pullRequest"]["user"]
    repo_name = content["pullRequest"]["repo"]
    pull_request_id = content["pullRequest"]["id"]
    anomaly_number = content["anomalyId"]

    db = get_new_db(current_app.config[DB_CONFIG])
    pr_processor = PrProcessor(current_app.config[GROUM_INDEX], db,
                               Search(current_app.config[CLUSTER_PATH],
                                      current_app.config[ISO_PATH],
                                      current_app.config[CLUSTER_INDEX],
                                      current_app.config[GROUM_INDEX],
                                      current_app.config[TIMEOUT]),
                               current_app.config[SRC_CLIENT])

    pr_ref = pr_processor.find_pr_commit(user_name, repo_name, pull_request_id)

    if pr_ref is None:
        error_msg = "Cannot find pull request %s for %s/%s" % (str(pull_request_id),
                                                               user_name,
                                                               repo_name)
        reply_json = {"status" : 1, "error" : error_msg}
        pr_processor = None
        return (None, None, Response(json.dumps(reply_json), status=404,
                                     mimetype='application/json'))

    anomaly_ref = db.get_anomaly_by_pr_and_number(pr_ref, anomaly_number)
    if anomaly_ref is None:
        error_msg = "Cannot find anomaly %s" % (str(anomaly_number))
        reply_json = {"status" : 1, "error" : error_msg}
        pr_processor = None
        return (None, None, Response(json.dumps(reply_json), status=404,
                                     mimetype='application/json'))

    db.disconnect()

    return (pr_processor, anomaly_ref, None)


def inspect_anomaly():
    logging.info("Inspect anomalies...")

    content = request.get_json(force=True)
    if content is None:
        return get_malformed_request()

    (pr_processor, anomaly_ref, error) = _lookup_anomaly(current_app, content)

    if (not error is None): return error
    assert (not pr_processor is None) and (not anomaly_ref is None)

    # TODO: generate more meaningful data for the edit suggestion
    # This should happen when creating the patch
    edit_suggestion = {"editText" : anomaly_ref.patch_text,
                       "fileName" : anomaly_ref.git_path,
                       "lineNumber" : anomaly_ref.method_ref.start_line_number}

    logging.debug(edit_suggestion)

    logging.info("Anomaly found, returning file...")
    return Response(json.dumps(edit_suggestion),
                    status=200,
                    mimetype='application/json')


def explain_anomaly():
    content = request.get_json(force=True)
    if content is None:
        return get_malformed_request()


    (pr_processor, anomaly_ref, error) = _lookup_anomaly(current_app, content)

    if (not error is None): return error
    assert (not pr_processor is None) and (not anomaly_ref is None)

    pattern_info = {"patternCode" : anomaly_ref.pattern_text,
                    "numberOfExamples" : anomaly_ref.pattern.frequency}

    return Response(json.dumps(pattern_info),
                    status=200,
                    mimetype='application/json')


def flaskrun(default_host="127.0.0.1", default_port="5000"):
    p = optparse.OptionParser()

    p.add_option('-a', '--address', help="Host name")
    p.add_option('-p', '--port', help="Port name")
    p.add_option('-d', '--debug', help="Debug mode",
                 action="store_true", default=False)

    p.add_option('-g', '--graph_path', help="Base path to the acdfgs")
    p.add_option('-c', '--cluster_path', help="Base path to the cluster directory")
    p.add_option('-i', '--iso_path', help="Path to the isomorphism computation")

    p.add_option('-z', '--srcclientaddress', help="")
    p.add_option('-l', '--srcclientport', help="")

    # p.add_option('-d', '--db_type', type='choice',
    #              choices= ["sqlite"],
    #              help="Choose db type to use",
    #              default = "sqlite")

    def usage(msg=""):
        if msg:
            print "----%s----\n" % msg
            p.print_help()
            print "Example of usage %s" % ("python search_service.py " \
                                           "-c <cluster_path>" \
                                           "-i <searchlattice>")
        sys.exit(1)
    opts, args = p.parse_args()


    host = opts.address if opts.address else default_host
    port = opts.port if opts.port else default_port

    srchost = opts.srcclientaddress if opts.srcclientaddress else None
    srcport = opts.srcclientport if opts.srcclientport else None

    if (not opts.cluster_path):
        usage("Cluster path not provided!")
    if (not os.path.isdir(opts.cluster_path)):
        usage("Cluster path %s does not exist!" % (opts.cluster_path))
    if (not opts.graph_path):
        usage("Graph path not provided!")
    if (not os.path.isdir(opts.graph_path)):
        usage("Graph path %s does not exist!" % (opts.graph_path))

    if (not opts.iso_path): usage("Iso executable not provided!")
    if (not os.path.isfile(opts.iso_path)):
        usage("Iso executable %s does not exist!" % opts.iso_path)

    if (opts.debug):
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    app = create_app(opts.graph_path, opts.cluster_path,
                     opts.iso_path,
                     DB_NAME,
                     srchost,srcport)

    app.run(
        debug=opts.debug,
        host=host,
        port=int(port)
    )
    logging.info("Running server...")


def create_app(graph_path, cluster_path, iso_path,
               db_path = DB_NAME,
               src_client_address = None,
               src_client_port = None):
    app = Flask(__name__)
    app.config[TIMEOUT] = 360
    app.config[CLUSTER_PATH] = cluster_path
    app.config[ISO_PATH] = iso_path

    cluster_file = get_cluster_file(cluster_path)

    logging.info("Creating cluster index...")
    app.config[CLUSTER_INDEX] = ClusterIndex(cluster_file)

    logging.info("Creating graph index...")
    app.config[GROUM_INDEX] = GroumIndex(graph_path)

    # create the db object
    config = SQLiteConfig(db_path)
    app.config[DB_CONFIG] = config
    db = get_new_db(config, True)
    db.disconnect()

    # set up the src_client
    if (src_client_address is None):
        src_client = SrcClientMock()
    else:
        src_client = SrcClientService(src_client_address,
                                      src_client_port)
    app.config[SRC_CLIENT] = src_client

    logging.info("Set up routes...")
    app.route('/search', methods=['POST'])(search_pattern)
    app.route('/get_apps', methods=['GET'])(get_apps)
    app.route('/get_groums', methods=['POST'])(get_groums)
    app.route('/process_graphs_in_pull_request', methods=['POST'])(process_graphs_in_pull_request)
    app.route('/inspect_anomaly', methods=['POST'])(inspect_anomaly)
    app.route('/explain_anomaly', methods=['POST'])(explain_anomaly)


    return app


if __name__ == '__main__':
    flaskrun()
