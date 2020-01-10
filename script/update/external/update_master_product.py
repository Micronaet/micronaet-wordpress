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
    'images': True,
    'category': False,
    'price': True,
    'stock': True,
    'text': True,
    'dimension': True, # and weight
    }

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
        ('product_id.default_code', '=', '7767936'), # TODO remove
        ])
    if not web_product_ids:
        continue

    for web_product in select_pool.browse(web_product_ids):        
        for lang in lang_list:            
            wp_lang = lang[:2]

            wp_id = eval('web_product.wp_%s_id' % wp_lang) 
                   
            data = {
                'lang': wp_lang,
                }
            need_update = False
            
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
                #else:
                #    print 'No category present'    

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
                          
            # -----------------------------------------------------------------
            # Update master product:
            # -----------------------------------------------------------------
            call = 'products/%s' % wp_id
            #reply = wcapi.put(call, data).json()    
            print 'Company: %s [%s] wcapi.put(%s, %s)' % (
                company, lang, call, data)
            #print reply    
            
'''
{'sku': u'7767936', 'lang': 'it', 'categories': [{'id': 571}, {'id': 547}, {'id': 593}, {'id': 549}, {'id': 635}, {'id': 555}], 'description': u"Vegas e' un tavolo da esterno allungabile in maniera telescopica, le gambe e il piano sono realizzate in polipropilene rinforzato in fibra di vetro  trattato anti-uv, colorato in massa. Il piano e' sorretto da barre in acciaio zincato. I piedini sono regolabili. Vegas dotato di una una prolunga esterna di 40 cm pu\xf2 raggiungere una lunghezza massima di 300 cm."}

call = 'products/18313'
data = {
    'sku': u'913006', 
    'lang': 'it', 
    'name': u'SEDIA FLASH', 
    'regular_price': u'58.0', 
    'status': 'publish', 
    'catalog_visibility': 'visible', 
    'short_description': u'SET 4 SEDIE IMPILABILI FLASH  IN POLICARBONATO', 
    'stock_quantity': 8, 
    'wp_type': u'variable', 
    'type': u'variable', 
    'categories': [{'id': 567}, {'id': 547}, {'id': 589}, {'id': 549}, {'id': 619}, {'id': 553}, {'id': 629}, {'id': 555}], 
    'description': u'Flash \xe8 una sedia classica nella linea, resistente nel materiale (la seduta \xe8 in polipropilene  rinforzato con fibra di vetro e lo schienale in policarbonato), armoniosa nella proporzione,  che la rende perfetta per ambienti moderni e giovani. Il design rivisito in chiave moderno e tecnologico la forma armoniosa di una delle sedie pi\xf9 semplici ma pi\xf9 utilizzate di tutti i tempi, in un contrasto tra passato e presente che \xe8 la chiave di lettura di molti arredamenti contemporanei. Adatta a personalizzare ogni ambiente, leggera da spostare e impilabile se necessario, comoda e facile da adattare a tutti gli arredi,  Flash \xe8 una sedia molto resistente, idonea sia per uso domestico che per l\u2019uso contract, i materiali utilizzati per la sua costruzione sono idonei anche per l\u2019 uso in ambienti esterni.'
    }
'''


