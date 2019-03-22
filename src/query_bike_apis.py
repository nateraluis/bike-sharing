import requests 
import json
import pandas as pd
import datetime
import os
import psycopg2
import psycopg2.extras
import traceback

# TODO: also station information

def get_nextbike_locations ():

    # request data
    URL = "https://gbfs.nextbike.net/maps/gbfs/v1/nextbike_bn/en/free_bike_status.json"

    # sending get request and saving the response as response object 
    response = requests.get(url = URL) 
    try:
        r = response.json()
        nextbikes = []
        for i in range(len(r['data']['bikes'])):
            bike_id = int(r['data']['bikes'][i]['bike_id'])

             # single bike have no ID (?!); skip these bikes
            if not bike_id:
                continue
            lat = r['data']['bikes'][i]['lat']
            lon = r['data']['bikes'][i]['lon']
            nextbikes.append([bike_id, NEXTBIKE, query_date, lat,lon])
        return nextbikes
    except Exception as e:
        traceback.print_exc()
        # TODO: notify if error occurs
    

def get_lidlbike_locations():

    #Berlin lat lon
    radius_center_lat=52.520008
    radius_center_lon=13.404954

    # request data
    # api key
    key1 ='Bearer 2e5ddcc9a03f000d8c2d023d55d2bc49'
    key2 ='Bearer 60f9ca3996f5ee4bb8bc5ca8a25ad0af'

    # api-endpoint 
    URL = "https://api.deutschebahn.com/flinkster-api-ng/v1/bookingproposals"

    radius=10000 # radius in meter, max 10000 (10km)
    providernetwork=2
    expand='rentalObject'
    limit = 50

    offset = 0 # mit offset Blättern
    more_bikes = True
    key = key1

    lidlbikes = []
    while more_bikes:
        try:
        
            #header
            # note in header
            headers = {"Authorization": key, "Accept": "application/json"}

            # defining a params dict for the parameters to be sent to the API 
            PARAMS = {'lat':radius_center_lat, 'lon':radius_center_lon, 'radius':radius, 'providernetwork':providernetwork, 'expand':expand, 'limit':limit, 'offset':offset} 

            # sending get request and saving the response as response object 
            response = requests.get(url = URL, params = PARAMS, headers=headers) 

            # TODO error handling
            r = response.json()

            

            for i in range(len(r['items'])):
                bike_id = r['items'][i]['rentalObject']['providerRentalObjectId']
                
                # single bike have no ID (?!); skip these bikes
                if not bike_id:
                    continue

                lat = r['items'][i]['position']['coordinates'][0]
                lon = r['items'][i]['position']['coordinates'][1]
                lidlbikes.append([bike_id, LIDLBIKE, query_date, lat, lon])

            # get all paginations
            offset += 50
            if len(r['items']) < 50:
                more_bikes = False

            # 30 calls max per minute (then timeout)
            if (offset % 1500 == 0):
                if key == key1:
                    key = key2
                else: 
                    key = key1
        except Exception:
            traceback.print_exc()
            # TODO: notify if error occurs
        
    return lidlbikes

def get_mobike_locations():

    # TODO: fix empty request returns

    # request data
    URL = "http://app.mobike.com/api/nearby/v4/nearbyBikeInfo"
    plattform= '1'

    # header
    headers = {"plattform": plattform, \
        "Content-Type": "application/x-www-form-urlencoded", \
        "User-Agent" : "Mozilla/5.0 (Android 7.1.2; Pixel Build/NHG47Q) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.9 NTENTBrowser/3.7.0.496 (IWireless-US) Mobile Safari/537.36"}

    radius_centers = pd.read_csv("coordinates.csv")

    mobikes = []
    for i in range (radius_centers.shape[0]):
        # defining a params dict for the parameters to be sent to the API 
        PARAMS = {'latitude': radius_centers.iloc[i, 0], 'longitude': radius_centers.iloc[i, 1]}

        # sending get request and saving the response as response object 
        response = requests.get(url = URL, params = PARAMS, headers = headers) 

        #Todo error handling
        r = response.json()

        if r['code'] == 0:
           
            for i in range(len(r['bike'])):
                bike_id = r['bike'][i]['distId'][1:]
                lat = r['bike'][i]['distY']
                lon = r['bike'][i]['distX']
                mobikes.append([bike_id, MOBIKE, query_date, lat, lon])
        
        else:
            continue
            # TODO: error handling

    return mobikes

if __name__== "__main__":
    # Connect to an existing database
    query_date= datetime.datetime.now()
    NEXTBIKE = 0
    LIDLBIKE = 1
    MOBIKE = 2

    nextbikes = get_nextbike_locations()
    lidlbikes = get_lidlbike_locations()
    mobikes = get_mobike_locations()

    # insert into database
    conn = psycopg2.connect("host=localhost dbname=bikes user=postgres password=kjLdfh$7383.,jdfkwölqQH")
    cur = conn.cursor()
    sql = """INSERT INTO public."bikeLocations"("id", "bikeId", "providerId", "timestamp", latitude, longitude) VALUES %s"""
    psycopg2.extras.execute_values(cur, sql, nextbikes, template='(DEFAULT, %s, %s, %s, %s, %s)')
    psycopg2.extras.execute_values(cur, sql, lidlbikes, template='(DEFAULT, %s, %s, %s, %s, %s)')
    psycopg2.extras.execute_values(cur, sql, mobikes, template='(DEFAULT, %s, %s, %s, %s, %s)')
            
    conn.commit()
    cur.close()
    conn.close()