# -*- coding: utf-8 -*-
from instagram.client import InstagramAPI
from pymongo import MongoClient
from collections import Counter
import unicodedata
import calendar
import datetime
import time
import math

###########################################################################
###########################################################################
###########################################################################
#CONFIDENTIAL SCRIPT - livloo.com
#Instagram Location Posts Scraper
#Version 1.0
#Description: scrape recent instagram posts to a mongodb database
###########################################################################
###########################################################################
###########################################################################

def main():
    api = InstagramAPI(client_id='1ed75e7649544ac5b1aacd2a1d6db2b1',
                       client_secret='1b78cda37723445b85f5c6da25469611')

    instaScraper(api, 39.2835, -76.6099, days=4, xDistance=10, yDistance=10)


#=========================================================================#
#instaScraper: scrape instagram based on a starting lat/lng, distance,     #
#              and days. Also add the data to a mongodb database           #
#                                                                          #
#==========================================================================#
def instaScraper(api, startLat, startLng, days, xDistance, yDistance):

    #Tracks position
    x = 0
    y = 0

    #shift position
    xShift = 1.5
    yShift = 2

    #max position
    xDistance = xDistance * 1000 #Convert the total km to m
    yDistance = yDistance * 1000 #Convert the total km to m

    #size: "radius" that gets sent to instagram
    size = 1000

    while (y <= yDistance):
        while (x <= xDistance):

            #update the lat and lng
            newLat = shiftLat(startLat, y)
            newLng = shiftLng(startLat, startLng, x)
            print str(newLat) + ',' + str(newLng)

            #generate the posts
            generatePosts(api, newLat, newLng, days, size)

            #update x coordinate
            x = x + size * xShift

        #reset x to 0
        x = 0

        #update y coordinate
        y = y + size * yShift


#==========================================================================#
#generatePosts: scrapes all posts within a specific 1km zone until the     #
#               designated time in the past is reached.                    #
#==========================================================================#
def generatePosts(api, userLat, userLng, days, sizeinM):

    #Initialize timestamp with current time
    timestamp = getCurrentTime();

    #Get the time difference
    goalTime = getTimeDifference(days)

    #Loop until the last post exceeds the goal time
    while (timestamp > goalTime):

        try:

            rawPosts = api.media_search(distance=1000, count=100, lat=userLat, lng=userLng, max_timestamp=timestamp)

        except InstagramAPIError, I:
            rawPosts = api.media_search(distance=1000, count=100, lat=userLat, lng=userLng, max_timestamp=timestamp)
            sleep(30)

        #parse the posts to a formatted python array
        posts = parsePosts(rawPosts)

        #break if no posts exist
        if (len(posts) == 0 or len(posts) == 1):
            goalTime = timestamp
        else:
            #Get the last timestamp
            timestamp = posts[len(posts)-1]["time"]

        #insert posts array into a mongodb database collection
        insertPostsMongo(posts)


#==========================================================================#
#parsePosts: parses a single request of posts into our custom array and    #
#            performs important parsing/cleaning operations.               #
#==========================================================================#
def parsePosts(rawPosts):

    posts = []

    for media in rawPosts:

        try:

            post = {'type': "", 'id': 1, 'time': 1, 'media_url': "",
                    'text': "", 'tags': {}, 'numTags': 0, 'username': "", 'fullname': "",
                    'user_pic': "", 'location_id': 1, 'location_name': "", 'location': [1,1]}

            #post id
            post["id"] = media.id
            #print post["time"]

            #time created
            post["time"] = datetime_to_timestamp(media.created_time)
            #print post["time"]

            #type of media (photo/video)
            post["type"] = media.type
            #print post["type"]

            #location id of post
            post["location_id"] = media.location.id
            #print post["location_id"]

            #location id of post
            post["location_name"] = media.location.name
            print post["location_name"]

            #lat/lng of post
            post["location"][0] = media.location.point.latitude
            post["location"][1] = media.location.point.longitude
            #print str(post["location"][0]) + ', ' + str(post["location"][1])

            #username
            post["username"] = media.user.username
            #print post["username"]

            #fullname
            post["fullname"] = media.user.full_name
            #print post["fullname"]

            #userpic
            post["user_pic"] = media.user.profile_picture
            #print post["user_pic"]

            #media url
            post["media_url"] = media.images['low_resolution'].url
            #print post["media_url"]

            try:
                #text of post
                post["text"] = media.caption.text
                #print post["text"]

                #tags generated from text
                post["tags"] = Counter(textToTags(post["text"]))
                #print post["tags"]

            except AttributeError, a:
                post["text"] = ""
                #print 'No Text Associated with post'

            posts.append(post)

            print media.link

            print ('===========================================================')


        except UnicodeEncodeError, e:
            #print 'POST NOT IN ENGLISH'
            print ''

    return posts


#==========================================================================#
#insertPostsMongo: inserts a formatted posts array to a MongoDB            #
#                                                                          #
#==========================================================================#
def insertPostsMongo(posts):

    #Initialize the database and collection
    client = MongoClient('localhost', 27017)
    db = client.test
    collection = db.locations6

    #Loop posts and insert into database
    for p in posts:

        if collection.find({'insta_id':p['location_id']}).count() > 0:


            #Find and update the tags
            query = collection.find({'insta_id':p['location_id']})

            #Initialize some variables
            myTag = Counter({})
            #Only will loop once
            for location in query:
                myTag = Counter(location['tags'])
            myTag = myTag + Counter(p['tags'])


            #update tags, numPosts, amd insert the post
            collection.update_one({
              'insta_id': p['location_id']
            },{
              '$set': {
                'tags':myTag
              },
                '$inc': {
                  'numPosts': 1
               },
                '$addToSet':{'posts':p}
            })


        else:
            #make new location
            location = createLocationArray(p)
            collection.insert_one(location)

def createLocationArray(post):
    return {'insta_id': post['location_id'], 'id': 1, 'name': post['location_name'], 'location': post['location'], 'tags': post['tags'], 'posts': [post], 'numPosts': 1}




#HELPER FUNCTIONS
#########################################################################################

####################################################
#Parse a string to tags and eliminate common words
####################################################
def textToTags(text):

    import re
    regex = re.compile('[^a-zA-Z ]')
    text = regex.sub('', text)
    from nltk.corpus import stopwords
    s=set(stopwords.words('english'))

    return filter(lambda w: not w in s,text.split())

####################################################
#Finds the most common words in a string
####################################################
def mostCommonWords(text):
    from collections import Counter
    print Counter(text.split()).most_common()


#####################################################
#Convert datetime to time stamp
#####################################################
def datetime_to_timestamp(dt):
    return calendar.timegm(dt.timetuple())

#####################################################
#Get time difference
#####################################################
def getTimeDifference(days):
    currentTime = int(time.time())
    pastTime = daysToSeconds(days)
    goalTime = currentTime - pastTime
    return goalTime

#####################################################
#Get current unix timestamp
#####################################################
def getCurrentTime():
    return calendar.timegm(time.gmtime())


#####################################################
#Convert days to seconds
#####################################################
def daysToSeconds(days):
    return days * 24 * 60 * 60


#####################################################
#Get a new lat
#####################################################
def shiftLat(lat, offset):

     #Earth’s radius, sphere
     R=6378137

     #Coordinate offsets in radians
     dLat = float(offset)/R

     #OffsetPosition, decimal degrees
     latNew = lat + dLat * 180/math.pi

     return latNew

#####################################################
#Get a new lng
#####################################################
def shiftLng(lat, lng, offset):

     #Earth’s radius, sphere
     R=6378137

     #Coordinate offsets in radians
     dLng = float(offset)/(R*math.cos(math.pi*lat/180))

     #OffsetPosition, decimal degrees
     lngNew = lng + dLng * 180/math.pi

     return lngNew


main()
