# Identifying At-Threat Locations & Severity from Police Radio

Project by Anna Haas, James Lovejoy, Matt Clifford and William Holder

### The Problem

During any type of disaster, chaos is present. To help organize this chaos and address the disaster FEMA (Federal Emergency Management Agency) steps in. The mission of FEMA is to "support the citizens and first responders to promote that as a nation we work together to build sustain, and improve our capability to prepare for, protect against, respond to, recover from, and mitigate all hazards." During a time of disaster, specifically during the Camp Fire, the most deadly wildfire in California history, can audio from police radios be used to identify affected locations and understand severity to more effectively allocate emergency resources? To address this problem we will extract vital information from audio files to map at-risk locations and show severity by the frequency of locations mentioned. This audio will come from five different police radios, providing unique, aggregated information.

### Data Collection

While police radio has potential to be a vital information resource for a variety of disasters, we chose to narrow our scope by focusing on the Camp Fire wildfire in Butte, County California that took place on November 8, 2018. Using Broadcastify's police radio archives we downloaded audio files from 6:44 AM - 9:12 AM from five different police radio scanners (Butte Sheriff Fire/Paradise Police, Chico Paradise Fire/CalFire, Chico Police Dispatch, Oroville Fire, and Oroville Police/Fire) over a time period of 6:44 AM to 9:12 AM. With the audio files collected, we passed them into Amazon Transcribe. We chose Amazon Transcribe as we were able to get it up and running fairly quickly, there is an easy to use web interface and it provided us with essential information such as translation confidence per word and speaker labeling. Additionally, Amazon Transcribe has parameters such as vocabulary that have been set to obtain the most pertinent information from the feeds. To best transcribe the audio files we added a custom vocabulary of proper nouns (city names) and a few key fire event related terms. The location-predominant vocabulary gave us significantly better results than the translation without it. It is important to note that we were limited by the quality of the audio (typically not clear with lots of background noise) and hence the quality of the translation. We attempted to clean the audio through noise reduction, normalizing sound, and low-pass/high-pass filter for human voice frequency; however, despite being easier to listen to the transcription did not improve so we decided to move forward with the raw audio form.

### Data Cleaning

The transcription of audio files to text resulted in 20 JSON files (4 for each of the 5 feeds). The JSON files were nested dictionaries containing detailed information on the transcribed words and the identification of various speakers. To transform these files into useful data we extracted two dataframes from each file - one for the individual words and one for the speakers. Both dataframes have a start and stop times associated with them and each individual word has a translation confidence score (0 to 1). The speaker was then appended to each word based on the start and stop time. The next step was to combine words to create individual observations. We defined an observation by the change of speaker. For each observation (a string of multiple words) we now have the associated speaker number, feed, start and stop time, and confidence of each individual word.
This data can be used to find additional data such as average confidence of a string and start and stop time as datetime objects using the feed start time (in the audio file name) and the observation start time (relative to each JSON file). Additionally, we added a column for a list of locations mentioned in each observation and an indicator for import words such as 'fire' and 'evacuation' related words. This dataframe was sorted and re-indexed by start time (regardless of feed) to better understand how events unfolded chronologically. This completed dataframe ('sentences') contains 463 observations and 18 columns.

As a next step toward mapping this data, we created a location-based observation where each location from the list of locations became an individual observation. Along with the location we included the text associated with that location and then appended geographical and shapefile data from the state of California associated with each town. This completed dataframe ('threats') contains 217 observations and 8 columns.

### Exploratory Data Analysis

While there are limitations due to the translation as a result of poor audio quality, the average translation confidence per observation is 0.75. There are 13 observations that have less than 0.1 as their minimum confidence and this is a result of fairly common words with low confidence such as 'been', 'someone', 'the', 'your', 'in', 'sure'. The average speaker length is between 1.09 and 1.60 seconds for all feeds, signaling that there is a lot of back and forth conversation. While most observations fall under 3 seconds, each feed has some observations that last longer than 7 seconds. Of our 464 observations, a location is mentioned in 138 of them (29.74%). For those that do mention a location, the average number of locations mentioned is 1.54. As time goes on over the two hour period more city names are mentioned, with the most consistently mentioned city being Oroville.

Most observations are quite short (as we discussed with speaker length), falling easily under 50 words and 250 characters. Most commonly appearing words are 'Twenty', 'Wait', 'Way', 'Forty', 'Seven', 'Oroville', 'Evacuate' (and other forms), and 'Thirty'. The most common words in observations mentioning fire are: 'area', 'report', 'concow', 'wait', and 'travel'; while the most common words found in the observations that do not contain fire are: 'clear', 'sixteen', and 'local'.

Using a predefined set of threat words gathered during our custom vocabulary research ('fire', 'engine', 'evacuation', 'evacuating', 'evacuation', 'mandatory', 'medic', 'emergency', 'danger', 'smoke'), a column was created indicating how many times one of those words had been observed in a 2 minute period. The mean was 2.71 with the max being 12. This could be a possible indicator of severity level. The word rate (words spoken per second) has a strong positive correlation (0.75) with the presence of threat terms. While this is expected as the more words being spoken in a time frame increases the likelihood to see threat words, we can also investigate if more words being spoken per second are any indication of an event occurring (versus routine radio conversation).

### Mapping

To show how the event unfolded over time and frequency with which cities were being mentioned we used Tableau. Tableau facilitated rapid prototyping of visualizations and dashboard elements. To keep the interface simple, we encoded only three variables:
  1. Location - any mention of a location within Butte County.
  2. Time - the time at which a speaker started a statement. To condense the animation, each frame (or “page” in Tableau) represents the actual time of a statement. For a more accurate depiction of mentions over time, to mimic a live context, up-sampling to interpolate one frame/page-per-second might be desirable.
  3. Location count - a running total of mentioned for each location. This feature is double-encoded by mark size and stepped color to increase visual popout and to aid comparison across tracked locations.

A consideration with this visualization is its ability to be used in a live context, where the number of mentions will be indefinite. In a live case, it might be useful to depict the frequency of mentions over a given cycle in addition to a running total. Our example map does gesture at this functionality by incorporating a slight fade as time passes after each mention. Additionally, a possible new dimension is an encoding of the source feed. Knowing which channels are discussing which locations/topics, and distinguishing whether a location is providing or in need of assistance, may be essential to a useful representation of a developing event. While this is omitted from our example for simplicity, a near-future feature may provide a better example of how this could be represented in an intuitive way  (https://www.tableau.com/products/coming-soon#feature-103005)

### Future Considerations

Natural language-based systems present many special challenges. In our problem space, these challenges are compounded by factors like limited audio quality, highly-specific and regionally variant discourse communities, audience transfer, live processing, and the predictable unpredictability surrounding any crisis event. Our exploration of this problem indicates that a major step to any federal-scale machine learning-based solution would require a significant up-front investment in preparation of high-quality training data. We suggest modeling this phase of the project on examples like YOUTUBE8M https://research.google.com/youtube8m/download.html.

One consideration for a rapid-response support tool of this nature is when to activate. Would this system be most effectively implemented as a constant listener on all/select channels, in order to indicate a potentially developing event even before local authorities are aware? If so, already-complex security and privacy considerations may be elevated. On the other hand, would the system need to be activated once an emergency is declared? In this case, thresholds for activation would be a primary consideration.

In a live setting, this system would ingest audio from many streams and send alerts when potential events are detected. An additional level of human approval would be added to decide if the event requires attention. The system would predict the type of event, the location, and severity, as well as provide a short audio snippet that caused the alert. Another consideration with this system is an indication of when the dispatcher is speaking to better grasp the conversation flow. In order to update custom vocabulary in a live situation, it would be interesting to look at how live twitter data could be used to curate location and event specific vocabularies. Lastly, the combination of radio and 911 calls would also lead to a larger, more robust picture of how events are unfolding.

### Data Dictionary

|Feature|Type|Description|
|---|---|---|
|text|string|sentence spoken (audio translation)|
|speaker_start|float|time the speaker began (seconds), relative to individual JSON files|
|speaker_end|float|time the speaker began (seconds), relative to individual JSON files|
|speaker_length|float|speaker_end - speaker_length|
|speaker|string|speaker number 0-9 relative to JSON file (used to construct sentences)|
|sentence|string|sentence number (used to construct sentences)|
|word_confidence|float|translation confidence score provided by Amazon Transcribe|
|feed|int|feed number from audio file name|
|location|list|cities (predefined) mentioned in the observation|
|state|string|'CA'|
|feed_name|string|name of feed from Broadcastify archives|
|department|string|police, fire, or both|
|text_clean|string|lowercase, no punctuation version of original text|
|start_time|datetime|actual start time of observation on November 8, 2018|
|end_time|datetime|actual end time of observation on November 8, 2018|

### SOURCES

CA Geographic Data:
https://data.ca.gov/dataset/ca-geographic-boundaries

Images:
https://www.washingtonpost.com/resizer/I2T-yNy6jndvNUG-dMTUeJ658pc=/1484x0/arc-anglerfish-washpost-prod-washpost.s3.amazonaws.com/public/VVZRSOHO4EI6RC2HXUEXL7LBTE.jpg

Background Information:
https://www.sfchronicle.com/california-wildfires/article/What-we-know-about-the-deadly-Camp-Fire-13401383.php
https://disasterphilanthropy.org/issue-insight/fema/
