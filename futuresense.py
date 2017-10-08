#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 28 08:38:09 2017

@author: djo
"""

import httplib as http
import ast
import time
import os
import sys
import datetime as dt
import json
import re
import pandas as pd


class FutureSense():
    def __init__(self, sandbox=False):
        self.access_token = ''
        self.refresh_token = ''
        self.client_id = os.environ['DEX_CLIENT_ID']
        self.client_secret = os.environ['DEX_CLIENT_SECRET']
        self.authcode = ''
        self.sandbox = sandbox
        self.headers = {}

        if self.sandbox:
            self.conn = http.HTTPSConnection("sandbox-api.dexcom.com")
        else:
            self.conn = http.HTTPSConnection("api.dexcom.com")


    def get_auth(self):
        '''
        Connects to the API to request an access token, enabling queries
        for user data
        '''

        payload = "client_secret=" + self.client_secret + "&client_id=" + self.client_id + "&code=" + self.authcode + "&grant_type=authorization_code&redirect_uri=34.215.61.65"

        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache"
            }

        self.conn.request("POST", "/v1/oauth2/token", payload, headers)

        res = self.conn.getresponse()
        data = res.read()

        result = ast.literal_eval(data)
        self.access_token = result['access_token']
        self.headers = {'authorization': "Bearer " + self.access_token}


    def keepalive(self):
        '''
        Continuously refresh the authorization connection every 9 minutes,
        until explicitly ordered to stop.
        '''
        pass


    def egvdecode(self, data):
        '''
        Unpack the data payload into units (str), rate of change (str), and
        EGVs list(dicts).
        ------------------------
        Watch for empty results like:
        {"unit":"mg/dL","rateUnit":"mg/dL/min","egvs":[]}
        '''
        # expected units = 'mg/dL'
        units_re = re.compile('(?<=\"unit\":\").+(?=\",\"rateUnit)')
        units = units_re.search(data).group()

        # expected rate = 'mg/dL/min'
        rate_re = re.compile('(?<=\"rateUnit\":\").+(?=\",\"egvs)')
        rate = rate_re.search(data).group()

        # gets EGVs as a list of dicts in str format
        egvs_re = re.compile('(?<=:\[).+(?=\]})')
        try:
            egvs = egvs_re.search(data).group().replace('null', '"null"')
        except:
            egvs = None

        return units, rate, egvs


    def eventdecode(self, data):
        events_re = re.compile('(?<=:\[).+(?=\]})')
        try:
            events = events_re.search(data).group().replace('null', '"null"')
        except:
            events = None

        return events


    def get_egvs(self, auth, startday='01/01/2015', incr=90, reps=1):
        self.authcode = auth

        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        self.get_auth()
        time.sleep(2)

        for i in range(reps):
            self.conn.request("GET", "/v1/users/self/egvs" + "?startDate=" +
                              str(start + (plusX * i)).replace(' ', 'T') +
                              "&endDate=" + str(start +
                              (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
            res = self.conn.getresponse()
            data = res.read()

            units, rate, egvs = self.egvdecode(data)
            if egvs != None:
                result = []
                for egv in ast.literal_eval(egvs):
                    egv.update({'recordType': 'egv', 'units': units, 'rate': rate})
                    result.append(egv)

                    # this will append a list of objects, not objects to the existing file
                    # need to correct so each entry is appended to the db individually
                    # also the file io is still fucked up
                with open('testdata.json', mode='r') as datafeed:
                    feeds = json.load(datafeed)
                    # print feeds
                with open('testdata.json', mode='w') as outfile:
                    json.load
                    print feeds
                    json.dump(feeds, outfile)

    def get_events(self, auth, startday='01/01/2015', incr=90, reps=1):
        self.authcode = auth

        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        self.get_auth()
        time.sleep(2)

        for i in range(reps):
            self.conn.request("GET", "/v1/users/self/events" + "?startDate=" +
                              str(start + (plusX * i)).replace(' ', 'T') +
                              "&endDate=" + str(start +
                              (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
            res = self.conn.getresponse()
            data = res.read()

            events = self.eventdecode(data)
            if events != None:
                for event in ast.literal_eval(events):
                    event.update({'recordType': 'event'})
                    print event


fs = FutureSense(sandbox=True)

fs.get_egvs(auth='authcode1', startday='9/1/2016', incr=.01)
fs.get_events(auth='authcode1', startday='9/1/2016', incr=1)
#fs.get_readings()
