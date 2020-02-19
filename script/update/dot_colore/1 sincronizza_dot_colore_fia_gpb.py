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

connector_id = {
    'fia': 5,
    'gpb': 6,
    }

pools = {}
for company in company_list:
    pools[company] = {}
    for lang in lang_list:
        pools[company][lang] = {}
        
        pools[company][lang]['colors'] = {}
    
config = ConfigParser.ConfigParser()

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
        pools[company][lang]['colors'] = \
            odoo.model('connector.product.color.dot') 

space_problem = []
for company in company_list:
    print 'Working DB', company
    
    for lang in lang_list:       
        print 'Working language', lang
        
        source = {
            'pool': pools[company][lang]['colors'],
            'connector_id': connector_id[company],            
            }
            
        # Destination:
        if company == 'fia':
            destination = {                
                'pool': pools['gpb'][lang]['colors'],
                'connector_id': connector_id['gpb'],            
                }
        else:
            destination = {                
                'pool': pools['fia'][lang]['colors'],
                'connector_id': connector_id['fia'],    
                }

        # Search colors:
        source_color_ids = source['pool'].search([])
        for source_color in source['pool'].browse(source_color_ids):
            name = source_color.name  # Code
            if name != name.strip():            
                print '   Space problem: %s %s %s' % (company, lang, name)
                if name not in space_problem:
                    space_problem.append(name)
                source['pool'].write([source_color.id], {
                    'name': name.strip(),
                    })

            destination_ids = destination['pool'].search([
                '|',
                ('name', '=', name),
                ('name', '=', name.strip()),
                ])

            data = {
                'connector_id': destination['connector_id'],
                'description': source_color.description,
                'hint': source_color.hint,
                'name': source_color.name.strip(),
                'not_active': source_color.not_active,
                }
                
            if destination_ids:
                # Update:
                print 'Update: %s %s %s' % (company, lang, data)
                destination['pool'].write(destination_ids, data)
            else:
                # Create:    
                print 'Create: %s %s %s' % (company, lang, data)
                destination['pool'].create(data)

print 'Space problem:'
print space_problem
