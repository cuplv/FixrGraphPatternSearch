"""
Client used to access the src service.

"""

import json
import logging
import requests


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

  def get_json_pyhton_repr(self):
    my_map = {
      "githubUrl" : self._github_url,
      "commitId" :     self._commit_id,
      "declaringFile" : self._declaring_file,
      "methodLine" : self._method_line,
      "methodName" : self._method_name,
    }

    return my_map

class PatchResult:
  def __init__(self, patch_text, error_msg, is_error):
    self._patch_text = patch_text
    self._error_msg = error_msg
    self._is_error = is_error

  def is_error(self):
    return self._is_error

  def get_error_msg(self):
    return self._error_msg

  def get_patch(self):
    return self._patch_text


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
                            True)
    return patch_res

class SrcClientService(SrcClient):
  """ Base class for the src client """
  def __init__(self, addresss, port):
    super(SrcClient, self).__init__()
    self._address = addresss
    self._port = port

  def _get_service_address(self):
    address = "%s:%s" % (self._address, self._port)
    return address

  def getPatch(self, method_req, diffs_req):
    patch_res = None
    request = {method_req.get_json_python_repr,
               diffs_req}
    try:
      service_address = self.get_service_address()
      request_result = requests.post(service_address, json = request)

      if (request_result.status_code == 200):
        result_data = request_result.json()
        res_value = result_data["res"]
        res_status = res_value[0]
        res_patch = res_value[1]

        if (res_value != 0):
          patch_res = PatchResult(None, result_data["error"], True)
        else:
          patch_res = PatchResult(res_patch, "", False)

      else:
        err_msg = "Error code: %s" % (str(request_result.status_code))
        patch_res = PatchResult(None, err_msg, True)
    except Exception as e:
      err_msg = str(e)
      logging.error(err_msg)
      patch_res = PatchResult(None, err_msg, True)

    return patch_res
