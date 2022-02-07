import os
import redis
from werkzeug.urls import url_parse
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader
import psycopg2

class Shortly(object):

    def __init__(self, config):
        self.redis = redis.Redis(config['redis_host'], config['redis_port'], decode_responses=True)
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),autoescape=True)
        
        self.url_map = Map([
            Rule('/', endpoint='index'),
            Rule('/products', endpoint='products'),
            Rule("/products/<int:product_id>", endpoint="show_product")
        ])

    def on_index(self, request):
        return self.render_template('index.html')
    
    def on_products(self, request):
        conn = psycopg2.connect(database="hetpatel", user='hetpatel', password='', host='127.0.0.1', port= '5432')
        cursor = conn.cursor()
        cursor.execute("SELECT id,name,list_price from product_template where type='product'")
        result = cursor.fetchall()
        print(result)
        conn.commit()
        conn.close()
        return self.render_template('products.html', render_context={'product_data': result})

    def on_show_product(self, request, product_id):
        conn = psycopg2.connect(database="hetpatel", user='hetpatel', password='', host='127.0.0.1', port= '5432')
        cursor = conn.cursor()
        cursor.execute("SELECT * from product_template where id="+str(product_id))
        result = cursor.fetchall()
        print(result[0])
        conn.commit()
        conn.close()
        return self.render_template('product_detail.html', render_context={'product': result[0]})

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context.get('render_context')), mimetype='text/html')

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, f'on_{endpoint}')(request, **values)
        except HTTPException as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)


def create_app(redis_host='localhost', redis_port=8000, with_static=True):
    app = Shortly({
        'redis_host':       redis_host,
        'redis_port':       redis_port
    })
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static':  os.path.join(os.path.dirname(__file__), 'static')
        })
    return app

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 8000, app, use_debugger=True, use_reloader=True)