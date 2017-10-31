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
import pymongo
from concurrent import futures


class FutureSense():
    def __init__(self, user, sandbox=False):
        self.access_token = ''
        self.refresh_token = ''
        self.client_id = os.environ['DEX_CLIENT_ID']
        self.client_secret = os.environ['DEX_CLIENT_SECRET']
        #self.redirect_uri = '34.215.61.65'
        self.redirect_uri = 'http://theglucoseguardian.com/callback'

        self.sandbox = sandbox
        self.headers = {}

        self.connect()

        self.mc = pymongo.MongoClient()  # Connect to the MongoDB server
        self.db = self.mc['future_sense']  # Use the 'future_sense' DB
        self.docs = self.db['docs'] # Use collection 'docs'

        # open the list of users (in username:authcode format) to get the
        # authorization code for the current user
        with open('users.csv', 'r') as f:
            self.users = ast.literal_eval(f.read())
        self.currentuser = user
        self.authcode = self.users[self.currentuser]

        # Get initial authcode
        self.auth_time = pd.datetime.now()
        self.auth_life = dt.timedelta(seconds=540)

        self.get_auth()


    def connect(self):
        '''
        Create a new connection object or reset it
        '''
        # set the connection URL based on whether we are using the
        # sandbox environment or production data
        if self.sandbox:
            self.conn = http.HTTPSConnection("sandbox-api.dexcom.com")
        else:
            self.conn = http.HTTPSConnection("api.dexcom.com")


    def get_auth(self):
        '''
        Connects to the API to request an access token, enabling queries
        for user data
        '''
        self.connect()

        payload = "client_secret=" + self.client_secret + "&client_id=" + self.client_id + "&code=" + self.authcode + "&grant_type=authorization_code&redirect_uri=" + self.redirect_uri

        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache"
            }

        while True:
            try:
                self.conn.request("POST", "/v1/oauth2/token", payload, headers)
                res = self.conn.getresponse()
                data = res.read()
            except http.CannotSendRequest:
                print("Resetting connection.")
                self.connect()
            break

        result = ast.literal_eval(data)
        print(result)
        self.access_token = result['access_token']
        self.refresh_token = result['refresh_token']
        self.headers = {'authorization': "Bearer " + self.access_token}

        self.auth_time = pd.datetime.now()


    def keepalive(self):
        '''
        Refresh the authorization token if it is close to expiring (tokens
        expire after 10 minutes, this will refresh after 9 minutes). Only works
        when program is running continuously - if token has expired, call get_auth() method to get a new token.
        '''
        if pd.datetime.now() > (self.auth_time + dt.timedelta(seconds=599)):
            self.get_auth()
        else:
            self.connect()

            payload = "client_secret=" + self.client_secret + "&client_id=" + self.client_id + "&refresh_token=" + self.refresh_token + "&grant_type=refresh_token&redirect_uri=" + self.redirect_uri

            headers = {
                'content-type': "application/x-www-form-urlencoded",
                'cache-control': "no-cache"
                }

            while True:
                try:
                    self.conn.request("POST", "/v1/oauth2/token", payload, headers)
                    res = self.conn.getresponse()
                    data = res.read()
                except http.CannotSendRequest:
                    print("Resetting connection.")
                    self.connect()
                break

            result = ast.literal_eval(data)
            self.access_token = result['access_token']
            self.refresh_token = result['refresh_token']
            self.headers = {'authorization': "Bearer " + self.access_token}

            self.auth_time = pd.datetime.now()


    def checktoken(self):
        print("Checking Token")
        if pd.datetime.now() > (self.auth_time + self.auth_life):
            print("Getting new token")
            self.keepalive()
            print("Token Recieved")
            time.sleep(1)
        print("No need to refresh")


    def groups(self, num_subs, d):
        d = ast.literal_eval(d)
        size = (len(d) / num_subs)
        if len(d) % num_subs != 0:
            size += 1
        result = []
        for i in range(num_subs):
            result.append(d[i*size:(i+1)*size])
        return result


    def get_egvs(self, startday=None, incr=7, reps=1):
        '''
        Get the Estimated Glucose Values (EGVs) for the specified date range,
        and stores the results in the DB
        '''
        if not startday:
            startday = self.find_last_record(recordType='egv')
        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        for i in range(reps):
            self.checktoken()
            self.connect()

            print("EGVS | Start Date:" + str(start + (plusX * i)) + " | End Date:" + str(start + (plusX * (i+1))))
            # sys.stdout.flush()

            while True:
                try:
                    self.conn.request("GET", "/v1/users/self/egvs" + "?startDate=" + str(start + (plusX * i)).replace(' ', 'T') + "&endDate=" + str(start + (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
                    res = self.conn.getresponse()
                    data = res.read()
                except http.BadStatusLine:
                    print("Bad connection, retrying in 10 seconds.")
                    time.sleep(10)
                    self.get_auth()
                    time.sleep(1)
                    continue
                break

            if int(res.status) != 200:
                try:
                    if ast.literal_eval(data.replace('null', '"null"'))['errors']['message'] == " - dates should not be in the future - ":
                        print("Invalid start date - beyond end of available data.")
                        return
                except:
                    raise ValueError("Request not successful.  Status =     {}".format(res.status))

            if data != None:
                units, rate, egvs = self.egv_decode(data)

            if egvs != None:
                executor = futures.ThreadPoolExecutor(20)
                future = [executor.submit(self.write_egvs, units, rate, group)
                            for group in self.groups(20, egvs)]
                futures.wait(future)
            else:
                print("Got no egvs!")


    def egv_decode(self, data):
        '''
        Unpack the data payload for EGVs and convert the list of records
        into individual records.
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


    def write_egvs(self, units, rate, egvs):
        '''
        Writes EGV results to the Mongo DB
        '''
        for egv in egvs:
            egv.update({'recordType': 'egv', 'units': units, 'rate': rate, 'user': self.currentuser})
            print egv
            self.docs.update_one(egv, {'$setOnInsert': egv}, upsert=True)


    def get_calibrations(self, startday=None, incr=7, reps=1):
        '''
        Get the calibration readings for the specified date range, and
        stores the results in the DB.

        Calibration readings are where the user physically tests their blood
        glucose level using a glucometer, and inputs the reading into the CGM
        software.
        '''
        if not startday:
            startday = self.find_last_record(recordType='calibration')
        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        for i in range(reps):
            self.checktoken()
            self.connect()

            print("CALIBRATIONS | Start Date:" + str(start + (plusX * i)) + " | End Date:" + str(start + (plusX * (i+1))))
            # sys.stdout.flush()

            while True:
                try:
                    self.conn.request("GET", "/v1/users/self/calibrations" + "?startDate=" + str(start + (plusX * i)).replace(' ', 'T') + "&endDate=" + str(start + (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
                    res = self.conn.getresponse()
                    data = res.read()
                except http.BadStatusLine:
                    print("Bad connection, retrying in 10 seconds.")
                    time.sleep(10)
                    self.get_auth()
                    time.sleep(1)
                    continue
                break
            if int(res.status) != 200:
                try:
                    if ast.literal_eval(data.replace('null', '"null"'))['errors']['message'] == " - dates should not be in the future - ":
                        print("Invalid start date - beyond end of available data.")
                        return
                except:
                    raise ValueError("Request not successful.  Status =     {}".format(res.status))

            if data != None:
                calibs = self.calib_decode(data)
            if calibs != None:
                executor = futures.ThreadPoolExecutor(5)
                future = [executor.submit(self.write_calibs, group)
                            for group in self.groups(5, calibs)]
                futures.wait(future)
            else:
                print("Got no calibrations!")


    def calib_decode(self, data):
        '''
        Unpack the data payload for calibrations and convert the list of records
        into individual records.
        '''
        calib_re = re.compile('(?<=:\[).+(?=\]})')
        try:
            calibs = calib_re.search(data).group().replace('null', '"null"')
        except:
            calibs = None

        return calibs


    def write_calibs(self, calibs):
        '''
        Write calibration records to Mongo DB
        '''
        for calib in calibs:
            calib.update({'recordType': 'calibration', 'user': self.currentuser})
            print calib
            self.docs.update_one(calib, {'$setOnInsert': calib}, upsert=True)


    def get_events(self, startday=None, incr=7, reps=1):
        '''
        Get event data for the specified date range, and stores the results
        in the DB.

        Event data includes records of when the user exercised, consumed food
        (recorded as grams of carbohydrates), consumed alcohol, or experienced
        stress - all of which can have an impact on glucose levels.
        '''
        if not startday:
            startday = self.find_last_record(recordType='event')
        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        for i in range(reps):
            self.checktoken()
            self.connect()

            print("EVENTS | Start Date:" + str(start + (plusX * i)) + " | End Date:" + str(start + (plusX * (i+1))))
            # sys.stdout.flush()

            while True:
                try:
                    self.conn.request("GET", "/v1/users/self/events" + "?startDate=" + str(start + (plusX * i)).replace(' ', 'T') + "&endDate=" + str(start + (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
                    res = self.conn.getresponse()
                    data = res.read()
                except http.BadStatusLine:
                    print("Bad connection, retrying in 10 seconds.")
                    time.sleep(10)
                    self.get_auth()
                    time.sleep(1)
                    continue
                break
            if int(res.status) != 200:
                try:
                    if ast.literal_eval(data.replace('null', '"null"'))['errors']['message'] == " - dates should not be in the future - ":
                        print("Invalid start date - beyond end of available data.")
                        return
                except:
                    raise ValueError("Request not successful.  Status =     {}".format(res.status))

            if data != None:
                events = self.event_decode(data)
            if events != None:
                executor = futures.ThreadPoolExecutor(10)
                future = [executor.submit(self.write_events, group)
                            for group in self.groups(10, events)]
                futures.wait(future)

            else:
                print("Got no events!")


    def event_decode(self, data):
        '''
        Unpack the data payload for events and convert the list of records
        into individual records.
        '''
        events_re = re.compile('(?<=:\[).+(?=\]})')
        try:
            events = events_re.search(data).group().replace('null', '"null"')
        except:
            events = None

        return events


    def write_events(self, events):
        '''
        Write event records to Mongo DB
        '''
        for event in events:
            event.update({'recordType': 'event', 'user': self.currentuser})
            print event
            self.docs.update_one(event, {'$setOnInsert': event}, upsert=True)


    def get_bounds(self, startday=None, incr=7):
        '''
        Get user devices and preferences
        '''
        if not startday:
            startday = self.find_last_record(recordType='egv')
        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        self.checktoken()
        self.connect()

        print("Bounds:")

        while True:
            try:
                self.conn.request("GET", "/v1/users/self/devices" + "?startDate=" + str(start).replace(' ', 'T') + "&endDate=" + str(start + plusX).replace(' ', 'T'), headers=self.headers)
                res = self.conn.getresponse()
                data = res.read()
            except http.BadStatusLine:
                print("Bad connection, retrying in 10 seconds.")
                time.sleep(10)
                self.get_auth()
                time.sleep(1)
                continue
            break
        if int(res.status) != 200:
            try:
                if ast.literal_eval(data.replace('null', '"null"'))['errors']['message'] == " - dates should not be in the future - ":
                    print("Invalid start date - beyond end of available data.")
                    return
            except:
                raise ValueError("Request not successful.  Status =     {}".format(res.status))

        if data != None:
            high, low = self.device_decode(data)

        self.write_bounds(high, low)


    def bounds_decode(self, data):
        high_re = re.compile('(?<=:\"high","value":)\d+(?=,"unit")')
        try:
            high = int(high_re.search(data).group().replace('null', '"null"'))
        except:
            high = 200

        low_re = re.compile('(?<=:\"low","value":)\d+(?=,"unit")')
        try:
            low = int(low_re.search(data).group().replace('null', '"null"'))
        except:
            low = 80

        return high, low


    def write_bounds(self, high, low):
        bounds = {'recordType': 'bounds', 'user': self.currentuser, 'high': high, 'low': low}
        print bounds
        self.docs.update_one(bounds, {'$setOnInsert': bounds}, upsert=True)


    def get_all(self, all_startday=None, all_incr=7, all_reps=1):
        self.get_egvs(startday=all_startday, incr=all_incr, reps=all_reps)
        self.get_calibrations(startday=all_startday, incr=all_incr, reps=all_reps)
        self.get_events(startday=all_startday, incr=all_incr, reps=all_reps)
        self.get_bounds(startday=all_startday, incr=all_incr)

    def find_last_record(self, recordType):
        try:
            end_date = self.docs.find_one({'user': self.currentuser, 'recordType': recordType}, projection={'displayTime': True, '_id': False}, sort=[('displayTime', pymongo.DESCENDING)])
            return pd.Timestamp(end_date['displayTime']).date()
        except:
            return '1/1/2015'
