"""Product template extensions for CSR Upcycling."""

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """Flag SKUs that qualify for CSR upcycling workflows."""

    _inherit = 'product.template'

    upcyclable = fields.Boolean(string='Upcyclable')
    co2e_per_unit = fields.Float(string='CO₂e/Unit (kg)', digits=(16, 4))
    cost_per_unit = fields.Float(string='Value/Unit (AED)', digits=(16, 2))
    upcycle_request_ids = fields.One2many(
        'csr.upcycle.request',
        'product_id',
        string='Upcycle Requests'
    )
    upcycle_request_count = fields.Integer(compute='_compute_upcycle_request_stats', store=False)
    upcycle_last_request_date = fields.Date(
        string='Last Upcycle Request',
        compute='_compute_upcycle_request_stats',
        store=False
    )

    @api.depends('upcycle_request_ids.state', 'upcycle_request_ids.request_date')
    def _compute_upcycle_request_stats(self):
        request_model = self.env['csr.upcycle.request']
        grouped = request_model.read_group(
            [('product_id', 'in', self.ids)],
            ['product_id', 'request_date:max'],
            ['product_id']
        )
        stats = {g['product_id'][0]: g for g in grouped}
        for template in self:
            data = stats.get(template.id)
            template.upcycle_request_count = data['__count'] if data else 0
            template.upcycle_last_request_date = data['request_date_max'] if data else False

    def action_view_upcycle_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': 'csr.upcycle.request',
            'view_mode': 'tree,kanban,form',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
                'search_default_group_by_state': 1,
            },
        }
