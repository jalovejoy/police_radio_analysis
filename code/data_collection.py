import pandas as pd
import numpy as np
from pandas.io.json import json_normalize
import json
from datetime import datetime, timedelta
import pytz


# Get 2 dataframes (one for words, one for speakers) from JSON
def transcription_outputs(file_name):

    # Read in the JSON file
    with open('./' + file_name,'r') as read_file:
         data = json.load(read_file)

    # Get Dataframe 1: Words
    words = data['results']['items']
    words = json_normalize(words,
              record_path='alternatives',
              meta=['end_time','start_time','type'],
              errors='ignore')
    words = words[['content','confidence','start_time','end_time','type']]
    words['feed'] = data['jobName']

    # Get Dataframe 2: Speaker
    speaker_labels = data['results']['speaker_labels']
    speaker_turns = json_normalize(speaker_labels,
                      record_path='segments',
                      meta='speakers',
                      errors='ignore')
    speaker_turns = speaker_turns[['start_time', 'end_time', 'items', 'speaker_label', 'speakers']]

    return words, speaker_turns


# Append speaker to words dataframe based on time
def append_speaker(items_df, speakers_df):

    # Set default values
    items_df['speaker_start'] = np.nan
    items_df['speaker_end'] = np.nan
    items_df['sentence'] = np.nan
    items_df['speaker'] = np.nan

    # Reset index
    items_df.reset_index(inplace=True, drop=True)

    # Format start time in both columns as type float
    items_df['start_time'] = items_df['start_time'].astype('float') ### MAY NOT NEED IF ALREADY SET
    speakers_df['start_time'] = speakers_df['start_time'].astype('float') ### MAY NOT NEED IF ALREADY SET

    # Iterate through rows in speaker df to append to items_df (dataframe of words)
    sentence = 0
    for i, sp_row in enumerate(speakers_df.iterrows()):
        start_time = sp_row[1][0] ### Make sure index locs are the same
        end_time = sp_row[1][1] ### Make sure index locs are the same
        speaker = sp_row[1][3] ### Make sure index locs are the same
        for i, it_row in enumerate(items_df[items_df['start_time'] >= start_time].iterrows()):
            if it_row[1][3] >= end_time: ### Make sure index locs are the same
                items_df.loc[it_row[0],'speaker'] = speaker
                items_df.loc[it_row[0],'speaker_start'] = start_time
                items_df.loc[it_row[0],'speaker_end'] = end_time
                items_df.loc[it_row[0],'sentence'] = sentence
                sentence += 1
                break
            else:
                items_df.loc[it_row[0],'speaker'] = speaker
                items_df.loc[it_row[0],'speaker_start'] = start_time
                items_df.loc[it_row[0],'speaker_end'] = end_time
                items_df.loc[it_row[0],'sentence'] = sentence

    # Fill in in values for the punctuation rows with the values from the previous text observation
    items_df['end_time'] = items_df['end_time'].map(lambda x: np.nan if x is 'nan' else float(x))
    items_df['speaker_end'] = items_df['speaker_end'].astype(float)
    for column in ['start_time', 'end_time', 'speaker_start', 'speaker_end', 'sentence', 'speaker']:
        items_df[column].fillna(method = 'ffill', inplace = True)

    # Fix confidence - replace None with np.nan and change values to float (from string)
    items_df['confidence'] = items_df['confidence'].map(lambda x: np.nan if x is None else float(x))

    return items_df


# Returns list of locations from our pre-defined list present in a single observation
def get_location(text):

    # Pre-defined location list
    location_list = ['CHICO', 'PARADISE', 'OROVILLE', 'MAGALIA', 'THERMALITO', 'GRIDLEY', 'DURHAM', 'PALERMO', 'RIDGE', 'BIGGS',
                        'COHASSET', 'BERRY-CREEK', 'FOREST-RANCH', 'BUTTE-CREEK-CANYON', 'BUTTE-VALLEY', 'COHASSET', 'CONCOW', 'BANGOR',
                        'HONCUT', 'YANKEE-HILL', 'FORBESTOWN', 'NORD', 'PUGLIA', 'STIRLING-CITY', 'RICHVALE', 'RACKERBY', 'BERRY-CREEK-RANCHERIA',
                        'CLIPPER-MILLS', 'ROBINSON-MILL', 'CHEROKEE', 'BUTTE-MEADOWS', 'ENTERPRISE-RANCHERIA']

    # Get list of locatoins mentioned
    locations_mentioned = []
    for location in location_list:
        if location.lower() in text.lower():
            locations_mentioned.append(location.replace('-',' '))

    return locations_mentioned

# Maps a list of the potential location matches from the CA_places dataframe and appends lat & long data
def label_centroids(df, ca_places):
    df['INTPTLON'] = 'None'
    df['INTPTLAT'] = 'None'
    df['ID_PLACES'] = 'None'
    for i, row in enumerate(df.iterrows()):
        intptlon = []
        intptlat = []
        id_places = []
        for loc in row[1]['location']:
            if loc in ca_places['NAME'].tolist():
                intptlon.extend(ca_places[ca_places['NAME'] == loc]['INTPTLON'])
                intptlat.extend(ca_places[ca_places['NAME'] == loc]['INTPTLAT'])
                id_places.extend(ca_places[ca_places['NAME'] == loc]['NAME'])
        df.at[i,'INTPTLON'] = intptlon
        df.at[i,'INTPTLAT'] = intptlat
        df.at[i,'ID_PLACES'] = id_places
    return df

# Maps file name to actual feed names (5 different feeds used)
def remap_feed(filename_str):

    # Dictionary to map feed numbers to feed bames
    feeds = {
        '1929'  : "Butte_Sheriff_Fire__Paradise_Police",
        '22956' : "Chico_Paradise_Fire__CalFire",
        '25641' : "Chico_Police_Dispatch",
        '24574' : "Oroville_Fire",
        '26936' : "Oroville_Police_Fire"
    }
    f = filename_str
    code = f[f.rfind('-')+1:-1]

    return feeds[code]


# Indicate which department the feed is associated with (Fire or Police)
def police_fire(feed_name):

    # Feed name to uppercase
    fnu = feed_name.upper()

    # Look for 'Fire' and 'Police' in feed name
    if 'FIRE' in fnu and 'POLICE' in fnu:
        return 'BOTH'
    elif 'FIRE' in fnu:
        return 'FIRE'
    elif 'POLICE' in fnu:
        return 'POLICE'
    else:
        return 'FEED_NAME_ERROR'


# Changes start time to the actual time (datetime object) based on thes start time of the entire feed
def actual_time_str(timecode_str, filename_str):

    filename_str = filename_str.split('/')[-1]

    # Get year, month, day, hour and minutes from file name
    YYYY = filename_str[:4]
    MM = filename_str[4:6]
    DD = filename_str[6:8]
    hh = filename_str[8:10]
    mm = filename_str[10:12]
    ssssmmmm  = float(timecode_str) # added via timedelta

    # adjust hours (file name is 2 hours behind actual time)
    hh_adj = str(int(hh)-2).zfill(2)

    # Create date time object
    dt_str = ''.join([YYYY,MM,DD,hh_adj,mm])
    dt_naive = datetime.strptime(dt_str, '%Y%m%d%H%M')
    tz_pac = pytz.timezone('US/Pacific')
    dt_pac_0 = tz_pac.localize(dt_naive)
    dt_pac_actual = dt_pac_0 + timedelta(seconds = int(ssssmmmm))

    return dt_pac_actual


# Take individual words and reconstruct into a sentence based on the time and speaker
def sentence_reconstruction(items_spkr_appnd, ca_places):

    # Create empty dataframe with desired columns
    df = pd.DataFrame(data='', index=[0], columns=['text','speaker_start','speaker_end','speaker_length','speaker',
                                                   'sentence', 'word_confidence','avg_confidence','min_conf','feed'])

    # Iterate through items dataframe to construct sentences
    index_set = 0
    confidence = []
    text = ''
    previous_speaker = items_spkr_appnd['speaker'][0]
    for i, speaker in enumerate(items_spkr_appnd['speaker']):
        if speaker != previous_speaker:
            df.loc[index_set,:] = {
                'speaker_start' : items_spkr_appnd.loc[i,'speaker_start'],
                'speaker_end' : items_spkr_appnd.loc[i,'speaker_end'],
                'speaker' : items_spkr_appnd.loc[i,'speaker'],
                'sentence' : items_spkr_appnd.loc[i,'sentence'],
                'text' : text,
                'word_confidence' : confidence,
                'min_conf' : min(confidence),
                'feed' : items_spkr_appnd.loc[i,'feed']
            }
            index_set += 1
            text = ''
            confidence = []
        text += str(items_spkr_appnd.loc[i, 'content'] + ' ')
        confidence.append(items_spkr_appnd.loc[i,'confidence'])
        previous_speaker = speaker

    # Calculate average confidence by removing NAs
    df['avg_confidence'] = df['word_confidence'].map(lambda list: np.mean([x for x in list if str(x) != 'nan']))

    # Add speaker_length
    df['speaker_length'] = df['speaker_end'] - df['speaker_start']

    # Add new columns: location, state, feed_name and is_fire_dept
    df['location'] = df['text'].map(get_location)
    df['state'] = 'CA'
    df['feed_name'] = df['feed'].map(remap_feed)
    df['department'] = df['feed_name'].map(police_fire)
    df = label_centroids(df, ca_places)

    return df


# Utilize previous functions to get master dataframe in the desired format
def get_dataframe(file_name, ca_places):

    # File name
    file_name = file_name

    # Step 1: get items and speaker df from json
    items_df, speakers_df = transcription_outputs(file_name)

    # Step 2: combine dataframes (single word observations with speaker)
    df = append_speaker(items_df, speakers_df)

    # Step 3: observations by sentence and additional desired columns
    df = sentence_reconstruction(df, ca_places)

    return df


# Create dataframe based on location to be used for location mapping
def create_threat_df(df):
    threat_df = pd.DataFrame(columns=['latitude','longitude'])
    index = 0
    for i, row in enumerate(df.iterrows()):
        if len(row[1]['INTPTLAT']) > 0:
            for j, loc in enumerate(row[1]['INTPTLAT']):
                threat_df.loc[index,'latitude'] = row[1]['INTPTLAT'][j]
                threat_df.loc[index,'longitude'] = row[1]['INTPTLON'][j]
                threat_df.loc[index,'id_places'] = row[1]['ID_PLACES'][j]
                threat_df.loc[index,'text'] = row[1]['text_clean']
                threat_df.loc[index,'confidence'] = row[1]['avg_confidence']
                threat_df.loc[index,'feed'] = row[1]['feed_name']
                threat_df.loc[index,'start_time'] = row[1]['start_time']
                threat_df.loc[index,'end_time'] = row[1]['end_time']
                threat_df.loc[index,'department'] = row[1]['department']
                index += 1
    return threat_df
