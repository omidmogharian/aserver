from webob import Request, Response
from webob import exc
from json import loads, dumps
import traceback, sys, inspect
from bson import json_util
from constants import Basic_HEADER
from utils import pep8case


class JsonRpcServer(object):
    """ Serve the given object via json-rpc """

    def __init__(self, obj):
        self.obj = obj

    def __call__(self, environ, start_response):
        """
        __call__ object is callable, when its called, the request (environ) will be fetched

        :param  environ: request object
        :type   environ: ``object``
        :param  start_response: start response object
        :type   start_response: ``object``

        :return: Response
        :rtype:   ``object``
        :raises exc.HTTPForbidden: if the webob Request raises an error
        """
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
        processes the given request as a json RPC

        :param  req: request object
        :type   req: ``object``

        :return: Response
        :rtype:   ``object``
        :raises ValueError: if json could not be decoded
        :raises ValueError: if json body missing a specified parameter
        :raises exc.HTTPForbidden: if a method name does not exist
        :raises ValueError: if a parameter must be a list or dict
        :raises ValueError: if a method does not exists
        """
        if req.method == 'OPTIONS':
            return Response(
                headers=Basic_HEADER)

        if req.method == 'GET':
            raise exc.HTTPMethodNotAllowed(
                "Only POST is allowed",
                allowed='POST')

        try:
            json = loads(req.body, object_hook=json_util.object_hook)
        except ValueError, e:
            raise ValueError('Bad JSON: %s' % e)
        try:
            act = req.headers.get('access_token') or req.headers.get('accessToken')

            method = json['method']
            params = json['params']
            params["requester"] = req.client_addr
            if act:
                params['security'] = act
            id = json['id']

        except KeyError, e:
            raise ValueError(
                "JSON body missing parameter: %s" % e)
        if method.startswith('_'):
            raise exc.HTTPForbidden(
                "Bad method name %s: must not start with _" % method)
        if not isinstance(params, dict) and not isinstance(params, list):
            raise ValueError(
                "Bad params %r: must be a dict or list " % params)

        if hasattr(self.obj, pep8case(method)):
            method = getattr(self.obj, pep8case(method))
        else:

            raise ValueError(
                "No such method %s" % method)
        try:
            if isinstance(params, dict):
                for k in params:
                    params[pep8case(k)] = params.pop(k)

            result = method(**params)
        except:
            # TODO: handel Exeption with diffrent code
            text = traceback.format_exc()
            exc_value = sys.exc_info()[1]
            error_value = dict(
                name='JSONRPCError',
                code=100,
                message=str(exc_value),
                error=text)
            return Response(
                headers=Basic_HEADER,
                status=500,
                content_type='application/json',
                body=dumps(dict(
                    error=error_value,
                    id=id), default=json_util.default))
        result = 1 if result == None else result

        return Response(
            headers=Basic_HEADER,
            content_type='application/json',
            body=dumps(dict(result=result,
                            id=id), default=json_util.default))
