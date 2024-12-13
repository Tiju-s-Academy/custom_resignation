from odoo import fields,models


class ResignationType(models.Model):
    _name = 'resignation.type'
    _description = 'Resignation Type'
    _sql_constraints = [('unique_name', 'unique(name)', 'This Type already Exist')]

    name = fields.Char(string='Type',required=True)
    hr_id = fields.Many2one('res.users', string="HR")
    vp_id = fields.Many2one('res.users',string="VP")
    md_ids = fields.Many2many('res.users',string="MD")

