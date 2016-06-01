from webob import Request, Response
from webob import exc
import cgi
from json import dumps
import inspect
# from vdbt.utils import *


class UploadServer(object):
    """ Serve the given object for uploading """

    def __init__(self, obj):
        self.obj = obj
        self.response_headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': (
                'access_token, '
                'accessToken, '
                'origin, '
                'x-csrftoken, '
                'content-type, '
                'accept'
            ),
            'Access-Control-Max-Age': '1728000'}

    def __call__(self, environ, start_response):
        req = Request(environ)
        try:
            resp = self.process(req)
        except ValueError, e:
            resp = exc.HTTPBadRequest(str(e))
        except exc.HTTPException, e:
            resp = e
        return resp(environ, start_response)

    def process(self, req):
        """
        process called when a http request is called

        :param  req: webob request object
        :type   req: ``object``

        :return: returns a webob response object
        :rtype:   ``object``
        """
        # TODO edit images (convert or so)
        # TODO spread pixels in image for sec. reasons (?)
        # https://github.com/python-pillow/Pillow/blob/master/PIL/Image.py#L1939
        # https://www.owasp.org/index.php/Unrestricted_File_Upload

        validated, response = self._validate(req)
        if not validated:
            return response

        try:
            files = []
            for file_ in req.POST:
                # check if element is a file
                if isinstance(req.POST[file_], cgi.FieldStorage):
                    files.append(req.POST[file_])
            upload_kw = {}

            if "security" in inspect.getargspec(self.obj.__call__):
                access_token = req.headers.get('access_token',
                                               req.headers.get('accessToken'))
                upload_kw['security'] = access_token

            return self._response(
                200,
                dumps(
                    self.obj(files, req.POST.get('uploadMeta', ''),
                             **upload_kw)),
                'application/json')
        except BaseException as e:
            return self._response(
                500,
                dumps(
                    {'error': str(e)}
                ),
                "application/json")

    def _validate(self, req):
        """Validate the request for current server instance.

        :param req: http request
        :type req: webob.Request
        :returns: tuple (continue, webob.Response)
        :rtype: tuple
        """
        if req.method == 'OPTIONS':
            return (False, self._response())
        if req.method != "POST":
            return (False, self._response(405,
                    "Method %s not allowed" % req.method))
        if "multipart/form-data" not in req.headers['Content-Type']:
            return (False, self._response(406, (
                'Not acceptable Content-Type; '
                'only multipart/form-data allowed')))
        file_number = len(filter(lambda x:
                                 isinstance(req.POST[x], cgi.FieldStorage),
                          req.POST))
        if file_number > 10:
            return (False, self._response(
                200,
                dumps(
                    {'error': 'Exceeded maximum number of files per upload'}
                ),
                "application/json"))
        elif file_number == 0:
            return (False, self._response(
                200,
                dumps(
                    {'error': 'No files for upload'}
                ),
                "application/json"))
        return (True, None)

    def _response(self, status=None, body=None, content_type=None):
        return Response(status=status,
                        content_type=content_type,
                        headers=self.response_headers,
                        body=body)
