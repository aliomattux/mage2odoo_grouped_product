# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp.osv import fields
from openerp.osv import osv
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare

class StockMove(osv.osv):
    _inherit = 'stock.move'


    def action_confirm(self, cr, uid, ids, context=None):
        move_ids = []
        for move in self.browse(cr, uid, ids, context=context):
            #in order to explode a move, we must have a picking_type_id on that move because otherwise the move
            #won't be assigned to a picking and it would be weird to explode a move into several if they aren't
            #all grouped in the same picking.
            if move.picking_type_id:
                move_ids.extend(self._action_explode(cr, uid, move, context=context))
            else:
                move_ids.append(move.id)

        #we go further with the list of ids potentially changed by action_explode
        return super(StockMove, self).action_confirm(cr, uid, move_ids, context=context)


    def _action_explode(self, cr, uid, move, context=None):
        """ Explodes pickings.
        @param move: Stock moves
        @return: True
        """
        if context is None:
            context = {}
        move_obj = self.pool.get('stock.move')
        prod_obj = self.pool.get("product.product")
        proc_obj = self.pool.get("procurement.order")
        uom_obj = self.pool.get("product.uom")
        to_explode_again_ids = []

	if move.product_id.mage_type == 'grouped' and move.product_id.grouped_products:
            processed_ids = []

            for component in move.product_id.grouped_products:
		product = component.product
                if product.type != 'service':
                    valdef = {
                        'picking_id': move.picking_id.id if move.picking_id else False,
                        'product_id': product.id,
                        'product_uom': product.uom_id.id,
                        'product_uom_qty': component.qty,
                        'product_uos': product.uom_id.id,
                        'product_uos_qty': component.qty,
                        'state': 'draft',  #will be confirmed below
                        'name': product.name,
                        'procurement_id': move.procurement_id.id,
                        'split_from': move.id, #Needed in order to keep sale connection, but will be removed by unlink
                    }
                    mid = move_obj.copy(cr, uid, move.id, default=valdef, context=context)
                    to_explode_again_ids.append(mid)
                else:
                    if prod_obj.need_procurement(cr, uid, [product.id], context=context):
                        valdef = {
                            'name': move.rule_id and move.rule_id.name or "/",
                            'origin': move.origin,
                            'company_id': move.company_id and move.company_id.id or False,
                            'date_planned': move.date,
                            'product_id': product.id,
                            'product_qty': component.qty,
                            'product_uom': product.uom_id.id,
                            'product_uos_qty': component.qty,
                            'product_uos': product.uom_id.id,
                            'group_id': move.group_id.id,
                            'priority': move.priority,
                            'partner_dest_id': move.partner_id.id,
                            }
                        if move.procurement_id:
                            proc = proc_obj.copy(cr, uid, move.procurement_id.id, default=valdef, context=context)
                        else:
                            proc = proc_obj.create(cr, uid, valdef, context=context)
                        proc_obj.run(cr, uid, [proc], context=context) #could be omitted
            
            #check if new moves needs to be exploded
            if to_explode_again_ids:
                for new_move in self.browse(cr, uid, to_explode_again_ids, context=context):
                    processed_ids.extend(self._action_explode(cr, uid, new_move, context=context))
            
            if not move.split_from and move.procurement_id:
                # Check if procurements have been made to wait for
                moves = move.procurement_id.move_ids
                if len(moves) == 1:
                    proc_obj.write(cr, uid, [move.procurement_id.id], {'state': 'done'}, context=context)

            if processed_ids and move.state == 'assigned':
                # Set the state of resulting moves according to 'assigned' as the original move is assigned
                move_obj.write(cr, uid, list(set(processed_ids) - set([move.id])), {'state': 'assigned'}, context=context)
                
            #delete the move with original product which is not relevant anymore
            move_obj.unlink(cr, SUPERUSER_ID, [move.id], context=context)
            #return list of newly created move
            return processed_ids

        return [move.id]


