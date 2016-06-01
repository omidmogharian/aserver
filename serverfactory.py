from webob import Request, Response
from simplejson import dumps
import sys
import re
from vdbt.aserve.jsonrpcserver import JsonRpcServer
from vdbt.aserve.uploadserver import UploadServer
import optparse
from wsgiref import simple_server
import subprocess
from multiprocessing import cpu_count


class App(object):

    server_mapping = {
        "JsonRpcServer": JsonRpcServer,
        "UploadServer": UploadServer
    }

    def __init__(self, settings):
        self.urls = [(r'^$', self.index)]
        if isinstance(settings, dict):
            self._api_init(settings)
        elif isinstance(settings, list):
            for setting in settings:
                self._api_init(setting)

    def _api_init(self, setting):
        v = setting['api_version']
        for item in setting.get('module_registry', {}).items():
            server = self.server_map(setting.get("server", "JsonRpcServer"))
            self.urls.append(((r'%s/?$' % (v + "/" + item[0]),
                               self.serve_obj(item[1], server))))

    def __call__(self, environ, start_response):
        """
        The main WSGI app Dispatch the current request to
        the functions from above and store the regular expression
        captures in the WSGI environment as  `myapp.url_args` so that
        the functions can access the url placeholders.

        If nothing matches call the `not_found` function.
        """

        req = Request(environ)
        path = req.path.lstrip('/')
        for regex, callback in self.urls:
            match = re.search(regex, path)
            if match is not None:
                environ['myapp.url_args'] = match.groups()
                return callback(environ, start_response)
        return self.not_found(environ, start_response)

    def serve_obj(self, expr, server=JsonRpcServer):
        """
        import module and serve the object with desired server
        """
        module, expression = expr.split(':', 1)
        __import__(module)
        module = sys.modules[module]
        obj = eval(expression, module.__dict__)
        return server(obj())

    def index(self, environ, start_response):
        """This function will be mounted on "/"
        """
        resp = Response(
            content_type='text/plain',
            body="Service Index, here!")

        return resp(environ, start_response)

    def not_found(self, environ, start_response):
        """Called if no URL matches."""
        req = Request(environ)
        if req.method == 'POST':
            resp = Response(
                status=500,
                content_type='application/json',
                body=dumps(dict(
                    result=None,
                    error='Path Not Found',
                    id=1)))
        else:
            resp = Response(
                status=500,
                content_type='text/plain',
                body="Path Not Found")
        return resp(environ, start_response)  #

    def server_map(self, server_name):
        """
        Map server name to a particular class name
        :param server_name: name of the server
        :type server_name: str
        :returns: server
        :rtype: classobj
        """
        return self.server_mapping.get(server_name)


def run_server(setting):
    parser = optparse.OptionParser(
        usage='%prog [OPTIONS] MODULE:EXPRESSION')
    parser.add_option(
        '-p', '--port', default='9999',
        help='Port to serve on (default 9999)')
    parser.add_option(
        '-H', '--host', default='127.0.0.1',
        help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    options, args = parser.parse_args()
    server = simple_server.make_server(options.host,
                                       int(options.port), App(setting))
    print 'Serving on http://%s:%s' % (options.host, options.port)
    server.serve_forever()


def run_gunicorn_server(app_name):
    parser = optparse.OptionParser(
        usage='%prog [OPTIONS] MODULE:EXPRESSION')
    parser.add_option(
        '-p', '--port', default='9999',
        help='Port to serve on (default 9999)')
    parser.add_option(
        '-H', '--host', default='127.0.0.1',
        help='Host to serve on (default localhost; 0.0.0.0 to make public)')
    parser.add_option(
        '-W', '--workers', default=str(cpu_count() * 2 + 1),
        help='Number of gunicorn workers')
    options, _ = parser.parse_args()

    cmd = "gunicorn --workers=%s %s -b %s:%s -k sync" % \
        (options.workers, app_name, options.host, options.port)
    print 'Serving on http://%s:%s' % (options.host, options.port)
    subprocess.call(cmd.split(" "))
