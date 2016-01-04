#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os.path
import tornado.ioloop
import tornado.web
import tornado.wsgi
import HTMLParser
import requests
import json

class TeleListHtmlParser(HTMLParser.HTMLParser):

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.tele_list = []
        self.current_tele = {}
        self.current_key = {"name": "", "deep": 0}

    def output(self):
        return self.tele_list

    def is_tag_start(self, tag, attrs, d_tag, d_variable, d_attr):
        return tag == d_tag and len(filter(lambda va: len(va) >= 2 and va[0] == d_variable and va[1] == d_attr, attrs)) == 1

    def get_attr_by(self, tag, attrs, d_tag, d_variable):
        if tag == d_tag:
            ret = filter(lambda va: len(va) >= 2 and va[0] == d_variable, attrs)
            if len(ret) == 1:
                return ret[0][1]
        return ""

    def handle_starttag(self, tag, attrs):
        if self.is_tag_start(tag, attrs, "li", "class", "p_title"):
            self.current_key["name"] = "p_title"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "p_thumb"):
            self.current_key["name"] = "p_thumb"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "p_actor"):
            self.current_key["name"] = "p_actor"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "p_rating"):
            self.current_key["name"] = "p_rating"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "p_link"):
            self.current_key["name"] = "p_link"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "div", "class", "source source_one"):
            self.current_key["name"] = "source source_one"
            self.current_key["deep"] = 1
        else:
            if self.current_key["deep"] > 0:
                self.current_key["deep"] += 1

        if self.current_key["name"] == "p_thumb" and self.current_key["deep"] > 1:
            img = self.get_attr_by(tag, attrs, "img", "original")
            if img != "":
                self.current_tele["thumb"] = img
        elif self.current_key["name"] == "p_link" and self.current_key["deep"] > 1:
            link = self.get_attr_by(tag, attrs, "a", "href")
            if link != "":
                self.current_tele["detail"] = link
        elif self.current_key["name"] == "source source_one" and self.current_key["deep"] > 1:
            if self.current_tele.get("status", None):
                if self.current_tele.get("title", None):
                    self.tele_list.append(self.current_tele)
                    self.current_tele = {}
            else:
                status = self.get_attr_by(tag, attrs, "a", "status")
                if status != "" and self.current_tele.get("title", None):
                    self.current_tele["status"] = status


    def handle_endtag(self, tag):
        if self.current_key["deep"] > 0:
            self.current_key["deep"] -= 1
            # if self.current_key["deep"] > 0:
            #     print("handle_endtag: \n" + str(self.current_key))


    def handle_data(self, data):
        if self.current_key["deep"] > 1 and self.current_key["name"] == "p_title":
            self.current_tele["title"] = data
        elif self.current_key["deep"] > 1 and self.current_key["name"] == "p_actor":
            if self.current_tele.get("actors", None):
                self.current_tele["actors"].append(data)
            else:
                self.current_tele["actors"] = [data,]
        elif self.current_key["deep"] >= 1 and self.current_key["name"] == "p_rating":
            if self.current_tele.get("rating", None):
                self.current_tele["rating"] += data
            else:
                self.current_tele["rating"] = data


class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("index.html")


class APIHandler(tornado.web.RequestHandler):

    def get(self):
        self.write("Hello, world api")


class SearchHandler(tornado.web.RequestHandler):
    '''Search http://www.soku.com

    '''
    def get(self):
        self.write("Hello, world Search")


class TeleplayListHandler(tornado.web.RequestHandler):

    def get(self):
        r = requests.get("http://www.soku.com/channel/teleplaylist_0_0_0_1_"+str(self.get_query_argument("page",1))+".html")
        parser = TeleListHtmlParser()
        parser.feed(r.text)
        parser.close()
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({"err":0, "msg":"", "data":parser.output()}))


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
    (r"/api/v1/search", SearchHandler),
    (r"/api/v1/channel/teleplaylist", TeleplayListHandler)
], **settings)

app = tornado.wsgi.WSGIAdapter(application)


def main():
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
