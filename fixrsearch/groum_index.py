"""
Keeps an index of apps and groums
"""

import logging
import itertools
import os
from cStringIO import StringIO

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
    def __init__(self, graph_path):
        self.graph_path = graph_path
        self.apps = [app_data, app_data_2]
        self.appid2groums = {app_key : [groum_data], app_key_2 : [groum_data_2]}
        self.groumid2path = {groum_key : groum_path, groum_key_2 : groum_path_2}

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

    def get_groum_key(self, user_name, repo_name, commit_id,
                      method_name, line_number):
        key = "%s/%s/%s/%s/%s" % (user_name, repo_name, commit_id,
                                  method_name, line_number)
        return key

    def get_groum_key_app(self, app_key, method_name, line_number):
        key = "%s/%s/%s" % (app_key,
                            method_name, line_number)
        return key

        # repo_path = os.path.join(opts.graph_dir,
        #                          opts.user,
        #                          opts.repo)
        # if (opts.hash):
        #     repo_path = os.path.join(repo_path, opts.hash)
        # else:
        #     first_hash = None
        #     for root, dirs, files in os.walk(repo_path):
        #         if len(dirs) > 0:
        #             first_hash = dirs[0]
        #         break
        #     if first_hash is None:
        #         usage("Username/repo not found!")
        #     repo_path = os.path.join(repo_path, first_hash)

        # splitted = opts.method.split(".")
        # class_list = splitted[:-1]
        # method_list = splitted[-1:]
        # fs_name = ".".join(class_list) + "_" + "".join(method_list)
        # groum_file = os.path.join(repo_path, fs_name + ".acdfg.bin")

        # if (not os.path.isfile(groum_file)):
        #     usage("Groum file %s does not exist!" % groum_file)


