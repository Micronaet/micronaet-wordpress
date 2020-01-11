import os
import woocommerce
import pickle
import urllib
import sys
import erppeek
import ConfigParser

# -----------------------------------------------------------------------------
# Read configuration parameter:
# -----------------------------------------------------------------------------
mode = 'openerp' # 'local'
company_list = ['fia', 'gpb']
lang_list = ['it_IT', 'en_US']
connector_id = 0 # TODO?

update = {
    'images': False,
    'variation_images': True,
    'category': True,
    
    'brand': True,
    'price': True,
    'stock': True,
    'text': True,
    'dimension': True, # and weight
    'status': True, # published, unpublished
    }

# Log mode:
option_log = 'Start options:'
for option in update:
    option_log += '\n%s: %s' % (option, update[option])
print option_log

pools = {}
for company in company_list:
    pools[company] = {}
    for lang in lang_list:
        pools[company][lang] = {}
        
        pools[company][lang]['product'] = {}
        pools[company][lang]['web_product'] = {}
    
config = ConfigParser.ConfigParser()

# Worpress parameters:
cfg_file = os.path.expanduser('../wordpress.cfg')
config.read([cfg_file])
wordpress_url = config.get('wordpress', 'url')
consumer_key = config.get('wordpress', 'key')
consumer_secret = config.get('wordpress', 'secret')

for company in company_list: #['fia', 'gpb']:
    cfg_file = os.path.expanduser('../%s.%s.cfg' % (mode, company))
    config.read([cfg_file])
    dbname = config.get('dbaccess', 'dbname')
    user = config.get('dbaccess', 'user')
    pwd = config.get('dbaccess', 'pwd')
    server = config.get('dbaccess', 'server')
    port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

    # -------------------------------------------------------------------------
    # Connect to ODOO:
    # -------------------------------------------------------------------------    
    for lang in lang_list:        
        odoo = erppeek.Client(
            'http://%s:%s' % (server, port), 
            db=dbname, user=user, password=pwd,
            )
        odoo.context = {'lang': lang}
        
        # Pool used:
        pools[company][lang]['product'] = \
            odoo.model('product.product') 
        pools[company][lang]['web_product'] = \
            odoo.model('product.product.web.server') 

# Spaziogiardino
wcapi = woocommerce.API(
    url=wordpress_url,
    consumer_key=consumer_key,
    consumer_secret=consumer_secret,
    wp_api=True,
    version='wc/v3',
    query_string_auth=True,
    timeout=600,
    )

# -----------------------------------------------------------------------------
# Update category:
# -----------------------------------------------------------------------------
'''
parameter = {'per_page': 10, 'page': 1}
while True:
    reply = wcapi.get("products/categories", params=parameter).json()
    parameter['page'] += 1    

    try:
        if reply.get['data']['status'] >= 400:
            print 'Error getting category list', reply
            break
    except:
        pass # Records present    

    if not reply:
        break

    for record in reply:
        print record['id'], record['lang'], record['name'], record['parent']
'''

for company in company_list:
    # Search italian product linked to WP product
    select_pool = pools[company][lang]['web_product']
    web_product_ids = select_pool.search([
        ('wp_it_id', '!=', False), 
        #('product_id.default_code', 'in', ('913006', 'SE31BB', 'LE00TG', '096458', '127SB ALAN', '830TX ANBI', '129D  ANBIBE', '127   BSJUT')), # TODO remove
        ])
    if not web_product_ids:
        continue

    for web_product in select_pool.browse(web_product_ids):        
        for lang in lang_list:            
            # -----------------------------------------------------------------
            #                            MASTER:
            # -----------------------------------------------------------------
            wp_lang = lang[:2]
            wp_id = eval('web_product.wp_%s_id' % wp_lang) 
            need_update = False
                   
            data = {
                'lang': wp_lang,
                }
            
            # -----------------------------------------------------------------
            # Category:
            # -----------------------------------------------------------------
            if update['category'] and wp_lang == 'it': # only Italy
                data['categories'] = []                
                for category in web_product.wordpress_categ_ids:
                    wp_category_id = eval(
                        'category.wp_%s_id' % wp_lang)
                    if category.parent_id:
                        wp_category_parent_id = eval(
                            'category.parent_id.wp_%s_id' % wp_lang)
                    else:
                        wp_category_parent_id = False        
                        
                    if wp_category_id:
                        data['categories'].append({'id': wp_category_id})
                    if wp_category_parent_id:
                        data['categories'].append({'id': wp_category_parent_id})

                if data['categories']:
                    need_update = True

            # -----------------------------------------------------------------
            # Master image:
            # -----------------------------------------------------------------
            if update['images'] and wp_lang == 'it': # only Italy
                data['images'] = []      
                for image in web_product.wp_dropbox_images_ids:
                    dropbox_link = image.dropbox_link
                    if dropbox_link and dropbox_link.startswith('http'):                        
                        data['images'].append({
                            'src': image.dropbox_link,
                            })
                        need_update = True
                          
            # -----------------------------------------------------------------
            # Update master product:
            # -----------------------------------------------------------------
            if need_update:                    
                call = 'products/%s' % wp_id
                reply = wcapi.put(call, data).json()    
                print 'Company: %s [%s] wcapi.put(%s, %s)' % (
                    company, lang, call, data)
                            
            # -----------------------------------------------------------------
            # Slave image:
            # -----------------------------------------------------------------
            call = 'products/%s/variations' % wp_id
            reply = wcapi.get(call).json()
            for variation in reply:
                variation_id = variation['id']
                variation_sku = variation['sku'].replace('&nbsp;', ' ')
                variation_lang = variation['lang']
                
                for company in company_list:    
                    variation_pool = pools[company]['it_IT']['web_product'] 
                    variation_ids = variation_pool.search([
                        ('product_id.default_code', '=', variation_sku),
                        ])
                    if variation_ids:
                        variation_odoo = variation_pool.browse(
                            variation_ids)[0]
                        
                        data = {
                            'lang': wp_lang,
                            }
                        variation_update = False
                        if update['variation_images'] and wp_lang == 'it': # only Italy
                            for image in variation_odoo.wp_dropbox_images_ids:
                                dropbox_link = image.dropbox_link
                                if dropbox_link and \
                                        dropbox_link.startswith('http'):                        
                                    data['image'] = [{
                                        'src': image.dropbox_link,
                                        }]
                                    variation_update = True
                                break # Only one image in variant!
                        if not variation_update:
                            print 'Variation no image in %s' % variation_sku
                            continue

                        reply = wcapi.put('products/%s/variations/%s' % (
                            wp_id, variation_id), data).json()
                        print 'Variation update image in %s' % variation_sku

