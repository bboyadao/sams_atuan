from bs4 import BeautifulSoup
import os
from ..settings import BASE_DIR
from loginform import fill_login_form
import time
import datetime
import re
import requests
import json
from yattag import Doc
from yattag import indent
import scrapy
from scrapy import signals
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser
from scrapy.xlib.pydispatch import dispatcher
import webbrowser


def get_item_links():
    input_dir = os.path.join(BASE_DIR, 'input')
    items_path = os.path.join(input_dir, 'items.txt')
    with open(items_path, 'r') as f:
        links = f.readlines()
    return links


class Each(scrapy.Spider):
    name = 'colect_item'
    allowed_domains = ['samsclub.com']
    start_urls = get_item_links()
    custom_settings = {
        'ITEM_PIPELINES': {
            "samsclub.pipelines.SamsclubPipeline": 1
        }
    }

    login_url = "https://www.samsclub.com/sams/account/signin/login.jsp"
    user = 'vikvikllco@gmail.com'
    password = 'pijorro88'

    def start_requests(self):
        yield scrapy.Request(self.login_url, self.parse_login)

    def parse_login(self, response):
        data, url, method = fill_login_form(response.url, response.body,
                                            self.user, self.password)
        return scrapy.FormRequest(url, formdata=dict(data),
                                  method=method, callback=self.start_crawl)

    def start_crawl(self, response):
        cookieJar = response.meta.setdefault('cookie_jar', CookieJar())
        cookieJar.extract_cookies(response, response.request)

        for url in self.start_urls:
            ZIP_CODE = 33131
            TIME = str(int(time.time() * 1000))
            title, product_id, sku_id, status, price = self.get_detail(
                url.rstrip())
            get_shipping_url = f"https://www.samsclub.com/sams/shop/product/moneybox/shippingDeliveryInfo.jsp?zipCode={ZIP_CODE}&productId={product_id}&skuId={sku_id}&status={status}&isSelectedZip=true&isLoggedIn=true&_={TIME}"

            item = {
                "title": title,
                "status": status,
                "price": price,
                "product_id": product_id,
                "sku_id": sku_id
            }
            request = scrapy.Request(
                get_shipping_url, meta={"item": item, "cookie_jar": cookieJar}, callback=self.parse)
            cookieJar.add_cookie_header(request)

            yield request

    def parse(self, response):
        item = response.meta['item']
        try:
            arrives = response.xpath(
                '//table/tbody/tr/td[1]/text()').extract_first().strip()
            try:
                cost = response.xpath(
                    '//table/tbody/tr/td[2]/span/text()').extract_first().strip()
            except:
                cost = response.xpath(
                    '//table/tbody/tr/td[2]/text()').extract_first().strip()
        except:
            arrives = ""
            cost = response.xpath(
                '//table/tbody/tr/td[1]/text()').extract_first().strip()
        item['arrives'] = arrives
        item['cost'] = cost

        # process to pretty look like
        re_title = BeautifulSoup(item['title'], 'html.parser')
        item['title'] = re_title.text.split("-")[0]

        yield item

    # actualy we can get data by requests. Sscrapy don't need to request and parse data, it take a double of time. We use re to handle data per each call.
    def get_detail(self, url):
        r = requests.get(url, timeout=5)
        title = re.search('<title>(.+?)</title>', r.text).group(0)
        product_id = re.search("'productId':'(.+?)'", r.text).group(1)
        sku_id = re.search("mainFormSku(.+?) ", r.text).group(1)
        status = re.search("data-onlinestatus=(.+?) ", r.text).group(1)
        price = re.search('itemprop=price>(.+?)<', r.text).group(1)

        return (title, product_id, sku_id, status, price)

    # handle for create Report HTML file when finish crawl's session

    def __init__(self):
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        output_dir = os.path.join(BASE_DIR, 'output')
        now = datetime.datetime.now()
        html_path = f'{datetime.date.today()}-{now.hour}-{now.minute}-{now.second}s.html'
        html_result = os.path.join(output_dir, html_path)
        with open(html_result, 'w') as f:
            f.write(self.export())
        webbrowser.open_new_tab('file://' + html_result)

    # Gen html code
    def export(self):
        doc, tag, text = Doc().tagtext()
        with open("result.json") as f:
            data = json.dumps(f.readlines())
            items = json.loads(data)
        with tag('html'):
            with tag('head'):
                doc.stag('meta', charset='utf-8')

                doc.stag('meta', name="viewport",
                         content='width=device-width, initial-scale=1')
                doc.stag('link', rel="stylesheet",
                         href="https://maxcdn.bootstrapcdn.com/bootstrap/4.1.3/css/bootstrap.min.css")
                with tag(
                        'script', src='https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js'):
                    pass

                with tag(
                        'script', src='https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.3/umd/popper.min.js'):
                    pass
                with tag(
                        'script', src='https://maxcdn.bootstrapcdn.com/bootstrap/4.1.3/js/bootstrap.min.js'):
                    pass

            with tag('body'):
                doc.attr(klass="container normal-style")
                with tag('h3', klass='breaking-news'):
                    text(f'Report With {len(items)} item(s) - ZIPCODE: 33131')
                with tag('table', klass='table table-striped'):
                    with tag('thead'):
                        with tag('tr'):
                            with tag('th', scope="col"):
                                doc.text('TITLE')
                            with tag('th', scope="col"):
                                doc.text('STOCK')
                            with tag('th', scope="col"):
                                doc.text('PRICE')
                            with tag('th', scope="col"):
                                doc.text('PRODUCT_ID')
                            with tag('th', scope="col"):
                                doc.text('SKU_ID')
                            with tag('th', scope="col"):
                                doc.text('SHIPPING_DATE')
                            with tag('th', scope="col"):
                                doc.text('SHIPPING_PRICE')

                    with tag('tbody'):
                        with tag('div'):
                            for item in items:
                                item = json.loads(item)
                                with tag('tr'):

                                    with tag('td'):
                                        doc.text(item['title'])
                                    with tag('td'):
                                        doc.text(item['status'])
                                    with tag('td'):
                                        doc.text(item['price'])
                                    with tag('td'):
                                        doc.text(item['product_id'])
                                    with tag('td'):
                                        doc.text(item['sku_id'])
                                    with tag('td'):
                                        doc.text(item['arrives'])
                                    with tag('td'):
                                        doc.text(item['cost'])

        return indent(doc.getvalue(),
                      indentation='    ',
                      newline='\r\n',
                      indent_text=True)
