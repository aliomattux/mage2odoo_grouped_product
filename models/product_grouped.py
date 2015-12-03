#Module designed not copy/pasted but basically looked at and written from
#OCA product links module If you want clearer copyright, contact me

from openerp.osv import osv, fields

class MageGroupedProduct(osv.osv):
    _name = 'mage.grouped.product'

#    @api.model
 #   def get_link_type_selection(self):
  #      # selection can be inherited and extended
   #     return [('cross_sell', 'Cross-Sell'),
    #            ('up_sell', 'Up-Sell'),
     #           ('related', 'Related')]

    _columns = {
	'product_tmpl_id': fields.many2one('product.template', 'Parent Product'),
	'product': fields.many2one('product.product', 'Product'),
	'position': fields.integer('Position'),
	'qty': fields.float('Quantity'),
    
    }



class ProductTemplate(osv.osv):
    _inherit = 'product.template'
    _columns = {
	'grouped_products': fields.one2many('mage.grouped.product', 'product_tmpl_id', 'Grouped Products'),
    }
