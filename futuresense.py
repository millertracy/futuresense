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


class FutureSense():
    def __init__(self, user, sandbox=False):
        self.access_token = ''
        self.refresh_token = ''
        self.client_id = os.environ['DEX_CLIENT_ID']
        self.client_secret = os.environ['DEX_CLIENT_SECRET']
        self.redirect_uri = '34.215.61.65'

        self.sandbox = sandbox
        self.headers = {}

        # set the connection URL based on whether we are using the
        # sandbox environment or production data
        if self.sandbox:
            self.conn = http.HTTPSConnection("sandbox-api.dexcom.com")
        else:
            self.conn = http.HTTPSConnection("api.dexcom.com")

        self.mc = pymongo.MongoClient()  # Connect to the MongoDB server using default settings
        self.db = self.mc['future_sense']  # Use (or create) a database called 'future_sense'
        self.docs = self.db['docs'] # Use (or create) a collection called 'docs'

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


    def get_auth(self):
        '''
        Connects to the API to request an access token, enabling queries
        for user data
        '''

        payload = "client_secret=" + self.client_secret + "&client_id=" + self.client_id + "&code=" + self.authcode + "&grant_type=authorization_code&redirect_uri=" + self.redirect_uri

        headers = {
            'content-type': "application/x-www-form-urlencoded",
            'cache-control': "no-cache"
            }

        self.conn.request("POST", "/v1/oauth2/token", payload, headers)

        res = self.conn.getresponse()
        data = res.read()

        result = ast.literal_eval(data)
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

            payload = "client_secret=" + self.client_secret + "&client_id=" + self.client_id + "&refresh_token=" + self.refresh_token + "&grant_type=refresh_token&redirect_uri=" + self.redirect_uri

            headers = {
                'content-type': "application/x-www-form-urlencoded",
                'cache-control': "no-cache"
                }

            self.conn.request("POST", "/v1/oauth2/token", payload, headers)

            res = conn.getresponse()
            data = res.read()

            result = ast.literal_eval(data)
            self.access_token = result['access_token']
            self.refresh_token = result['refresh_token']
            self.headers = {'authorization': "Bearer " + self.access_token}

            self.auth_time = pd.datetime.now()


    def get_egvs(self, startday='01/01/2015', incr=90, reps=1):
        '''
        Get the Estimated Glucose Values (EGVs) for the specified date range,
        and stores the results in the DB
        '''
        if pd.datetime.now() > (self.auth_time + self.auth_life):
            self.keepalive()
            time.sleep(1)

        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        for i in range(reps):
            print("EGVS | Start Date:" + str(start + (plusX * i)) + " | End Date:" + str(start + (plusX * (i+1))))
            # sys.stdout.flush()
            self.conn.request("GET", "/v1/users/self/egvs" + "?startDate=" +
                              str(start + (plusX * i)).replace(' ', 'T') +
                              "&endDate=" + str(start +
                              (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
            res = self.conn.getresponse()
            data = res.read()

            units, rate, egvs = self.egv_decode(data)
            if egvs != None:
                for egv in ast.literal_eval(egvs):
                    egv.update({'recordType': 'egv', 'units': units, 'rate': rate, 'user': self.currentuser})
                    if not self.docs.find_one(egv):
                        self.docs.insert_one(egv)

                    # print egv


    def get_calibrations(self, startday='01/01/2015', incr=90, reps=1):
        '''
        Get the calibration readings for the specified date range, and
        stores the results in the DB.

        Calibration readings are where the user physically tests their blood
        glucose level using a glucometer, and inputs the reading into the CGM
        software.
        '''
        if pd.datetime.now() > (self.auth_time + self.auth_life):
            self.keepalive()
            time.sleep(1)

        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        for i in range(reps):
            print("CALIBRATIONS | Start Date:" + str(start + (plusX * i)) + " | End Date:" + str(start + (plusX * (i+1))))
            # sys.stdout.flush()
            self.conn.request("GET", "/v1/users/self/calibrations" + "?startDate=" +
                              str(start + (plusX * i)).replace(' ', 'T') +
                              "&endDate=" + str(start +
                              (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
            res = self.conn.getresponse()
            data = res.read()

            calibs = self.calib_decode(data)
            if calibs != None:
                for calib in ast.literal_eval(calibs):
                    calib.update({'recordType': 'calibration', 'user': self.currentuser})
                    if not self.docs.find_one(calib):
                        self.docs.insert_one(calib)

                    # print calib


    def get_events(self, startday='01/01/2015', incr=90, reps=1):
        '''
        Get event data for the specified date range, and stores the results
        in the DB.

        Event data includes records of when the user exercised, consumed food
        (recorded as grams of carbohydrates), consumed alcohol, or experienced
        stress - all of which can have an impact on glucose levels.
        '''
        if pd.datetime.now() > (self.auth_time + self.auth_life):
            self.keepalive()
            time.sleep(1)

        start = pd.Timestamp(startday)
        plusX = dt.timedelta(days=incr)

        for i in range(reps):
            print("EVENTS | Start Date:" + str(start + (plusX * i)) + " | End Date:" + str(start + (plusX * (i+1))))
            # sys.stdout.flush()
            self.conn.request("GET", "/v1/users/self/events" + "?startDate=" +
                              str(start + (plusX * i)).replace(' ', 'T') +
                              "&endDate=" + str(start +
                              (plusX * (i+1))).replace(' ', 'T'), headers=self.headers)
            res = self.conn.getresponse()
            data = res.read()

            events = self.event_decode(data)
            if events != None:
                for event in ast.literal_eval(events):
                    event.update({'recordType': 'event', 'user': self.currentuser})
                    if not self.docs.find_one(event):
                        self.docs.insert_one(event)

                    # print event

    def get_all(self, all_startday='01/01/2015', all_incr=90, all_reps=1):
        self.get_egvs(startday=all_startday, incr=all_incr, reps=all_reps)
        self.get_calibrations(startday=all_startday, incr=all_incr, reps=all_reps)
        self.get_events(startday=all_startday, incr=all_incr, reps=all_reps)

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

fs = FutureSense(user='sandbox5', sandbox=True)

fs.get_all(all_startday='1/1/2016', all_reps=4)
