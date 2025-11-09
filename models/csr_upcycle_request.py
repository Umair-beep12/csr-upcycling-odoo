"""CSR Upcycle Request core model."""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CSRUpcycleRequest(models.Model):
    """Internal upcycle transactions capturing circular metrics per department."""

    _name = "csr.upcycle.request"
    _description = "CSR Upcycle Request"
    _order = "create_date desc"

    name = fields.Char(required=True, default=lambda self: _('New Upcycle Request'))
    request_date = fields.Date(default=lambda self: fields.Date.context_today(self))
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        required=True,
        ondelete='restrict'
    )
    product_co2e_per_unit = fields.Float(string='CO₂e/Unit Snapshot (kg)', digits=(16, 4))
    product_cost_per_unit = fields.Float(string='Value/Unit Snapshot (AED)', digits=(16, 2))
    department_id = fields.Many2one('hr.department', required=True, ondelete='restrict')
    requested_by_id = fields.Many2one(
        'res.users',
        string='Requested By',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict'
    )
    quantity = fields.Float(default=1.0, required=True)
    reason = fields.Text(string='Internal Notes')

    co2e_avoided = fields.Float(string='CO₂e Avoided (kg)', compute='_compute_impacts', store=True)
    aed_saved = fields.Float(string='AED Saved', compute='_compute_impacts', store=True)
    ceits_awarded = fields.Float(string='CEITs Awarded', compute='_compute_impacts', store=True)

    approval_date = fields.Datetime(string='Approved On')
    done_date = fields.Datetime(string='Completed On')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('done', 'Done'),
    ], default='draft')

    _sql_constraints = [
        ('quantity_positive', 'CHECK(quantity > 0)', 'Quantity must be greater than zero.')
    ]

    @api.depends('quantity', 'product_co2e_per_unit', 'product_cost_per_unit')
    def _compute_impacts(self):
        for request in self:
            qty = request.quantity or 0.0
            co2 = request.product_co2e_per_unit or 0.0
            cost = request.product_cost_per_unit or 0.0
            request.co2e_avoided = qty * co2
            request.aed_saved = qty * cost
            request.ceits_awarded = round((request.co2e_avoided / 5.0) + (request.aed_saved / 100.0), 2)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for request in self:
            if request.product_id:
                request.product_co2e_per_unit = request.product_id.co2e_per_unit
                request.product_cost_per_unit = request.product_id.cost_per_unit

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._apply_product_snapshot(vals)
            vals.setdefault('requested_by_id', self.env.uid)
            vals.setdefault('request_date', fields.Date.context_today(self))
        records = super().create(vals_list)
        return records

    def write(self, vals):
        vals = vals.copy()
        if 'product_id' in vals:
            self._apply_product_snapshot(vals)
        return super().write(vals)

    def _apply_product_snapshot(self, vals):
        product_id = vals.get('product_id')
        if product_id:
            product = self.env['product.template'].browse(product_id)
            vals.setdefault('product_co2e_per_unit', product.co2e_per_unit)
            vals.setdefault('product_cost_per_unit', product.cost_per_unit)

    def _ensure_submission_ready(self):
        for request in self:
            missing = []
            if not request.product_id:
                missing.append(_('Product'))
            if not request.department_id:
                missing.append(_('Department'))
            if not request.quantity:
                missing.append(_('Quantity'))
            if missing:
                raise ValidationError(
                    _('Cannot submit "%s" because the following fields are missing or invalid: %s') %
                    (request.display_name, ', '.join(missing))
                )

    # -- Workflow helpers -------------------------------------------------
    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                continue
            request._ensure_submission_ready()
            request.state = 'submitted'
        return True

    def action_approve(self):
        self._check_manager_rights()
        for request in self:
            if request.state != 'submitted':
                continue
            request.state = 'approved'
            request.approval_date = fields.Datetime.now()
        return True

    def action_reject(self):
        self._check_manager_rights()
        for request in self:
            if request.state in ('draft', 'done'):
                continue
            request.state = 'rejected'
        return True

    def action_mark_done(self):
        self._check_manager_rights()
        for request in self:
            if request.state not in ('approved',):
                continue
            request.state = 'done'
            request.done_date = fields.Datetime.now()
            request._create_reward_entry()
        return True

    def action_reset_to_draft(self):
        for request in self:
            request.state = 'draft'
            request.approval_date = False
            request.done_date = False
        return True

    def _check_manager_rights(self):
        if not self.env.user.has_group('csr_upcycling.group_csr_manager'):
            raise ValidationError(_('Only CSR Upcycling Managers can perform this action.'))

    def _create_reward_entry(self):
        self.ensure_one()
        if not self.requested_by_id:
            return
        Reward = self.env['csr.employee.reward']
        existing = Reward.search([
            ('request_id', '=', self.id),
            ('user_id', '=', self.requested_by_id.id),
        ], limit=1)
        if existing:
            return
        Reward.create({
            'name': _('Reward for %s') % self.name,
            'user_id': self.requested_by_id.id,
            'points': self.ceits_awarded or 0.0,
            'reason': _('Automatic reward for completing "%s".') % (self.name,),
            'request_id': self.id,
        })

    def action_view_related_product(self):
        self.ensure_one()
        if not self.product_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': self.product_id.display_name,
            'res_model': 'product.template',
            'view_mode': 'form',
            'res_id': self.product_id.id,
            'target': 'current',
        }

    def action_view_related_department(self):
        self.ensure_one()
        if not self.department_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': self.department_id.display_name,
            'res_model': 'hr.department',
            'view_mode': 'form',
            'res_id': self.department_id.id,
            'target': 'current',
        }
