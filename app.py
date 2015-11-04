#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import tornado.ioloop
import tornado.web
import tornado.wsgi

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Hello, world")

class VideosHandler(tornado.web.RequestHandler):
    # https://youplay.avosapps.com/api/v1/videos/{base64 url}
    # example: https://youplay.avosapps.com/api/v1/videos/aHR0cDovL3R2LnNvaHUuY29tLzIwMTUxMTAzL240MjUxNTgwMDQuc2h0bWw=

    def get(self, url):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({"k1": url, "k2": [{"k": 1}, {"k2": "s"}]}))

settings = {"debug": True}
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/api/v1/videos/(.*)", VideosHandler),
], **settings)

app = tornado.wsgi.WSGIAdapter(application)

def main():
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
