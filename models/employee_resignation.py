from odoo import api, fields, models,_
from odoo.exceptions import UserError


class EmployeeResignation(models.Model):
    _name = 'employee.resignation'
    _description = 'Employee Resignation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'serial_number'
    # _sql_constraints = [('employee_id_unique', 'unique(employee_id)', 'This Employee already requested for Resignation')]

    serial_number = fields.Char(
        string='New',
        default=lambda self: self.env['ir.sequence'].next_by_code('resignation'),
        copy=False,
        readonly=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
    )
    parent_id = fields.Many2one('hr.employee', string='Responsible Person', compute='_compute_department_id', store=True)
    approved_date = fields.Date(string='Approved Last Date',readonly=1)
    notice_period = fields.Char("Notice Period", default='3 Months')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('in_progress', 'In Progress'),
            ('approved', 'Approved'),
            ('refuse', 'Refuse')
        ],
        default='draft',
        string='Status',
        tracking=True
    )
    resignation_type = fields.Many2one('resignation.type', string='Type',required=True)
    reason = fields.Text(string='Reason')

    approvers = fields.Many2many('res.users','Approvers', string='Approvers', readonly=True, tracking=True)
    can_approve = fields.Boolean(compute='_compute_can_approve', string='Can Approve')

    manager_id = fields.Many2one('res.users', string='Manager')
    hr_id = fields.Many2one('res.users', string='Hr')
    vp_id = fields.Many2one('res.users', string='Vp')
    md_ids = fields.Many2many('res.users','Md', string='Md')

    manager_approved = fields.Boolean(string='Manager Approved', default=False)
    hr_approved = fields.Boolean(string='HR Approved', default=False)
    vp_approved = fields.Boolean(string='VP Approved', default=False)
    md_approved = fields.Boolean(string='MD Approved', default=False)

    @api.depends('state', 'approvers')
    def _compute_can_approve(self):
        current_user = self.env.user
        for record in self:
            record.can_approve = False
            if record.state == 'submitted' and record.parent_id.user_id == current_user and not record.manager_approved:
                record.can_approve = True
            elif record.state == 'in_progress' and current_user.id == record.resignation_type.hr_id.id and record.manager_approved and not record.hr_approved:
                print("hr")
                record.can_approve = True
                if record.resignation_type.hr_id.id == record.parent_id.user_id.id:
                    record.hr_approved = True
                    record.can_approve = False

            elif record.state == 'in_progress' and current_user.id == record.resignation_type.vp_id.id and record.manager_approved and record.hr_approved and not record.vp_approved:
                print("vp")
                record.can_approve = True
                if record.resignation_type.vp_id.id == record.parent_id.user_id.id:
                    record.vp_approved = True
                    record.can_approve = False
                    print("3 nd")

            elif record.state == 'in_progress' and current_user.id in record.resignation_type.md_ids.ids and record.manager_approved and record.hr_approved and record.vp_approved and not record.md_approved:
                print("md")
                record.can_approve = True
            else:
                record.can_approve = False

    is_admin = fields.Boolean(string='Is Admin', compute='_compute_is_admin', store=False)

    def _compute_is_admin(self):
        for record in self:
            record.is_admin = self.env.user.has_group('custom_resignation.group_admin')

    department_id = fields.Many2one('hr.department', string='Department', compute='_compute_department_id', store=True)

    @api.depends('employee_id')
    def _compute_department_id(self):
        for record in self:
            if record.employee_id:
                record.department_id = record.employee_id.department_id
                record.parent_id = record.employee_id.parent_id
            else:
                record.department_id = False
                record.parent_id = False

    def action_submit(self):
        custody = self.env['custody'].sudo().search(['&', ('employee_id','=',self.employee_id.id),('return_date', '=',None)])
        print(custody)
        if not custody.id:
            print("its not checking")
            self.state = 'submitted'
            parent_user_id = self.parent_id.user_id.id
            self.activity_schedule(
                'custom_timeoff.mail_activity_timeoff',
                user_id=parent_user_id,
            )
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'You Submitted Resignation',
                    'type': 'rainbow_man',
                }
            }
        else:
            raise UserError(_('You should return company property at first'))

    def action_approve(self):
        current_user = self.env.user
        if current_user in self.approvers:
            raise UserError("You have already approved this request.")

        # Manager Approval
        if self.state == 'submitted' and self.parent_id.user_id == current_user and not self.manager_approved:
            self.manager_approved = True
            self.state = 'in_progress'
            self.manager_id = current_user
            # manager activity unlink
            activity_ids = self.activity_ids
            if activity_ids:
                activity_ids.unlink()
            # create  activity for hr
            hr_user_id = self.resignation_type.hr_id.id
            self.activity_schedule(
                'custom_resignation.mail_activity_resignation',
                user_id=hr_user_id,
            )
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'You Approved',
                    'type': 'rainbow_man',
                }
            }

        # HR Approval
        elif self.state == 'in_progress' and current_user.id == self.resignation_type.hr_id.id and not self.hr_approved:
            self.hr_approved = True
            if self.state == 'in_progress' and self.create_uid.id == self.resignation_type.vp_id.id and self.manager_approved:
                print("vp resihned")
                self.state = 'approved'
                self.approved_date = fields.Datetime.now()
                # unlink hr activity
                activity_ids = self.activity_ids
                if activity_ids:
                    activity_ids.unlink()
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'Resignation Approved',
                        'type': 'rainbow_man',
                    }
                }
            # unlink hr activity
            activity_ids = self.activity_ids
            if activity_ids:
                activity_ids.unlink()
            # create  activity for vp
            vp_user_id = self.resignation_type.vp_id.id
            self.activity_schedule(
                'custom_resignation.mail_activity_resignation',
                user_id=vp_user_id,
            )
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'You Approved',
                    'type': 'rainbow_man',
                }
            }

        # VP Approval
        elif self.state == 'in_progress' and current_user.id == self.resignation_type.vp_id.id and not self.vp_approved:
            self.vp_approved = True
            if self.parent_id.user_id.id in self.resignation_type.md_ids.ids:
                self.md_approved = True
                self.state = 'approved'
                self.approved_date = fields.Datetime.now()
                # unlink vp activity
                activity_ids = self.activity_ids
                if activity_ids:
                    activity_ids.unlink()
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': 'Resignation Approved',
                        'type': 'rainbow_man',
                    }
                }
            # unlink vp activity
            print("vp try to unlink activity")

            activity_ids = self.activity_ids
            print("activity",activity_ids)
            if activity_ids:
                activity_ids.unlink()
            # create  activity for md
            md_user_ids = self.resignation_type.md_ids.ids
            for md_id in md_user_ids:
                print(md_id)
                self.activity_schedule(
                    'custom_resignation.mail_activity_resignation',
                    user_id=md_id,
                )
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'You Approved',
                    'type': 'rainbow_man',
                }
            }

        # MD Approval
        elif self.state == 'in_progress' and current_user.id in self.resignation_type.md_ids.ids and not self.md_approved:
            self.md_approved = True
            self.state = 'approved'
            self.approved_date = fields.Datetime.now()
            activity_ids = self.activity_ids
            if activity_ids:
                activity_ids.unlink()
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Resignation Approved',
                    'type': 'rainbow_man',
                }
            }

        self.approvers = [(4, current_user.id)]

    def action_refuse(self):
        for rec in self:
            rec.state = 'refuse'
            # Reset approval tracking
            rec.manager_approved = False
            rec.hr_approved = False
            rec.vp_approved = False
            rec.md_approved = False

    # custody_details = fields.One2many('custody', compute="_compute_custody_details", string="Custody Details")
    #
    # @api.depends('employee_id')
    # def _compute_custody_details(self):
    #     for record in self:
    #         if record.employee_id:
    #             record.custody_details = self.env['custody'].search([
    #                 ('employee_id', '=', record.employee_id.id)
    #             ])
    #         else:
    #             record.custody_details = False









