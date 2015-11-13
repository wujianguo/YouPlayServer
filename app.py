#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os.path
import tornado.ioloop
import tornado.web
import tornado.wsgi

class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html")


class APIHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("Hello, world")


class SearchHandler(tornado.web.RequestHandler):
    '''Search http://www.soku.com

    '''
    def get(self):
        self.write("Hello, world")


class TeleplayListHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("Hello, world")


class VideosHandler(tornado.web.RequestHandler):
    '''Extract videos api

    https://youplay.avosapps.com/api/v1/videos/{base64 url}
    example:
        https://youplay.avosapps.com/api/v1/videos/aHR0cDovL3R2LnNvaHUuY29tLzIwMTUxMTAzL240MjUxNTgwMDQuc2h0bWw=
    '''

    def get(self, url):
        url = url.split('/')[0]
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({"k1": url, "k2": [{"k": 1}, {"k2": "s"}]}))


settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "public"),
    "template_path": os.path.join(os.path.dirname(__file__), "views"),
    "gzip": True,
    "debug": True
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/api/v1", APIHandler),
    (r"/api/v1/videos/(.*)", VideosHandler),
    ("r/api/v1/search", SearchHandler),
    ("r/api/v1/channel/teleplaylist", TeleplayListHandler)
], **settings)

app = tornado.wsgi.WSGIAdapter(application)


def main():
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
