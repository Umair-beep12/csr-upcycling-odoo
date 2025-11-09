"""Department KPIs for CSR Upcycling."""

from odoo import api, fields, models


class HRDepartment(models.Model):
    """Augment departments with CSR upcycle KPIs."""

    _inherit = 'hr.department'

    upcycle_request_ids = fields.One2many(
        'csr.upcycle.request',
        'department_id',
        string='Upcycle Requests'
    )
    upcycle_request_count = fields.Integer(compute='_compute_upcycle_metrics', store=True)
    upcycle_total_co2e = fields.Float(string='Total CO₂e Avoided', compute='_compute_upcycle_metrics', store=True)
    upcycle_total_aed = fields.Float(string='Total AED Saved', compute='_compute_upcycle_metrics', store=True)
    upcycle_total_ceits = fields.Float(string='Total CEITs', compute='_compute_upcycle_metrics', store=True)
    upcycle_rank = fields.Integer(string='Impact Rank', compute='_compute_upcycle_rank')

    @api.depends('upcycle_request_ids.state', 'upcycle_request_ids.co2e_avoided',
                 'upcycle_request_ids.aed_saved', 'upcycle_request_ids.ceits_awarded')
    def _compute_upcycle_metrics(self):
        for department in self:
            impactful = department.upcycle_request_ids.filtered(lambda r: r.state in ('approved', 'done'))
            department.upcycle_request_count = len(impactful)
            department.upcycle_total_co2e = sum(impactful.mapped('co2e_avoided'))
            department.upcycle_total_aed = sum(impactful.mapped('aed_saved'))
            department.upcycle_total_ceits = sum(impactful.mapped('ceits_awarded'))

    @api.depends('upcycle_total_ceits')
    def _compute_upcycle_rank(self):
        all_departments = self.search([])
        ranked = sorted(all_departments, key=lambda d: d.upcycle_total_ceits, reverse=True)
        rank_map = {dept.id: idx + 1 for idx, dept in enumerate(ranked)}
        for department in self:
            department.upcycle_rank = rank_map.get(department.id, 0)

    def action_view_upcycle_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Upcycle Requests',
            'res_model': 'csr.upcycle.request',
            'view_mode': 'tree,kanban,form',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id},
        }
