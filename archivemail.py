#! /usr/bin/python3.4

import argparse
import datetime
import logging
import logging.handlers
import pickle
import json

import pymongo
from redis import StrictRedis

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Archiver .')
    parser.add_argument('-i','--instance', help='Instance Num of this script ', required=True)
    args = parser.parse_args()
    argsdict = vars(args)
    instance = argsdict['instance']

    FILESIZE=1024*1024*1024 #1MB
    logger = logging.getLogger('emailarchiver'+instance)
    formatter = logging.Formatter('EMAIL ARCHIVER-['+instance+']:%(asctime)s %(levelname)s - %(message)s')
    hdlr = logging.handlers.RotatingFileHandler('/var/tmp/emailarchiver_'+instance+'.log', maxBytes=FILESIZE, backupCount=10)
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.DEBUG)

    try:
        conn=pymongo.MongoClient()
        print ("Connected successfully!!!")
    except pymongo.errors.ConnectionFailure as e:
        print ("Could not connect to MongoDB: %s" % e )

    db = conn.inbounddb.mailBackup

    db.ensure_index("Expiry_date", expireAfterSeconds=0)

    rclient = StrictRedis()

    mailarchivebackup = 'mailarchivebackup_' + instance
    while True:
        if (rclient.llen(mailarchivebackup)):
            item = rclient.brpop (mailarchivebackup)
            message = pickle.loads (item[1])
            jsondata = json.loads(message)
            logger.info("Getting Mails from {}".format(mailarchivebackup))
            utc_timestamp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            db.insert( {'from':jsondata['fa'], 'Expiry_date' : utc_timestamp, 'inboundJson':message } )
        else:
            item = rclient.brpoplpush('mailarchive', mailarchivebackup)
            message = pickle.loads(item)
            logger.info("Getting Mails from {}".format('mailarchive'))
            utc_timestamp = datetime.datetime.utcnow() + datetime.timedelta(days=30)
            jsondata = json.loads(message)
            db.insert( {'from':jsondata['fa'], 'Expiry_date' : utc_timestamp, 'inboundJson':message } )
            logger.info ('len of {} is : {}'.format(mailarchivebackup, rclient.llen(mailarchivebackup)))
            rclient.lrem(mailarchivebackup, 0, item)
            logger.info ('len of {} is : {}'.format(mailarchivebackup, rclient.llen(mailarchivebackup)))
