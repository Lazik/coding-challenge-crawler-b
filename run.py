#!/usr/bin/env python
# -*- coding: utf-8

'''
                        .s$$$Ss.
            .8,         $$$. _. .              ..sS$$$$$"  ...,.;
 o.   ,@..  88        =.$"$'  '          ..sS$$$$$$$$$$$$s. _;"'
  @@@.@@@. .88.   `  ` ""l. .sS$$.._.sS$$$$$$$$$$$$S'"'
   .@@@q@@.8888o.         .s$$$$$$$$$$$$$$$$$$$$$'
     .:`@@@@33333.       .>$$$$$$$$$$$$$$$$$$$$'
     .: `@@@@333'       ..>$$$$$$$$$$$$$$$$$$$'
      :  `@@333.     `.,   s$$$$$$$$$$$$$$$$$'
      :   `@33       $$ S.s$$$$$$$$$$$$$$$$$'
      .S   `Y      ..`  ,"$' `$$$$$$$$$$$$$$
      $s  .       ..S$s,    . .`$$$$$$$$$$$$.
      $s .,      ,s ,$$$$,,sS$s.$$$$$$$$$$$$$.
      / /$$SsS.s. ..s$$$$$$$$$$$$$$$$$$$$$$$$$.
     /`.`$$$$$dN.ssS$$'`$$$$$$$$$$$$$$$$$$$$$$$.
    ///   `$$$$$$$$$'    `$$$$$$$$$$$$$$$$$$$$$$.
   ///|     `S$$S$'       `$$$$$$$$$$$$$$$$$$$$$$.
  / /                      $$$$$$$$$$$$$$$$$$$$$.
                           `$$$$$$$$$$$$$$$$$$$$$s.
                            $$$"'        .?T$$$$$$$
                           .$'        ...      ?$$#\
                           !       -=S$$$$$s
                         .!       -=s$$'  `$=-_      :
                        ,        .$$$'     `$,       .|
                       ,       .$$$'          .        ,
                      ,     ..$$$'
                          .s$$$'                 `s     .
                   .   .s$$$$'                    $s. ..$s
                  .  .s$$$$'                      `$s=s$$$
                    .$$$$'                         ,    $$s
               `   " .$$'                               $$$
               ,   s$$'                              .  $$$s
            ` .s..s$'                                .s ,$$
             .s$$$'                                   "s$$$,
          -   $$$'                                     .$$$$.
        ."  .s$$s                                     .$',',$.
        $s.s$$$$S..............   ................    $$....s$s......
         `""'           `     ```"""""""""""""""         `""   ``

Copyright Loïc Maltais-Herry
Copryright open to transfer (C S.13.5)
qc.loic@gmail.com
Code may not be distributed, modified or used for commercial purpose.

13/02/2014
'''

import argparse
import datetime
import mechanize
import urllib
import urllib2

import json
import ast
import re
import copy
from bs4 import BeautifulSoup, NavigableString
	
def parse_date(s):
    """Parse a date string

    Arguments:
    s -- Date as string in format: YYYY-MM-DD
    """
    return datetime.datetime.strptime(s, '%Y-%m-%d')
	
def today(offset=0):
	"""Get today's date, with an optional offset

	Keyword arguments:
	offset -- offset the number of days to offset from today (default 0)
	"""
	return datetime.date.today() + datetime.timedelta(days=offset)

def init_browser():
	"""
	Create a mechanize.Browser()
	Set cookies
	Enter the language page
	
	Returns the Browser() instance as br
	"""
	url = 'http://ca.megabus.com/BusStops.aspx'
	br = mechanize.Browser()
	br.set_handle_robots(False)
	br.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]
	br.open(url)
	response = br.response().read()

	br.select_form(nr=0)
	response = br.submit(name='btnEnglishCanada').read()  #"Press" the english button
	
	return br
	
def generate_destination_ajax_data(br):
	"""
	Takes a mechanize browser br
	This functions extracts all input name & values from the aspx form. The aspx form in the state as present in the br (mechanize.Browser())
	
	Returns a dictionary with field_name as key and field_value as value.
	See end of file for a list of all inputs for this aspx app. @generate_destination_ajax_data::input_data
	"""
	post_data = {}
	
	for control in br.form.controls:
		
		c_name = control.name
		c_value = br[control.name]
		
		if control.type == 'select':
			c_value = r''
			if len(br[control.name]) == 0:
				c_value = r''
			elif len(br[control.name]) == 1:
				c_value=br[control.name][0]
			else:
				raise Exception("[Post Data Extraction] While extracting form data for post data, one value was a list with more than 1 element.")

		if control.disabled == False:
			post_data[c_name] = c_value
			
	return post_data
	
def get_destination_subpage(response):
	"""
	Intercept ajax response and get the new html code
	
	Returns the new html code
	"""
	s_str1 = r'updatePanel|confirm1_UpdatePanel1|'
	idx_1 = response.find(s_str1)
	idx_2 = response.find('|0|hiddenField|__EVENTTARGET|')
	
	if idx_1 == -1 or idx_2 == -1:
		raise Exception('[get_stops::extract_first_destination] Fatal : could not find modifier code in ajax request.')
	
	page_subset = response[idx_1+len(s_str1):idx_2]
	
	return page_subset
	
def extract_all_destination(response, origin_name):
	"""
	Given full http ajax#1 response and origin name,
	Returns a list of dicts : 
		[ {'origin':origin_name1,'destination',destination_name1}, {}, ... ]
		
	Each dict is a pair of key 'origin':origin_name and 'destination':destination_name
	"""
	page_subset = get_destination_subpage(response)
	soup = BeautifulSoup(page_subset)
	
	destination_list = soup.find("select", id='confirm1_ddlTravellingTo')
	
	destinations = []
	
	for option in destination_list.find_all("option"):
		value = option['value']
		if (value == '-1'):
			continue
			
		route_pair = {}
		route_pair['origin'] = origin_name
		route_pair['destination'] = option.contents[0]
		
		destinations.append(route_pair)
		
	return destinations
	
def extract_route_list(response, origin):
	"""
	Given full http ajax#1 response and origin_id,
	Returns a list of destination_id
	* Note, the ids are in string format : "43"
	"""
	page_subset = get_destination_subpage(response)
	soup = BeautifulSoup(page_subset)
	
	destination_list = soup.find("select", id='confirm1_ddlTravellingTo')
	
	destination_l = []
	
	for option in destination_list.find_all("option"):
		value = option['value']
		if (value == '-1'):
			continue
			
		destination_l.append(value)
		
	return destination_l
	
def extract_first_destination(response):
	"""
	Given full http ajax#1 response (i.e. an origin_id is selected)
	Returns the first valid destination_id
	* Note, id is in string form: "44"
	"""
	
	page_subset = get_destination_subpage(response)
	soup = BeautifulSoup(page_subset)
	
	destination_list = soup.find("select", id='confirm1_ddlTravellingTo')
	
	for option in destination_list.find_all("option"):
		value = option['value']
		if (value != '-1'):
			return value
	
	return -1
	
def create_stop_dictionary(control):
	"""
	Given a mechanize control,
	Returns a dictionary of the form
	{stop_id:stop_name}
	* Note, id is in string form : "44"
	"""
	stop_dict = {}
	if control.type == "select": 
		for item in control.items:
			if item.name == "-1":
				continue
			else:
				clean_label = [label.text for label in item.get_labels()]
				clean_label = clean_label[0]
				stop_dict[item.name]=clean_label
	
	return stop_dict

def resolve_stop_routes(origin, origin_name, br, id_mode=0):
	"""
	Given an origin (id), an origin_name, a mechanize browser br and an optional id_mode
	Returns
	 for id_mode = 0  ($step2)
		List of named pairs : [ {'origin':origin_name,'destination',destination_name1}, {...,destination_name2}, ... ]
	 for id_mode = 1 ($step3)
		List of possible destination_id for origin param : ["4", "55"]
	"""
	url = 'http://ca.megabus.com/BusStops.aspx'

	br.open(url)
	response = br.response().read()
	
	# Select form
	br.select_form("ctl01")
	
	# Create post_data for ajax call
	post_data = generate_destination_ajax_data(br)

	# Store an initial copy to make the submit request
	original_data = {}
	original_data = copy.deepcopy(post_data)
	
	# Set origin
	post_data[r'confirm1$ddlLeavingFromMap'] = origin
			
	# Ajax action verb 
	post_data[r'UserStatus$ScriptManager1'] = r'confirm1$UpdatePanel1|confirm1$ddlLeavingFromMap'
	post_data[r'__ASYNCPOST'] = r'true'

	# Ajax function
	post_data['__EVENTTARGET'] = r'confirm1$ddlLeavingFromMap'

	# Encode post_data
	data = urllib.urlencode(post_data)
	
	# Ajax #1 Request
	br.open(url, data)
	
	# Ajax #1 response
	response = br.response().read()

	# Returns pairs of (origin,destination)
	# if id_mode == 1: returns pairs of ids
	# else : returns named pairs (i.e. station name)
	if id_mode == 0:
		route_pairs = extract_all_destination(response, origin_name)
	elif id_mode == 1:
		route_pairs = extract_route_list(response, origin)
	
	return route_pairs
	
def resolve_stop_info(origin, origin_name, br):
	"""
	Given an origin (id), an origin_name, and mechanize browser br
	Returns a dict describing the stop_info
	
	{
	"stop_name": "Hamilton McMaster University, ON",
	"stop_location":"McMaster University at Mary Keyes and Cootes Drive",
	"lat":43.258736,
	"long":-79.92245
	}
	"""
	url = 'http://ca.megabus.com/BusStops.aspx'

	# Select form
	br.select_form("ctl01")
	
	# Create post_data for ajax call
	post_data = generate_destination_ajax_data(br)

	# Store an initial copy to make the submit request
	original_data = {}
	original_data = copy.deepcopy(post_data)
	
	# Set origin
	post_data[r'confirm1$ddlLeavingFromMap'] = origin
			
	# Ajax action verb 
	post_data[r'UserStatus$ScriptManager1'] = r'confirm1$UpdatePanel1|confirm1$ddlLeavingFromMap'
	post_data[r'__ASYNCPOST'] = r'true'

	# Ajax function
	post_data['__EVENTTARGET'] = r'confirm1$ddlLeavingFromMap'

	# Encode post_data
	data = urllib.urlencode(post_data)
	
	# Ajax #1 Request
	br.open(url, data)
	
	# Ajax #1 response
	response = br.response().read()

	# Output first valid destination
	destination_id = extract_first_destination(response)
	
	if destination_id == -1:
		print "[get_stops::resolve_stop_info] Warning: No destination found for origin :" + origin + ". Could be a bug or 'weird website'"
		print "skipping to next origin"
		return
	
	# Ajax #2 preparation
	# Extract view_state & event_validation
	view_state, event_validation = extract_aspx_state_variables(response)
	
	# UserStatus$ScriptManager1:confirm1$UpdatePanel1|confirm1$ddlTravellingTo
	post_data[r'UserStatus$ScriptManager1'] = r'confirm1$UpdatePanel1|confirm1$ddlTravellingTo'
	post_data[r'confirm1$ddlTravellingTo'] = destination_id

	post_data[r'__EVENTTARGET'] = r'confirm1$ddlTravellingTo'
	
	post_data[r'__VIEWSTATE'] = view_state
	post_data[r'__EVENTVALIDATION'] = event_validation
	
	# Encode post_data
	data = urllib.urlencode(post_data)
	
	# Ajax #2 Request
	br.open(url, data)
	
	# Ajax #2 response
	response = br.response().read()
	
	# Post Submit Preparation
	# extract new state_view and event_validation
	view_state, event_validation = extract_aspx_state_variables(response)
	
	# Manipulate post data to submit form
	original_data[r'confirm1$ddlLeavingFromMap'] = origin
	original_data[r'confirm1$ddlTravellingTo'] = destination_id
	original_data[r'confirm1$btnSearch'] = r'Search'
	
	original_data[r'__VIEWSTATE'] = view_state
	original_data[r'__EVENTVALIDATION'] = event_validation
	
	# Encode data
	submit_data = urllib.urlencode(original_data)
	
	# Post Submit Request
	br.open(url, submit_data)
	
	# Geolocation response
	response = br.response().read()
	
	position, location = extract_geolocation(response, origin_name) #origin_name
	
	lat = position[0]
	long = position[1]
	
	stop_info = {}
	
	stop_info["stop_name"] = origin_name
	stop_info["stop_location"] = location
	stop_info["lat"] = str(lat)
	stop_info["long"] = str(long)
	
	'''
	{
		"stop_name": "Hamilton McMaster University, ON",
		"stop_location":"McMaster University at Mary Keyes and Cootes Drive",
		"lat":43.258736,
		"long":-79.92245
	}
	'''
	
	return stop_info
	
def extract_aspx_state_variables(response):
	"""
	Given an ajax response, extract the new states of the aspx app
	Returns (viewstate, event_validation)
	"""
	# Get view_state
	s_str1 = r'|__VIEWSTATE|'
	view_idx_1 = response.find(s_str1)
	
	sub_response = response[view_idx_1+len(s_str1):]
	view_idx_2 = sub_response.find(r'|')
	viewstate = sub_response[0:view_idx_2]
	
	# Get event_validation
	s_str1 = r'|__EVENTVALIDATION|'
	event_idx_1 = sub_response.find(s_str1)
	
	sub_response = sub_response[event_idx_1+len(s_str1):]
	event_idx_2 = sub_response.find(r'|')
	event_validation = sub_response[0:event_idx_2]
	
	return (viewstate, event_validation)

def extract_geolocation(response, origin_name):
	"""
	Given the form request response, an origin_name
	Extracts its position(lat, long) and its location.
	Location example : 'T1-Post P6 (Grd Level), T3-Post C8. Pearson Airport'
	
	Returns (position, location)
	"""
	
	#EmperorBing.addMarker(map, new Microsoft.Maps.Pushpin(new Microsoft.Maps.Location(43.258736,-79.92245), { undefined: undefined, icon:'/images/mapmarker.gif', width:42, height:42, anchor: new Microsoft.Maps.Point(21,21)}),new simpleInfo('McMaster University',' The McMaster University stop is located at McMaster University at Mary Keyes and Cootes Drive.'));
	
	#EmperorBing.addMarker(map, new Microsoft.Maps.Pushpin(new Microsoft.Maps.Location(43.682583,-79.61363), { undefined: undefined, icon:'/images/mapmarker.gif', width:42, height:42, anchor: new Microsoft.Maps.Point(21,21)}),new simpleInfo('T1-Post P6 (Grd Level), T3-Post C8','Pearson Airport'));
	
	str1 = r'EmperorBing.addMarker(map, new Microsoft.Maps.Pushpin(new Microsoft.Maps.Location'
	idx_1 = response.find(str1)
	
	# Cut the javascript line we want
	sub_response = response[idx_1+len(str1):]
	lower_bound = sub_response.find(r';')
	sub_response = sub_response[0:lower_bound]
	
	js_text = sub_response # used in commented code.
	
	# Extract Position
	idx_position = sub_response.find(r')')
	str_position = sub_response[0:idx_position+1]
	#print str_position
	position = ast.literal_eval(str_position)
	
	# Extract Location
	
	# cut new simpleInfo
	si_str1 = r'new simpleInfo'
	si_idx1 = sub_response.find(si_str1)
	
	sub_response = sub_response[si_idx1+len(si_str1):-1]
	#print sub_response
	
	# Deal with malformed app output
	try:
		simple_info = ast.literal_eval(sub_response)
	except SyntaxError:
		#SyntaxError: EOL while scanning string literal
		#Fix their malformed output
		sub_response += "')"
		simple_info = ast.literal_eval(sub_response)
	except:
		raise
	
	# Can do more processing for a more uniform output.
	if origin_name != simple_info[0]:
		left = simple_info[0].strip().replace('\n','')
		right = simple_info[1].strip().replace('\n','')
		
		if left[-1] == '.':
			location = left + ' ' + right
		else:
			location = left+'. '+right
	else:
		clean_info = simple_info[1].strip().replace('\n','')
		location = clean_info
		# Can cut the 'located at' here
		# Because some left part have a . at the end, it won't match origin_name... more logic
		
	return (position, location)
	
def get_route_specifics(br, origin, destination, origin_name, destination_name, start_date, end_date):
	"""
	Given a mechanize browser br, an origin (id), destination (id), origin_name, destination_name, a start_date datetime.date obj and an end_date obj
	
	Returns a list of dicts describing each route with price & times for the date range [start_date, end_date]
	[{"origin": "Beamsville, ON","destination": "Hamilton GO Centre, ON","departure_time": "2013-06-05T07:20:00","arrival_time": "2013-06-05T08:15:00","duration": "0:55","price": 5.00}, {},...]
	
	"""
	# Stores our return info
	multi_day_route_specifics = []
	
	# Attribution of dates
	current_date = start_date
	end_date_obj = end_date
	
	# Cover the date range
	while ( current_date <= end_date_obj ):
		
		# Create date in busbud format
		formatted_date = current_date.strftime('%Y-%m-%d')
		
		# Create date in megabus format
		start_date = current_date.strftime('%d/%m/%Y')
		
		# Encoding date
		# 13%2f02%2f2014
		start_date = urllib.quote(start_date,'')
		
		# Build URL
		url = "http://ca.megabus.com/JourneyResults.aspx?originCode=" + origin + "&destinationCode=" + destination + "&outboundDepartureDate=" + start_date + "&inboundDepartureDate=&passengerCount=1&transportType=0&concessionCount=0&nusCount=0&outboundWheelchairSeated=0&outboundOtherDisabilityCount=0&inboundWheelchairSeated=0&inboundOtherDisabilityCount=0&outboundPcaCount=0&inboundPcaCount=0&promotionCode=&withReturn=0"
		#print url
		
		# Send Request
		br.open(url)
		
		# Get response
		response = br.response().read()
		
		# Build soup
		soup = BeautifulSoup(response)
		
		# Find Result-block anchor
		div_anchor = soup.find('div', id="JourneyResylts_OutboundList_main_div")
		
		# Null check (no departs)
		if div_anchor is None:
			current_date += datetime.timedelta(days=1)
			continue

		# Holds route info for 1 day
		route_specifics = []

		# Find every result-section
		ul_sections = div_anchor.find_all('ul', class_ = "journey standard")

		# Null check (no departs)
		if ul_sections is None:
			current_date += datetime.timedelta(days=1)
			continue
			
		# For each result-section, extract all the info (price, times, duration)
		for section in ul_sections:
			# Info dict
			route_info = {}
			
			route_info['origin'] = origin_name
			route_info['destination'] =  destination_name
			
			# Extract depart_time
			to_from_section = section.find('li', class_="two")
			
			departs = to_from_section.p
			depart_time = departs.contents[2].strip()

			# Extract arrival_time
			arrival = departs.find_next_sibling('p')
			arrival_time = arrival.contents[2].strip()
			
			# Extract duration
			duration_section = section.find('li', class_="three")
			duration = duration_section.p.contents[0].strip()

			# Extract price
			price_section = section.find('li', class_="five")
			price = price_section.p.contents[0].strip()

			# Create dict in busbud format | 2013-06-05T08:15:00
			route_info["departure_time"] = formatted_date + "T" + depart_time + ":00"
			route_info["arrival_time"] = formatted_date + "T" + arrival_time + ":00"
			
			# duration format : "2hrs 59mins" -> "2:59"
			route_info["duration"] = duration.replace('hrs ',':').replace('mins','')
			
			# "$44.00" -> 44.0
			route_info["price"] = float( price.replace('$','').strip() )
			
			route_specifics.append(route_info)
		
		multi_day_route_specifics += route_specifics
		
		# Increment for next_day
		current_date += datetime.timedelta(days=1)
	
	return multi_day_route_specifics
	
	#<div id="JourneyResylts_OutboundList_main_div" class="JourneyList">
	#	<ul class="heading">
	#	<ul id="JourneyResylts_OutboundList_GridViewResults_ctl00_row_item" class="journey standard">
	#		<li class="two">  depart/arrive
	#			<p> Departs
	#			<p class='arrive'> Arrive
	#		<li class="three">
	#			<p> duration </p>
	#		<li class="four">
	#			<img id="JourneyResylts_OutboundList_GridViewResults_ctl01_imgCarrier" title="Megabus Canada" src="images/carriers/megabus_sm.gif" alt="Megabus Canada" style="border-width:0px;">
	#		<li class="five">
	#			<p> price </p>
	#	<ul id="JourneyResylts_OutboundList_GridViewResults_ctl01_row_item" class="journey standard">
	
	
def get_stops(args):
	"""
	Function handles step1
	"""
	url = 'http://ca.megabus.com/BusStops.aspx'
	
	# Initialize aspx state variables
	br = init_browser()

	# Get all stop names
	br.select_form("ctl01")
	
	# Select origin list
	control = br.form.find_control("confirm1$ddlLeavingFromMap")

	# Create Stop Dictionary (id -> stop_name)
	stop_dict = create_stop_dictionary(control)

	bus_stops = []
	for stop_id in stop_dict:
		stop_name = stop_dict[stop_id]
		stop_info = resolve_stop_info(stop_id, stop_name, br)
		bus_stops.append(stop_info)
	
	# Write stop_list to disk
	args.output.write(json.dumps(bus_stops, indent=4))
	args.output.close()
	
def get_routes(args):
	"""
	Function handles step2
	"""
	
	# Initialize aspx state variables
	br = init_browser()

	# Get all stop names
	br.select_form("ctl01")
	
	# Select origin list
	control = br.form.find_control("confirm1$ddlLeavingFromMap")

	# Create Stop Dictionary (id -> stop_name)
	stop_dict = create_stop_dictionary(control)
	
	bus_routes = []
	
	for stop_id in stop_dict:

		stop_name = stop_dict[stop_id]
		stop_info = resolve_stop_routes(stop_id, stop_name, br)
		
		bus_routes+=stop_info
		
	# Write stop_list to disk
	args.output.write(json.dumps(bus_routes, indent=4))
	args.output.close()
	
def get_departures(args):
	"""
	Function handles step3
	"""
	
	if args.startdate > args.enddate:
		print "[get_departures] Fatal: Date supplied in the wrong order. enddate must be greater or equal to startdate."
		return

	br = init_browser()

	# Should save/load pickle version of both list (faster)
	
	# # Fetch stops
	# Get all stop names
	br.select_form("ctl01")
	
	# Select origin list
	control = br.form.find_control("confirm1$ddlLeavingFromMap")

	# Create Stop Dictionary (id -> stop_name)
	stop_dict = create_stop_dictionary(control)
	# ##
	
	# Fetch routes
	route_dict = {}
	
	for stop_id in stop_dict:
		stop_name = stop_dict[stop_id]

		# stop_info = ["3","4"]
		stop_info = resolve_stop_routes(stop_id, stop_name, br, 1)
		
		route_dict[stop_id] = stop_info
	# ##

	# Go
	departures = []
	for stop_id in stop_dict:
		for route_id in route_dict[stop_id]:
			origin_name = stop_dict[stop_id]
			destination_name = stop_dict[route_id]
			route_specifics = get_route_specifics(br, stop_id, route_id, origin_name, destination_name, args.startdate, args.enddate)
			
			departures+=route_specifics
			
	# Write departures to disk
	args.output.write(json.dumps(departures, indent=4))
	args.output.close()

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Crawl web site.')
	parser.add_argument('--extract', required=True, choices=['stops', 'routes', 'departures'],
						help='the type of extraction to perform')
	parser.add_argument('--output', required=True, type=argparse.FileType('w'),
						help='the path of the output file to generate')
	parser.add_argument('--startdate', required=False, type=parse_date, default=today(),
						help='the beginning of the departure date range')
	parser.add_argument('--enddate', required=False, type=parse_date, default=today(7),
						help='the end of the departure date range')

	args = parser.parse_args()

	if args.extract == 'stops':
		print 'Downloading stops to {}'.format(args.output)
		get_stops(args)

	elif args.extract == 'routes':
		print 'Downloading routes to {}'.format(args.output)
		get_routes(args)

	elif args.extract == 'departures':
		print 'Downloading departures to {0} for dates {1} through {2}'.format(
			args.output, args.startdate, args.enddate)
		get_departures(args)

'''
@generate_destination_ajax_data::input_data

UserStatus_ScriptManager1_HiddenField:
ctl16$ddlLanguage:en
JourneyPlanner$txtNumberOfPassengers:1
JourneyPlanner$hdnSelected:-1,
JourneyPlanner$ddlLeavingFrom:-1
JourneyPlanner$txtPromotionalCode:
confirm1$ddlLeavingFromMap:429
confirm1$ddlTravellingTo:449
confirm1$btnSearch:Search
__EVENTTARGET:
__EVENTARGUMENT:
__LASTFOCUS:
__VIEWSTATE:/wEPD...uWW3av
__EVENTVALIDATION:/wEWW...UgsAS3qJ9M4=
'''
