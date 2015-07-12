# -*- coding: utf-8 -*-
# Copyright (c) 2015 joehand
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import csv
from datetime import datetime, date
import logging
from operator import itemgetter
import requests
import time


from pelican import signals


logger = logging.getLogger(__name__)

class Gdocs_Sheet(object):
    """
    Google Docs
    Init downloads from public html and returns text content
    Process creates list of data w/ a dict per row
    """

    def __init__(self, gen, url, name='default'):
        self.content = None
        self.gen = gen
        self.name = name
        #github_url = GITHUB_API.format(self.gen.settings['GITHUB_USER'])
        try:
            r = requests.get(url)
            c = r.text
            c = ''.join([i if ord(i) < 128 else ' ' for i in c]) # replace ascii chars
        except:
            logger.warning("unable to open {0}".format(url))
            return
        self.content = c

    def process(self):
        if self.content is None:
            return []
        lines = self.content.splitlines()
        header = [h.strip() for h in lines[0].split(',')] #trim header
        data = list(csv.DictReader(lines[1:], fieldnames=header))
        return data

class Gdocs_Coffee(Gdocs_Sheet):
    """
    Special processing for coffee sheet
    """
    def __init__(self, *args, **kwargs):
        self.max_cups = 0
        self.intervals = ((5,7),(7,9),(9,11),(11,13),(13,15),(15,17))
        super(Gdocs_Coffee, self).__init__(*args, **kwargs)

    def process(self):
        data = super(Gdocs_Coffee, self).process()
        clean_data = {}
        for item in data:
            date_fmt = "%B %d, %Y at %I:%M%p"
            date_time = time.strptime(item['Date_Time'], date_fmt)
            delta = date.today() - datetime.strptime(item['Date_Time'], date_fmt).date()
            days_ago = delta.days
            hour = (float(time.strftime("%H", date_time)) +
                        float(time.strftime("%M", date_time))/60)

            clean_data.setdefault(days_ago,[0 for i in self.intervals])
            for i,interval in enumerate(self.intervals):
                if interval[0] < hour < interval[1]:
                    clean_data[days_ago][i] += 1
                    if clean_data[days_ago][i] > self.max_cups:
                        self.max_cups = clean_data[days_ago][i]
                    continue
        # print(clean_data)
        no_data = []
        for day in range(0,31):
            if day not in clean_data:
                clean_data[day] = [0 for i in self.intervals]
                no_data.append(day)
        return {
            'max' : self.max_cups,
            'intervals': self.intervals,
            'data': clean_data,
            'no_data':no_data
        }


def initialize(gen):
    if not 'GDOCS' in gen.settings.keys():
        logger.warning('GDOCS not set')
    else:
        gen.plugin_sheets = []
        for sheet in gen.settings['GDOCS']:
            name = sheet['name']
            if name == 'coffee':
                gen.plugin_sheets.append(
                    (name,Gdocs_Coffee(gen, sheet['url'],name=name))
                )
            else:
                gen.plugin_sheets.append(
                    (name,Gdocs_Sheet(gen, sheet['url'],name=name))
                )

def fetch(gen, metadata):
    gen.context['gdocs_data'] = {}
    for name, obj in gen.plugin_sheets:
        data = obj.process()
        gen.context['gdocs_data'][name] = data


def register():
    signals.article_generator_init.connect(initialize)
    signals.article_generator_context.connect(fetch)