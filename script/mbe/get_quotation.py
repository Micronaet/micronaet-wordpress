#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import pdb
import requests
from datateime import datetime
from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
import xml.etree.cElementTree as ElementTree

location = 'https://api.mbeonline.it/ws'
username = 'user'
password = 'password'

data = {
    # 'Credentials': {'Username': '', 'Passphrase': ''},
    'InternalReferenceID': 'ODOO11-lg',
    'ShippingParameters': {
        # 'Courier': '',
        # 'Service': '',
        'Items': {'Item': [{
            'Dimensions': {
                'Width': 30,
                'Lenght': 20,
                'Height': 20
                },
            'Weight': 5}
        ]},
        'DestinationInfo': {
           'Country': 'IT',
           'State': 'BS',
           # 'idSubzone': '',
           'ZipCode': '25100',
           'City': 'Brescia'
           },
        # 'CourierService': '',
        'PackageType': 'GENERIC',
        'ShipType': 'EXPORT'
        },
    'System': 'IT'
    }


# -----------------------------------------------------------------------------
#                                  Utility:
# -----------------------------------------------------------------------------
# ODOO >> MBE 
# -----------------------------------------------------------------------------
def dict2xml(dictionary, level=0, cr=''):
    """ Turn a simple dict of key/value pairs into XML
    """
    result = ''
    level += 1
    spaces = ' ' * level
    for key, value in dictionary.items():
       if type(value) == dict:
           result += '%s<%s>%s%s%s</%s>%s' % (
               spaces, key, cr, dict2xml(value, level, cr), spaces, key, cr)
       elif type(value) == list:
           for item in value:
               result += '%s<%s>%s%s%s</%s>%s' % (
                  spaces, key, cr, dict2xml(item, level, cr), spaces, key, cr)
       else:
           result += '%s<%s>%s</%s>%s' % (spaces, key, value, key, cr)
    return result


def get_envelope(request, dictionary, cr=''):
    """ Extract xml from dict and put in envelope:
    """
    reply = dict2xml(dictionary, level=4, cr=cr)
    result = '''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://www.onlinembe.it/ws/">
        <soapenv:Header/>
        <soapenv:Body>
            <ws:%s>
                <RequestContainer>%s</RequestContainer>
            </ws:%s>
        </soapenv:Body>
    </soapenv:Envelope>''' % (request, reply, request)
    return result.replace('\n', '').replace('\t', '    ')


# -----------------------------------------------------------------------------
# XML2Dict
# -----------------------------------------------------------------------------
def get_in_type(text):
    """ Return in correct value
    """
    # Boolean:
    if text == 'true':
        return True
    if text == 'false':
        return False

    # Datetime

    # Date

    # Integer
    if not (text or '').startswith('0'):
        try:
            return int(text)
        except:
            pass

            # Float
        try:
            return float(text)
        except:
            pass
    return text


class XmlListConfig(list):
    def __init__(self, aList):
        for element in aList:
            if element:
                # treat like dict
                if len(element) == 1 or element[0].tag != element[1].tag:
                    self.append(XmlDictConfig(element))
                # treat like list
                elif element[0].tag == element[1].tag:
                    self.append(XmlListConfig(element))
            elif element.text:
                text = element.text.strip()
                if text:
                    self.append(text)


class XmlDictConfig(dict):
    """
    Example usage:
    >>> tree = ElementTree.parse('your_file.xml')
    >>> root = tree.getroot()
    >>> xmldict = XmlDictConfig(root)

    Or, if you want to use an XML string:
    >>> root = ElementTree.XML(xml_string)
    >>> xmldict = XmlDictConfig(root)
    And then use xmldict for what it is... a dict.
    """

    def __init__(self, parent_element):
        """ Creator of instance
        """
        if parent_element.items():
            self.update(dict(parent_element.items()))
            
        for element in parent_element:
            if element:
                # treat like dict - we assume that if the first two tags
                # in a series are different, then they are all different.
                if len(element) == 1 or element[0].tag != element[1].tag:
                    aDict = XmlDictConfig(element)
                # treat like list - we assume that if the first two tags
                # in a series are the same, then the rest are the same.
                else:
                    # here, we put the list in dictionary; the key is the
                    # tag name the list elements all share in common, and
                    # the value is the list itself
                    aDict = {element[0].tag: XmlListConfig(element)}
                    
                # if the tag has attributes, add those to the dict
                if element.items():
                    aDict.update(dict(element.items()))
                self.update({element.tag: aDict})
                
            # this assumes that if you've got an attribute in a tag,
            # you won't be having any text. This may or may not be a
            # good idea -- time will tell. It works for the way we are
            # currently doing XML configuration files...
            elif element.items():
                self.update({element.tag: dict(element.items())})
                
            # finally, if there are no child tags and no attributes, extract
            # the text or the correct type (if it's possible)
            else:
                self.update({element.tag: get_in_type(element.text)})


# -----------------------------------------------------------------------------
# Request call:
# -----------------------------------------------------------------------------
header = {'Content-Type': 'text/xml'}

packages = []
for line in open('./data/package.csv', 'r'):
    line = line.strip()
    if not line:
        continue
    row = line.split('|')
    if len(row) != 4:
        print('Not a package row: %s' % line)
    packages.append(row)

places = []
for line in open('./data/place.csv', 'r'):
    line = line.strip()
    if not line:
        continue
    row = line.split('|')
    if len(row) != 4:
        print('Not a place row: %s' % line)
    places.append(row)

# Loop in cross package - places
out_file = open('./data/output.csv', 'w')
out_file.write('Package|Destination|Min|Max|Detail\n')
for package in packages:
    weight, H, L, W = package

    for place in places:
        city, state, zipcode, country = place
        max_val = min_val = 0

        # Update data record:
        data['ShippingParameters']['Items']['Item'][0] = {
                'Dimensions': {'Width': W, 'Lenght': L, 'Height': H},
                'Weight': weight,
                }
        data['ShippingParameters']['DestinationInfo'] = {
                'Country': country,
                'State': state or country,
                'City': city,
                'ZipCode': zipcode,
                }

        payload = get_envelope('ShippingOptionsRequest', data, cr='')
        reply = requests.post(
            location,
            auth=HTTPBasicAuth(username, password),
            headers=header,
            data=payload,
            )
        if not reply.ok:
            print('MBE error reply')
            continue
        reply_text = reply.text
        data_block = reply_text.split(
            '<RequestContainer>')[-1].split('</RequestContainer>')[0]

        data_block = str(
            '<RequestContainer>%s</RequestContainer>' % data_block)
        root = ElementTree.XML(data_block)
        result_data = XmlDictConfig(root)
        title = '%s Kg, H%s X L%s X W%s|%s (%s)' % (
            weight, H, L, W, city, country)
        detail = ''
        try:
            options = result_data['ShippingOptions']['ShippingOption']
        except:
            out_file.write('%s|ERR|ERR|Non trovata griglia\n' % title)
            continue
        for record in options:
            price = record['NetShipmentPrice']
            if not min_val:
                min_val = price

            if price < min_val:
                min_val = price
            if price > max_val:
                max_val = price

            detail += '%s EUR: [%s >> %s %s]|' % (
                price,
                record['ServiceDesc'],
                record['CourierServiceDesc'],
                record['Courier'],
                )

        out_line = '%s|%s|%s|%s\n' % (
            title,
            min_val,
            max_val,
            detail,
        )
        out_file.write(out_line)
        out_file.flush()
    out_file.write('\n')  # Empty line between package
