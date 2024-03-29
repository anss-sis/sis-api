'''
api_demo.py  2023-06-15
version 1.2 
    Changelog: Removed code to refresh a token, since that endpoint has been removed

This module contains functions to demo the following
    1. Send a request to the SIS webservice endpoint and write out the data in csv file 

Dependencies: 
  requests library. To install it run command: 
    $ pip3 install requests

  Token files: 
    1. sis_test.token: Your SIS token for the test website. Needed if running the script to connect to the test site
    2. sis_prod.token: Your SIS token for the production website. Needed if running the script to connect to the production site
  Get a token by using the SIS UI > Your Account page > Get a Token and copy it to the file.
  Limit read/write access to token file to only the user running the script and place it in the same directory as the script.

Example usage:
  1a. To get logger models
      $ python3 api_demo.py test getloggermodel logger_models.csv 
  1b. To get equipment for 2 models AIRLINK GX440, CP-WAN-B311-A operated by SCSN-CA. 
        Note that if modelname contains spaces it should be enclosed in quotes
      $ python3 api_demo.py test getequipment equipment.csv --modelnames "AIRLINK GX440" CP-WAN-B311-A --operatorcodes SCSN-CA
  1c. To get equipment belonging to a certain equipment category at given sites
      $ python3 api_demo.py prod getequipinstall loggerbeta.csv --categorys "LOGGER" --netcodes "AK" --lookupcodes "S32K" "M19K" "H23K"

Author: Prabha Acharya, ANSS SIS Development Team, SCSN

'''

import requests
import argparse
import os
import csv
from collections import defaultdict

config = { 
    'prod': {'baseurl': 'https://anss-sis.scsn.org/sis/api',
            'tokenfile': 'sis_prod.token', }, 
    'test': {'baseurl': 'https://anss-sis.scsn.org/sistest/api',
            'tokenfile': 'sis_test.token', }, 
    }


def read_token_file(mode):
    tokenfile = config[mode]['tokenfile']
    scriptpath = os.path.dirname(os.path.abspath(__file__))
    fpathname = os.path.join(scriptpath, tokenfile)
    with open (fpathname) as f:
        content = f.read()
        token = content.strip()
        return token

#  ----------- REPORT GENERATION --------------

def get_logger_models(mode, outfpathname):
    ''' Get the logger modelnames for test or prod sites and write csv output to a file '''

    if not outfpathname:
        print ("Error: Please provide output csv filepath and name. ")
        return 
    endpointurl = 'v1/equipment-models'
    filterparams = {'category': 'LOGGER', 
        'sort': 'modelname', 
        'page[number]': 1}

    all_data, incl_dict = send_request(mode, endpointurl, filterparams)

    if all_data is None:
        return

    with open(outfpathname, 'w', newline='') as csvfile:
        # Specify columns to be written out
        fieldnames = ['modelname', 'manufacturer', 'family', 'description', 'notes', 'createdby', 'datecreated', 'modifiedby', 'datemodified']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for r in all_data:
            writer.writerow(r['attributes'])

def get_equipment(mode, outfpathname, modelnames, operatorcodes, inventory_states=[]):
    ''' Get the equipment and write csv output to a file. 
        Requires two parameters used to filter the output: modelnames and operatorcodes
        Optional input: inventory  '''

    if not outfpathname:
        print ("Error: Please provide output csv filepath and name. ")
        return 
    if not modelnames and not operatorcodes:
        print ("Error: Please provide modelname and operatorcode to limit the result. ")
        return 

    endpointurl = 'v1/equipment'

    filterparams = {'modelname': ','.join(modelnames),
        'operatorcode': ','.join(operatorcodes), 
        'page[number]': 1}
    if inventory_states:
        filterparams['inventory'] = ','.join(inventory_states)

    try:
        all_data, incl_dict = send_request(mode, endpointurl, filterparams)
    except:
        # Add error handling as needed. For now doing nothing
        return

    if all_data is None:
        return

    # Flatten the data for a csv output. Extract the attributes, and values from sub-dicts for equip epoch and ipaddress. 
    attr_keys = ['serialnumber', 'sourcetemplate', 'notes', 'createdby', 'datecreated', 'modifiedby', 'datemodified',]

    ee_keys = ['operatorcode', 'ownercode', 'inventory']
    model_keys = ['category', 'manufacturer', 'modelname']
    equips = []
    for r in all_data:

        # Get values from attributes
        attribs = r['attributes']
        equip = { k: attribs[k] for k in attr_keys }

        # Demo to show how to get information from the included section
        # Get the model name, category, manufacturer from incl_dict
        modellookup = r['relationships']['equipmodel']['data']
        model = incl_dict[modellookup['type']][modellookup['id']]
        modeldict = { k: model[k] for k in model_keys }
        equip.update(modeldict)

        # Demo to show how to get information from a sub dictionary (equipepochs, equipips, equipsettings)
        # Extract inventory state and operator from latest epoch
        for ee in attribs['equipepochs']:
            if ee['offdate'] is None:       # Client side filtering
                ee_data = {k: ee[k] for k in ee_keys}
                equip.update(ee_data) 

        # Get the ipv4address for demo.  
        # Merge all IP addresses (0 to many) into one comma separated list
        ips = [ ip.get('ipv4address', None) for ip in attribs['equipips'] ]
        equip['ipv4addresses'] = ', '.join(ips) if ips else ''


        # Client side filtering: Get one equip setting "sim-id" for demo. 
        # The setting keys depend on the model and could be an input param rather than hardcoded here. 
        for setting in attribs['equipsettings']:
            if setting['keyname'] == 'SIM-ID':
                equip['sim-id'] = setting['settingvalue']

        # Add the equipment dict into the list. 
        equips.append(equip)
    
    with open(outfpathname, 'w', newline='') as csvfile:
        # Specify columns to be written out
        fieldnames = ['category', 'manufacturer', 'modelname', 'serialnumber', 'operatorcode', 'ownercode', 'inventory', 'ipv4addresses', 'sim-id', 'sourcetemplate', 'notes', 'createdby', 'datecreated', 'modifiedby', 'datemodified',]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for equip in equips:
            writer.writerow(equip)

def get_equipinstall(mode, outfpathname, categorys, netcodes, lookupcodes=[]):
    ''' Get the equipment installation and write csv output to a file.
        Requires two parameters used to filter the output: netcodes and categorygroups
        Optional input: lookupcode  '''

    if not outfpathname:
        print ("Error: Please provide output csv filepath and name. ")
        return
    if not categorys:
        print ("Error: Please provide categories to limit the result. ")
        return

    endpointurl = 'v1/equipment-installations'

### construct filter string
    proto_filter = {'category': ','.join(categorys)}
    sort_opt = {'sort': 'category'}
    if netcodes:
       proto_filter = {**proto_filter,**{'netcode':','.join(netcodes)}}
       sort_opt = {'sort': 'netcode'}
    if lookupcodes:
       proto_filter = {**proto_filter,**{'lookupcode':','.join(lookupcodes)}}
       sort_opt = {'sort': 'lookupcode'}
    proto_filter = {**proto_filter,**{'isactive': 'y','page[number]': 1}}
    filterparams = {**proto_filter,**sort_opt}

    try:
        print(filterparams)
        all_data, incl_dict = send_request(mode, endpointurl, filterparams)
    except:
        # Add error handling as needed. For now doing nothing
        return

    if all_data is None:
        return

    # Flatten the data for a csv output. Extract the attributes, and values from sub-dicts for equip epoch and ipaddress.
    attr_keys = ['ondate']
    e_keys = ['modelname', 'serialnumber', 'category']
    site_keys = ['netcode', 'lookupcode']
    equips = []
    for r in all_data:

        # Get values from attributes
        attribs = r['attributes']
        equipinstall = { k: attribs[k] for k in attr_keys }
        equip = equipinstall

        # Demo to show how to get information from the included section
        # Get the model name, category, manufacturer from incl_dict
        equiplookup = r['relationships']['equipment']['data']
        equipm = incl_dict[equiplookup['type']][equiplookup['id']]
        equipdict = { k: equipm[k] for k in e_keys }
        equip.update(equipdict)

        # Extract lookupcode from latest epoch
        selookup = r['relationships']['siteepoch']['data']
        sepoch = incl_dict[selookup['type']][selookup['id']]
        sedict = { k: sepoch[k] for k in site_keys }
        equip.update(sedict)

        equips.append(equip)

    with open(outfpathname, 'w', newline='') as csvfile:
        # Specify columns to be written out
        fieldnames = ['modelname','serialnumber', 'netcode','lookupcode']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for equip in equips:
            writer.writerow(equip)

def send_request (mode, endpointurl, filterparams):
    ''' Use this function to build and send the request and get all the pages of data.
    Send in filterparams with the url to take advantage of server side filtering and to reduce extra large results.
    If a huge resultset is expected, add in code to handle errors that might be raised because of server side throttling.
    '''
    if mode not in config:
        print (f'Error in input parameters. Valid values for mode are {list(config.keys())}. Received {mode}')
        return
    baseurl = config[mode]['baseurl']
    url = f'{baseurl}/{endpointurl}'
    token = read_token_file(mode)
    # Set the token in the request header
    auth_header = {'Authorization': f'Bearer {token}',}
    
    # Initialize a list to store all the data entries. Relevant when the result is split over many pages.
    all_data = []
    
    # Initialize a dict to reorganize and save the included elements into a dict of this form: { type: { id: { attributes dict }}}
    incl_dict = defaultdict(dict)

    try:
        while (True):
            print (f'Sending a request to {url} with filter: {filterparams}')
            r = requests.get(url, headers=auth_header, params=filterparams, )
            r.raise_for_status()
            res = r.json()
            all_data.extend(res['data'])
            included = res.get('included', None)
            if included:
                for entry in included:
                    incl_dict[entry['type']][entry['id']] = entry['attributes']

            number_of_pages = res['meta']['pagination']['pages']

            # Go to the next page. Use this method, or look under links > next for the url.
            filterparams['page[number]'] += 1
            if filterparams['page[number]'] > number_of_pages:
                break
    
    except requests.exceptions.HTTPError as e:
        print ('ERROR: Request failed.', e)
        print ('The token might be invalid or expired. Get another token by using the SIS UI > Your Account page > Generate Token. Copy the token into the token file')
        raise    
    except Exception as e:
        print ('ERROR: ', e)
        raise
    else:
        return all_data, incl_dict


def main():
    parser = argparse.ArgumentParser(description='SIS Webservice Reports')
    parser.add_argument('mode', choices=config.keys(), default='test',
                        help='Connect to SIS test or production')
    subparsers = parser.add_subparsers(title='Report type', dest='reporttype')

    # Create the subparser for loggermodel report
    parser_lm = subparsers.add_parser('getloggermodel', )
    parser_lm.add_argument('outfilename', help='Path and name of output csv file')

    # Create the subparser for equipment report
    parser_eq = subparsers.add_parser('getequipment', )
    parser_eq.add_argument('outfilename', help='Path and name of output csv file')
    parser_eq.add_argument('--modelnames', required=True, nargs='+', help='Equipment Modelnames')
    parser_eq.add_argument('--operatorcodes', required=True, nargs='+', help='Operator codes')
    parser_eq.add_argument('--inventory', nargs='+', help='Inventory states')

    # Create the subparser for equipment installation report
    parser_eq = subparsers.add_parser('getequipinstall', )
    parser_eq.add_argument('outfilename', help='Path and name of output csv file')
    parser_eq.add_argument('--categorys', required=True, nargs='+', help='Categorys')
    parser_eq.add_argument('--netcodes', nargs='+', help='Net codes')
    parser_eq.add_argument('--lookupcodes', nargs='+', help='Lookup Code')

    args = parser.parse_args()

    if args.reporttype:
        if args.reporttype == 'getloggermodel':
            get_logger_models(args.mode, args.outfilename)
        elif args.reporttype == 'getequipment':
            get_equipment(args.mode, args.outfilename, args.modelnames, args.operatorcodes, args.inventory)
        elif args.reporttype == 'getequipinstall':
            get_equipinstall(args.mode, args.outfilename, args.categorys, args.netcodes, args.lookupcodes)

if __name__ == "__main__":
    main()
