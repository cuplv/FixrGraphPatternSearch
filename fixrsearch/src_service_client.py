"""
Client used to access the src service.

"""

import json
import logging
import requests
import base64


class SrcMethodReq:
  def __init__(self,
               github_url,
               commit_id,
               declaring_file,
               method_line,
               method_name):
    self._github_url = github_url
    self._commit_id = commit_id
    self._declaring_file = declaring_file
    self._method_line = method_line
    self._method_name = method_name

  def get_json_repr(self, src_on_disk = None):
    if src_on_disk is None:
      my_map = {
        "githubUrl" : self._github_url,
        "commitId" :     self._commit_id,
        "declaringFile" : self._declaring_file,
        "methodLine" : self._method_line,
        "methodName" : self._method_name,
      }
    else:
      my_map = {
        "fileData" : self._get_src_encoding(src_on_disk),
        "declaringFile" : self._declaring_file,
        "methodLine" : self._method_line,
        "methodName" : self._method_name,
      }
    return my_map

  def _get_src_encoding(self, src_on_disk):
    file_to_encode = src_on_disk + "/sources/" + self._declaring_file
    with open(file_to_encode, "rb") as f:
      encoded = base64.b64encode(f.read().encode("utf-8"))
    return encoded


class DiffEntry():
  def __init__(self, line_num, entry_name, what):
    self._line_num = line_num
    self._entry_name = entry_name
    self._what = what

  def get_json_repr(self):
    my_map = {
      "lineNum" : self._line_num,
      "entryName" : self._entry_name,
      "what" : self._what
    }
    return my_map

class SourceDiff():
  def __init__(self, diff_type, entry, exits):
    self._diff_type = diff_type
    self._entry = entry
    self._exits = exits

  def get_json_repr(self):
    my_map = {
      "diffType" : self._diff_type,
      "entry" : self._entry.get_json_repr(),
      "exits" : [e.get_json_repr() for e in self._exits]
    }

    return my_map

class PatchResult:
  def __init__(self, patch_text, error_msg, is_error, git_path):
    self._patch_text = patch_text
    self._error_msg = error_msg
    self._is_error = is_error
    self._git_path = git_path

  def is_error(self):
    return self._is_error

  def get_error_msg(self):
    return self._error_msg

  def get_patch(self):
    return self._patch_text

  def get_git_path(self):
    return self._git_path

class SrcClient(object):
  """ Base class for the src client """
  def __init__(self):
    super(object, self).__init__()

  def getPatch(self, method_req, diffs_req):
    raise NotImplementedError()


class SrcClientMock(SrcClient):
  def __init__(self):
    super(SrcClient, self).__init__()

  def getPatch(self, method_req, diffs_req):
    patch_res = PatchResult(None,
                            "Mock implementation",
                            True,
                            "")
    return patch_res

class SrcClientService(SrcClient):
  """ Base class for the src client """
  def __init__(self, addresss, port):
    super(SrcClient, self).__init__()
    self._address = addresss
    self._port = port

  def _get_service_address(self, is_local):
    if is_local:
      address = "http://%s:%s/patch_from_file" % (self._address, self._port)
    else:
      address = "http://%s:%s/patch" % (self._address, self._port)
    return address

  def getPatch(self, method_req, diffs_requests, src_on_disk = None):
    if src_on_disk is not None:
      is_local = True
    else:
      is_local = False
    patch_res = None
    diffs_requests_converted = [diffs_req.get_json_repr() for diffs_req in diffs_requests]
    request = {"methodRef" : method_req.get_json_repr(src_on_disk),
               "diffsToApply" : [diffs_requests_converted[0]]}
    try:
      service_address = self._get_service_address(is_local)
      request_result = requests.post(service_address, json = request)

      if (request_result.status_code == 200):
        result_data = request_result.json()
        res_value = result_data["res"]
        res_status = res_value[0]

        if (res_status == 0):
          res_patch = res_value[1]
          if (len(res_patch) == 2):

            def is_extension(text):
              return (text.endswith(".java") or
                      text.endswith(".scala") or
                      text.endswith(".kt") or
                      text.endswith(".kts"))
            # Hack
            zero_is_fn = is_extension(res_patch[0])
            one_is_fn = is_extension(res_patch[1])

            if (zero_is_fn and one_is_fn):
              patch_res = PatchResult(None, "No patch text in the reply", True,
                                      "")
            else:
              patch_file = res_patch[0] if zero_is_fn else res_patch[1]
              patch_text = res_patch[0] if one_is_fn else res_patch[1]

              patch_res = PatchResult(patch_text, "", False, patch_file)
          else:
            patch_res = PatchResult(None, "No patch text in the reply", True, "")
        else:
          patch_res = PatchResult(None, result_data["error"], True, "")
          logging.error(result_data["error"])

      else:
        err_msg = "Error code: %s" % (str(request_result.status_code))
        logging.error(err_msg)
        patch_res = PatchResult(None, err_msg, True, "")
    except Exception as e:
      err_msg = str(e)
      logging.error(err_msg)
      patch_res = PatchResult(None, err_msg, True, "")

    return patch_res
