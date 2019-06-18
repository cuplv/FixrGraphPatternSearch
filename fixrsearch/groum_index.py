"""
Keeps an index of apps and groums existing in the
dataset.
"""

import json
import logging
import itertools
import sys
import os

from fixrgraph.annotator.protobuf.proto_acdfg_pb2 import Acdfg

groum_key = "Dagwaging/RoseWidgets/7848e367734f462a085a72c9d6323262aef29900/com.dagwaging.rosewidgets.db.widget.UpdateService.update/208"
groum_data = {
    "groum_key" : groum_key,
    "method_line_number": 208,
    "package_name": "com.dagwaging.rosewidgets.db.widget",
    "class_name": "com.dagwaging.rosewidgets.db.widget.UpdateService",
    "source_class_name": "UpdateService.java",
    "method_name": "update"
}
groum_path="Dagwaging/RoseWidgets/7848e367734f462a085a72c9d6323262aef29900/com.dagwaging.rosewidgets.db.widget.UpdateService_update.acdfg.bin"

groum_key_2 = "osmwp/MeMoPlayer/fd47ade14e3f8b256e3a332649bb567052044c70/com.orange.memoplayer.WidgetUpdate.getRemoteView/155"
groum_data_2 = {
    "groum_key" : groum_key_2,
    "method_line_number": 155,
    "package_name": "com.orange.memoplayer",
    "class_name": "com.orange.memoplayer.WidgetUpdate",
    "source_class_name": "WidgetUpdate.java",
    "method_name": "getRemoteView"
}
groum_path_2="osmwp/MeMoPlayer/fd47ade14e3f8b256e3a332649bb567052044c70/com.orange.memoplayer.WidgetUpdate_getRemoteView.acdfg.bin"

app_key = "Dagwaging/RoseWidgets/7848e367734f462a085a72c9d6323262aef29900"
app_data = {
    "app_key" : app_key,
    "url": "https://github.com/Dagwaging/RoseWidgets",
    "user_name": "Dagwaging",
    "commit_hash": "7848e367734f462a085a72c9d6323262aef29900",
    "commit_date": "",
    "repo_name": "RoseWidgets"
}
app_key_2 = "osmwp/MeMoPlayer/fd47ade14e3f8b256e3a332649bb567052044c70"
app_data_2 = {
    "app_key" : app_key_2,
    "url": "https://github.com/osmwp/MeMoPlayer",
    "user_name": "osmwp",
    "commit_hash": "fd47ade14e3f8b256e3a332649bb567052044c70",
    "commit_date": "",
    "repo_name": "MeMoPlayer"
}

class GroumIndex(object):
    def __fake_init__(self, graph_path):
        self.graph_path = graph_path
        self.apps = [app_data, app_data_2]
        self.appid2groums = {app_key : [groum_data], app_key_2 : [groum_data_2]}
        self.groumid2path = {groum_key : groum_path, groum_key_2 : groum_path_2}

    def __init__(self, graph_path):
        self.graph_path = os.path.abspath(graph_path)

        self.apps = []
        self.appid2groums = {}
        self.groumid2path = {}

        self.index_file_name = os.path.join(self.graph_path, "graph_index.json")
        if (os.path.exists(self.index_file_name)):
            self.load_index(self.index_file_name)
        else:
            self.build_index()
            self.write_index(self.index_file_name)

    def get_apps(self):
        return self.apps

    def get_groums(self, app_id):
        if app_id in self.appid2groums:
            return self.appid2groums[app_id]
        else:
            return []

    def get_groum_path(self, groum_id):
        if groum_id in self.groumid2path:
            return os.path.join(self.graph_path, self.groumid2path[groum_id])
        else:
            return None

    @staticmethod
    def get_app_key(user_name, repo_name, commit_id):
      app_key = "%s/%s/%s" %(user_name,
                             repo_name,
                             commit_id)
      return app_key

    def get_groum_key(self, user_name, repo_name, commit_id,
                      method_name, line_number):
        key = "%s/%s/%s/%s/%s" % (user_name, repo_name, commit_id,
                                  method_name, line_number)
        return key

    def get_groum_key_app(self, app_key, method_name, line_number):
        key = "%s/%s/%s" % (app_key,
                            method_name, line_number)
        return key

    def process_groum(self, apps_set, groum_abs_path):
        # Read the groum
        acdfg = Acdfg()
        with open(groum_abs_path,'rb') as fgroum:
            acdfg.ParseFromString(fgroum.read())
            method_list = []
            for method_node in acdfg.method_node:
                method_list.append(method_node.name)
            fgroum.close()

        # get repo data
        if (not acdfg.HasField("repo_tag")):
            # logging.info("No repo_tag...")
            return
        repoTag = acdfg.repo_tag

        if (not (repoTag.HasField("user_name") and
                 repoTag.HasField("repo_name") and
                 repoTag.HasField("url") and
                 repoTag.HasField("commit_hash"))):
            # logging.info("No repo info...")
            return


        app_key = "%s/%s/%s" % (repoTag.user_name,
                                repoTag.repo_name,
                                repoTag.commit_hash)

        repo = {
            "app_key" : app_key,
            "repo_name" : repoTag.repo_name,
            "user_name" : repoTag.user_name,
            "url" : repoTag.url,
            "commit_hash" : repoTag.commit_hash}

        # get acdfg data
        if (not acdfg.HasField("source_info")):
            # logging.info("No source_info...")
            return
        protoSource = acdfg.source_info

        if (not (protoSource.HasField("package_name") and
                 protoSource.HasField("class_name") and
                 protoSource.HasField("method_name") and
                 protoSource.HasField("class_line_number") and
                 protoSource.HasField("method_line_number") and
                 protoSource.HasField("source_class_name") and
                 protoSource.HasField("abs_source_class_name"))):
            # logging.info("No source info...")
            return;

        groum_key = "%s/%s.%s/%s" % (app_key,
                                     protoSource.class_name,
                                     protoSource.method_name,
                                     protoSource.method_line_number)
        groum_data = {
            "groum_key" : groum_key,
            "method_line_number": protoSource.method_line_number,
            "package_name": protoSource.package_name,
            "class_name": protoSource.class_name,
            "source_class_name" : protoSource.source_class_name,
            "method_name": protoSource.method_name
        }

        # get the path of the file relative to self.graph_path
        assert(groum_abs_path[:len(self.graph_path)] == self.graph_path)
        groum_rel_path = groum_abs_path[len(self.graph_path)+1:]

        # logging.info("Adding info...")

        # Set the data structure
        if app_key not in apps_set:
            self.apps.append(repo)
            apps_set.add(app_key)

        if not app_key in self.appid2groums:
            self.appid2groums[app_key] = [groum_data]
        else:
            self.appid2groums[app_key].append(groum_data)

        self.groumid2path[groum_key] = groum_rel_path


    def build_index(self):
        logging.info("Creating graph index...")

        apps_set = set()
        for root, subFolder, files in os.walk(self.graph_path):
            for item in files:
                if item.endswith(".bin") :
                    full_file_name = os.path.join(root,item)
                    full_file_name = os.path.abspath(full_file_name)
                    self.process_groum(apps_set, full_file_name)


        logging.info("Index created - stats:\n" \
                     "\tNumber of repos: %d\n" \
                     "\tNumber of graphs: %d\n" % (len(self.apps),
                                                   len(self.groumid2path)))


    def write_index(self, index_file_name):
        logging.info("Writing index...")
        index_data = {"apps" : self.apps,
                      "appid2groums" : self.appid2groums,
                      "groumid2path" : self.groumid2path}
        with open(index_file_name, "w") as index_file:
            json.dump(index_data, index_file)
            index_file.close()


    def load_index(self, index_file_name):
        logging.info("Loading index...")

        with open(index_file_name, "r") as index_file:
            index_data = json.load(index_file)
            index_file.close()

        self.apps = index_data["apps"]
        self.appid2groums = index_data["appid2groums"]
        self.groumid2path = index_data["groumid2path"]
