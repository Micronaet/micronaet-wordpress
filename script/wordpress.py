#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

import os
import sys
from requests import request
import json # for dumps (json encode procedure)


__author__ = 'nicola.riolini@gmail.com'
__title__ = 'odoo-woocommerce-api'
__version__ = '1.0'
__license__ = 'AGPL'

parameters = {
    'url': 'http://demo8.evoluzionetelematica.it/spaziogiardino.it',
    'consumer_key': 'ck_f00df6028cc22a7e0bf0b8f4579e5f36bd83866a',
    'consumer_secret': 'cs_a9998513e0c5f1af1abd74885e90f48e49082a78',
    }

kwargs = {
    'wp_api': 'wp_api',
    'version': 'wc/v3',
    # 'is_ssl': False,
    'timeout': 5,
    # 'verify_ssl': False,
    # 'query_string_auth': False,
    }


class API(object):
    """ API Class for manage request
    """

    def __init__(self, url, consumer_key, consumer_secret, **kwargs):
        self.url = url
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.wp_api = kwargs.get('wp_api', True)
        self.version = kwargs.get('version', 'wc/v3')
        # self.is_ssl = self.__is_ssl()
        self.timeout = kwargs.get('timeout', 5)
        # self.verify_ssl = kwargs.get('verify_ssl', True)
        # self.query_string_auth = kwargs.get('query_string_auth', False)

    # def __is_ssl(self):
    #    ''' Check if url use HTTPS '''
    #    return self.url.startswith('https')

    def __get_url(self, endpoint):
        """ Get URL for requests """
        url = self.url
        api = 'wc-api'

        if url.endswith('/') is False:
            url = '%s/' % url

        if self.wp_api:
            api = 'wp-json'

        return '%s%s/%s/%s' % (url, api, self.version, endpoint)

    def __request(self, method, endpoint, data, params=None, **kwargs):
        """ Do requests
        """
        import pdb; pdb.set_trace()
        if params is None:
            params = {}
        url = self.__get_url(endpoint)
        headers = {
            'user-agent': 'WooCommerce API Client-Python/%s' % __version__,
            'accept': 'application/json'
            }

        auth = (self.consumer_key, self.consumer_secret)
        params.update({
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret
            })
        # if self.is_ssl is True and self.query_string_auth is False:
        # elif self.is_ssl is True and self.query_string_auth is True:
        #    params.update({
        #        'consumer_key': self.consumer_key,
        #        'consumer_secret': self.consumer_secret
        #        })
        # else:
        #    print 'ERROR'

        if data is not None:
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            headers['content-type'] = 'application/json;charset=utf-8'

        return request(
            method=method,
            url=url,
            # verify=self.verify_ssl,
            auth=auth,
            params=params,
            data=data,
            timeout=self.timeout,
            headers=headers,
            **kwargs
        )

    def get(self, endpoint, **kwargs):
        """ Get requests """
        return self.__request('GET', endpoint, None, **kwargs)

    def post(self, endpoint, data, **kwargs):
        """ POST requests """
        return self.__request('POST', endpoint, data, **kwargs)

    def put(self, endpoint, data, **kwargs):
        """ PUT requests """
        return self.__request('PUT', endpoint, data, **kwargs)

    def delete(self, endpoint, **kwargs):
        """ DELETE requests """
        return self.__request('DELETE', endpoint, None, **kwargs)

    def options(self, endpoint, **kwargs):
        """ OPTIONS requests """
        return self.__request('OPTIONS', endpoint, None, **kwargs)

#WP = API(
#    parameters['url'],
#    parameters['consumer_key'],
#    parameters['consumer_secret'],
#    **kwargs)
#
#print WP.get('orders')
#import pdb; pdb.set_trace()

res = request(
    method='GET',
    url='http://demo8.evoluzionetelematica.it/spaziogiardino.it/wp-json/wc/v3/products',
    auth=(
        'ck_f00df6028cc22a7e0bf0b8f4579e5f36bd83866a',
        'cs_a9998513e0c5f1af1abd74885e90f48e49082a78',
        ),
    params={},
    data='',
    timeout=5,
    headers={
        'user-agent': 'ODOO API Client-Python/1.0',
        'accept': 'application/json'
        },
    )
print(res.text)
url = 'http://demo8.evoluzionetelematica.it/spaziogiardino.it/wp-json/wc/v3/products'
key = 'ck_f00df6028cc22a7e0bf0b8f4579e5f36bd83866a'
secret = 'cs_a9998513e0c5f1af1abd74885e90f48e49082a78'
command = 'curl %s -u %s:%s '  % (
    url,
    key,
    secret,
    )
print(command)
os.system(command)

import pdb; pdb.set_trace()
from woocommerce import API

url = 'http://demo8.evoluzionetelematica.it/spaziogiardino.it'
wcapi = API(
    url=url,
    consumer_key=key,
    consumer_secret=secret,
    wp_api=True,
    version="wc/v3"
)
print(wcapi.get("products").json())
