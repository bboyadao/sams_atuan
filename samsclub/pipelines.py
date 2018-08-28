# -*- coding: utf-8 -*-
import json


class SamsclubPipeline(object):
    """
    receive full detail of product then insert to result.json

    """

    def open_spider(self, spider):
        self.file = open(f'result.json', 'w')

    def close_spider(self, spider):
        self.file.close()

    def process_item(self, item, spider):
        line = json.dumps(dict(item)) + "\n"
        self.file.write(line)
        return item
