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
import base64
import re
import time
from random import random
from urlparse import urlparse

fake_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'UTF-8,*;q=0.5',
    'Accept-Encoding': 'gzip,deflate,sdch',
    'Accept-Language': 'en-US,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:13.0) Gecko/20100101 Firefox/13.0'
}


# DEPRECATED in favor of match1()
def r1(pattern, text):
    m = re.search(pattern, text)
    if m:
        return m.group(1)


def get_html(url):
    r = requests.get(url)
    return r.text

get_decoded_html = get_html

class SohuExtractor:

    def __init__(self, url):
        self.url = url

    def real_url(self, host, vid, tvid, new, clipURL, ck):
        url = 'http://'+host+'/?prot=9&prod=flash&pt=1&file='+clipURL+'&new='+new +'&key='+ ck+'&vid='+str(vid)+'&uid='+str(int(time.time()*1000))+'&t='+str(random())+'&rb=1'
        return json.loads(get_html(url))['url']

    def extract(self, meta, quality="highVid"):
        if re.match(r'http://share.vrs.sohu.com', self.url):
            vid = r1('id=(\d+)', url)
        else:
            html = get_html(self.url)
            vid = r1(r'\Wvid\s*[\:=]\s*[\'"]?(\d+)[\'"]?', html)
        assert vid

        infos = []
        if re.match(r'http://tv.sohu.com/', self.url):
            info = json.loads(get_decoded_html('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % vid))
            for qtyp in ["oriVid","superVid","highVid" ,"norVid","relativeId"]:
                hqvid = info['data'][qtyp]
                if hqvid != 0 and hqvid != vid :
                    info = json.loads(get_decoded_html('http://hot.vrs.sohu.com/vrs_flash.action?vid=%s' % hqvid))

                    host = info['allot']
                    prot = info['prot']
                    tvid = info['tvid']
                    urls = []
                    data = info['data']
                    title = data['tvName']
                    size = sum(data['clipsBytes'])
                    assert len(data['clipsURL']) == len(data['clipsBytes']) == len(data['su'])
                    if meta:
                        item = {
                            "quality": qtyp,
                            "totalDuration": data["totalDuration"],
                            "totalBytes": data["totalBytes"],
                            "clipsBytes": data["clipsBytes"],
                            "clipsDuration": data["clipsDuration"]
                            }
                        infos.append(item)
                        continue

                    if quality == qtyp:
                        for new,clip,ck, in zip(data['su'], data['clipsURL'], data['ck']):
                            clipURL = urlparse(clip).path
                            urls.append(self.real_url(host,hqvid,tvid,new,clipURL,ck))

                        item = {
                            "urls": urls,
                            "quality": qtyp,
                            "totalDuration": data["totalDuration"],
                            "totalBytes": data["totalBytes"],
                            "clipsBytes": data["clipsBytes"],
                            "clipsDuration": data["clipsDuration"]
                            }
                        return item


        return infos

class DetailInfoHtmlParser(HTMLParser.HTMLParser):

    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self.current_key = {"name": "", "deep": 0}
        self.detail = {}
        self.urls = []
        self.attr_url_name = False
        self.current_url = {}
        self.current_source = {}
        self.is_end = False

    def output(self):
        return self.detail

    def is_tag_start(self, tag, attrs, d_tag, d_variable, d_attr):
        return tag == d_tag and len(filter(lambda va: len(va) >= 2 and va[0] == d_variable and va[1] == d_attr, attrs)) == 1

    def get_attr_by(self, tag, attrs, d_tag, d_variable):
        if tag == d_tag:
            ret = filter(lambda va: len(va) >= 2 and va[0] == d_variable, attrs)
            if len(ret) == 1:
                return ret[0][1]
        return ""

    def add_sources(self, source, urls):
        u = filter(lambda url: url["site"]==source["site"], urls)
        if not self.detail.get("sources", None):
            self.detail["sources"] = []

        self.detail.setdefault("status", source["status"])

        s = {"site": source["site"], "name": source["title"], "icon": source["icon"], "status": source["status"]}
        s["episodes"] = []
        for i in u:
            s["episodes"].append({"url": i["url"], "title": i["name"]})
        self.detail["sources"].append(s)

    def handle_starttag(self, tag, attrs):
        if self.is_end:
            return
        if self.is_tag_start(tag, attrs, "li", "class", "base_name"):
            self.current_key["name"] = "base_name"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "base_pub"):
            self.current_key["name"] = "base_pub"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "base_what"):
            self.current_key["name"] = "base_what"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "p_thumb"):
            self.current_key["name"] = "p_thumb"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "li", "class", "long"):
            if not self.detail.get("actors", None):
                self.current_key["name"] = "long"
                self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "ul", "class", "linkpanel"):
            self.current_key["name"] = "linkpanel"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "ul", "class", "other"):
            self.current_key["name"] = "source"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "div", "class", "source  source_one"):
            self.current_key["name"] = "source_one"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "div", "class", "rating"):
            self.current_key["name"] = "rating"
            self.current_key["deep"] = 1
        elif self.is_tag_start(tag, attrs, "div", "class", "intro"):
            self.is_end = True
            return
        else:
            if self.current_key["deep"] > 0:
                self.current_key["deep"] += 1

        if self.current_key["name"] == "p_thumb" and self.current_key["deep"] > 1:
            img = self.get_attr_by(tag, attrs, "img", "src")
            if img != "":
                self.detail["thumb"] = img
        elif self.current_key["name"] == "linkpanel" and self.current_key["deep"] == 3:
            href = self.get_attr_by(tag, attrs, "a", "href")
            site = self.get_attr_by(tag, attrs, "a", "site")
            if href != "" and site != "":
                self.attr_url_name = True
                self.current_url = {"url": href, "site": site}
        elif self.current_key["name"] == "source_one" and self.current_key["deep"] > 1:
            site = self.get_attr_by(tag, attrs, "div", "name")
            title = self.get_attr_by(tag, attrs, "div", "title")
            src = self.get_attr_by(tag, attrs, "label", "_src")
            status = self.get_attr_by(tag, attrs, "input", "title")
            if site != "":
                self.current_source["site"] = site
            if title != "":
                self.current_source["title"] = title
            if status != "":
                self.current_source["status"] = status
            if src != "":
                self.current_source["icon"] = src
                self.add_sources(self.current_source, self.urls)
                self.current_source = {}

        elif self.current_key["name"] == "source" and self.current_key["deep"] > 1:
            site = self.get_attr_by(tag, attrs, "li", "name")
            title = self.get_attr_by(tag, attrs, "img", "title")
            src = self.get_attr_by(tag, attrs, "img", "src")
            status = self.get_attr_by(tag, attrs, "label", "title")
            if site != "":
                self.current_source["site"] = site
            if title != "":
                self.current_source["title"] = title
            if src != "":
                self.current_source["icon"] = src
            if status != "":
                self.current_source["status"] = status
                self.add_sources(self.current_source, self.urls)
                self.current_source = {}



    def handle_endtag(self, tag):
        if self.is_end:
            return
        if self.current_key["deep"] > 0:
            self.current_key["deep"] -= 1

    def handle_data(self, data):
        if self.is_end:
            return
        if self.current_key["deep"] > 1 and self.current_key["name"] == "base_name":
            self.detail["name"] = data.strip()
        elif self.current_key["deep"] >= 1 and self.current_key["name"] == "base_pub":
            self.detail["pub"] = data.strip()
        elif self.current_key["deep"] >= 1 and self.current_key["name"] == "base_what":
            self.detail["sum"] = data.strip()
        elif self.current_key["deep"] > 1 and self.current_key["name"] == "long":
            if data.strip() == "/" or data.strip() == "":
                return
            if self.detail.get("actors", None):
                self.detail["actors"].append(data)
            else:
                self.detail["actors"] = [data,]
        elif self.current_key["deep"] > 1 and self.current_key["name"] == "rating":
            self.detail.setdefault("rating", data)
        elif self.attr_url_name:
            self.current_url["name"] = data
            self.urls.append(self.current_url)
            self.attr_url_name = False
            self.current_url = {}


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
        response_str = json.dumps({"err":0, "msg":"", "data":parser.output()})
        self.set_header("Content-Length", str(len(response_str)))
        self.write(response_str)


class AnimeListHandler(tornado.web.RequestHandler):

    def get(self):
        r = requests.get("http://www.soku.com/channel/animelist_0_0_0_1_"+str(self.get_query_argument("page",1))+".html")
        parser = TeleListHtmlParser()
        parser.feed(r.text)
        parser.close()
        self.set_header('Content-Type', 'application/json')
        response_str = json.dumps({"err":0, "msg":"", "data":parser.output()})
        self.set_header("Content-Length", str(len(response_str)))
        self.write(response_str)


class DetailHandler(tornado.web.RequestHandler):

    def get(self, detail):
        r = requests.get("http://www.soku.com/detail/show/" + detail)
        parser = DetailInfoHtmlParser()
        parser.feed(r.text)
        parser.close()
        self.set_header('Content-Type', 'application/json')
        response_str = json.dumps({"err":0, "msg":"", "data":parser.output()})
        self.set_header("Content-Length", str(len(response_str)))
        self.write(response_str)

class VideosHandler(tornado.web.RequestHandler):
    '''Extract videos api

    https://youplay.avosapps.com/api/v1/videos/{base64 url}
    example:
        https://youplay.avosapps.com/api/v1/videos/aHR0cDovL3R2LnNvaHUuY29tLzIwMTUxMTAzL240MjUxNTgwMDQuc2h0bWw=
    '''

    def get(self, url):
        origin_url = base64.b64decode(url.split('/')[0])
        meta = int(self.get_query_argument("meta", "0"))
        quality = self.get_query_argument("quality", None)
        self.set_header('Content-Type', 'application/json')
        sohu = SohuExtractor(origin_url)
        response_str = json.dumps({"err":0, "msg":"", "data":sohu.extract(meta, quality)})
        self.set_header("Content-Length", str(len(response_str)))
        self.write(response_str)

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
    (r"/api/v1/detail/show/(.*)", DetailHandler),
    (r"/api/v1/channel/teleplaylist", TeleplayListHandler),
    (r"/api/v1/channel/animelist", AnimeListHandler)
], **settings)

app = tornado.wsgi.WSGIAdapter(application)


def main():
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()

if __name__ == '__main__':
    main()
