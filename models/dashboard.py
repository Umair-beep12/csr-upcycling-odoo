"""Dashboard data model."""

from odoo import api, fields, models, tools


class CSRUpcyclingDashboard(models.Model):
    _name = 'csr.upcycling.dashboard'
    _description = 'CSR Upcycling Dashboard'
    _auto = False

    name = fields.Char(string='Label')
    department_id = fields.Many2one('hr.department', string='Department')
    total_co2e = fields.Float(string='CO₂e Avoided (kg)')
    total_aed = fields.Float(string='AED Saved')
    total_ceits = fields.Float(string='CEITs Awarded')
    overall_co2e = fields.Float(string='Overall CO₂e')
    overall_aed = fields.Float(string='Overall AED')
    overall_ceits = fields.Float(string='Overall CEITs')
    is_total = fields.Boolean(string='Is Total Row')
    co2e_share = fields.Float(string='CO₂e Share (%)')
    aed_share = fields.Float(string='AED Share (%)')
    ceits_share = fields.Float(string='CEITs Share (%)')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW %(table)s AS
            WITH req AS (
                SELECT department_id,
                       SUM(co2e_avoided) AS total_co2e,
                       SUM(aed_saved) AS total_aed,
                       SUM(ceits_awarded) AS total_ceits
                FROM csr_upcycle_request
                WHERE state IN ('approved', 'done')
                GROUP BY department_id
            ),
            aggregated AS (
                SELECT
                    COALESCE(dept.name->>'en_US', dept.name#>>'{}', 'All Departments') AS name,
                    dept.id AS department_id,
                    req.total_co2e,
                    req.total_aed,
                    req.total_ceits,
                    SUM(req.total_co2e) OVER () AS overall_co2e,
                    SUM(req.total_aed) OVER () AS overall_aed,
                    SUM(req.total_ceits) OVER () AS overall_ceits,
                    CASE WHEN SUM(req.total_co2e) OVER () = 0 THEN 0
                         ELSE (req.total_co2e / NULLIF(SUM(req.total_co2e) OVER (), 0)) * 100 END AS co2e_share,
                    CASE WHEN SUM(req.total_aed) OVER () = 0 THEN 0
                         ELSE (req.total_aed / NULLIF(SUM(req.total_aed) OVER (), 0)) * 100 END AS aed_share,
                    CASE WHEN SUM(req.total_ceits) OVER () = 0 THEN 0
                         ELSE (req.total_ceits / NULLIF(SUM(req.total_ceits) OVER (), 0)) * 100 END AS ceits_share,
                    FALSE AS is_total
                FROM req
                LEFT JOIN hr_department AS dept ON dept.id = req.department_id
            ),
            totals AS (
                SELECT
                    'All Departments' AS name,
                    NULL::integer AS department_id,
                    COALESCE(SUM(total_co2e), 0) AS total_co2e,
                    COALESCE(SUM(total_aed), 0) AS total_aed,
                    COALESCE(SUM(total_ceits), 0) AS total_ceits,
                    COALESCE(SUM(total_co2e), 0) AS overall_co2e,
                    COALESCE(SUM(total_aed), 0) AS overall_aed,
                    COALESCE(SUM(total_ceits), 0) AS overall_ceits,
                    100.0 AS co2e_share,
                    100.0 AS aed_share,
                    100.0 AS ceits_share,
                    TRUE AS is_total
                FROM req
            )
            SELECT row_number() OVER () AS id, *
            FROM (
                SELECT * FROM aggregated
                UNION ALL
                SELECT * FROM totals
            ) AS all_rows
        """ % {'table': self._table})
