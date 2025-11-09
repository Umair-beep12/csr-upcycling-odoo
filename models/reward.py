"""CSR employee reward tracking."""

from odoo import api, fields, models, _


class CSREmployeeReward(models.Model):
    _name = 'csr.employee.reward'
    _description = 'CSR Employee Reward'
    _order = 'date desc, id desc'

    name = fields.Char(required=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')
    points = fields.Float(string='Points')
    reason = fields.Text()
    date = fields.Date(default=lambda self: fields.Date.context_today(self))
    request_id = fields.Many2one('csr.upcycle.request', ondelete='cascade')


class ResUsers(models.Model):
    _inherit = 'res.users'

    csr_reward_ids = fields.One2many('csr.employee.reward', 'user_id', string='CSR Rewards')
    csr_reward_count = fields.Integer(compute='_compute_csr_reward_count')

    @api.depends('csr_reward_ids')
    def _compute_csr_reward_count(self):
        for user in self:
            user.csr_reward_count = len(user.csr_reward_ids)

    def action_view_csr_rewards(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('CSR Rewards'),
            'res_model': 'csr.employee.reward',
            'view_mode': 'tree,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }
