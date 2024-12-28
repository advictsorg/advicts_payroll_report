from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
import json


class ReportWizard(models.TransientModel):
    _name = "ad.payroll.report"
    _description = "Advance Payroll Report"

    start_date = fields.Date('Start Date', required=True,
                             default=lambda self: self.env.context.get('default_start_date'))
    end_date = fields.Date('End Date', required=True, default=lambda self: self.env.context.get('default_end_date'))
    department_id = fields.Many2one('hr.department', 'Department')
    employee_id = fields.Many2one('hr.employee', 'Employee')

    def _get_report_data(self):
        if self.start_date > self.end_date:
            raise ValidationError(_("Start Date cannot be after End Date."))

        # Prepare domain for filtering
        domain = [
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date)
        ]

        # Add optional department filter
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))

        # Add optional employee filter
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))

        # Retrieve payroll reports
        payroll_reports = self.env['hr.payroll.report'].search(domain)

        # Prepare report data
        report_data = []
        for report in payroll_reports:
            # Handle case where no analytic distribution exists
            analytic_distribution = {}
            try:
                # Try to parse existing analytic distribution
                if isinstance(report.employee_id.contract_id.analytic, dict):
                    analytic_distribution = report.employee_id.contract_id.analytic
                elif report.employee_id.contract_id.analytic:
                    analytic_distribution = json.loads(report.employee_id.contract_id.analytic or '{}')
            except Exception:
                # If parsing fails, use an empty dict
                analytic_distribution = {}

            # If no analytic distribution, create a default entry with 100%
            if not analytic_distribution:
                analytic_distribution = {'0': 100}

            # Create entries for each analytic distribution (or default)
            for analytic_id, percentage in analytic_distribution.items():
                # Default project name if no analytic project found
                project_names = 'No Project'

                # Try to fetch project names
                try:
                    project_ids = [int(pid) for pid in analytic_id.split(',') if pid.strip()]
                    if project_ids:
                        projects = self.env['account.analytic.account'].sudo().browse(project_ids)
                        project_names = ', '.join(projects.mapped('name') or ['No Project'])
                except Exception:
                    pass
                specific_rules = {
                    'Food Allowance': 'FD',
                    'Transport Allowance': 'TRANS',
                    'Card Allowance': 'CARD',
                    'Deductions': 'DED',
                    'Salary Advance Paid': 'SAP',
                    'Accommodation': 'ACC',
                    'Gross Salary': 'GROSS',
                    'Total Allowance': 'ALLOW',
                }
                # Create entry for each analytic distribution
                report_entry = {
                    'Employee': report.employee_id.name,
                    'Department': report.department_id.name or '',
                    'Job Position': report.job_id.name or '',
                    'Start Date': report.date_from,
                    'End Date': report.date_to,
                    'Work Days': report.count_work or 0,
                    'Work Hours': report.count_work_hours or 0,
                    'Days of Paid Time Off': report.count_leave or 0,
                    'Days of Unpaid Time Off': report.count_leave_unpaid or 0,
                    'Days of Unforeseen Absence': report.count_unforeseen_absence or 0,
                    'wage': {
                        'Basic Wage': (report.basic_wage or 0) * (percentage / 100),
                        'Gross Wage': (report.gross_wage or 0) * (percentage / 100),
                        'Net Wage': (report.net_wage or 0) * (percentage / 100)
                    },
                    'Basic Wage for Time Off': (report.leave_basic_wage or 0) * (percentage / 100),
                    'Number of Days': report.number_of_days or 0,
                    'Number of Hours': report.number_of_hours or 0,
                    'Work Type': dict(report._fields['work_type'].selection).get(report.work_type, ''),
                    'analytic': project_names,
                    'analytic_percentage': percentage
                }
                for name, code in specific_rules.items():
                    salary_rule = self.env['hr.salary.rule'].sudo().search([('code', '=', code)], limit=1)
                    if salary_rule:
                        field_name = salary_rule._get_report_field_name()
                        report_entry[name] = (getattr(report, field_name, 0) or 0) * (percentage / 100)

                report_data.append(report_entry)
                # Add dynamic salary rule fields
                salary_rules = self.env['hr.salary.rule'].sudo().search([('appears_on_payroll_report', '=', True)])
                for rule in salary_rules:
                    field_name = rule._get_report_field_name()
                    report_entry[rule.name] = (getattr(report, field_name, 0) or 0) * (percentage / 100)

                report_data.append(report_entry)

        return {
            'data': report_data,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'total_employees': len(set(entry['Employee'] for entry in report_data)),
            'total_net_wage': sum(entry['wage']['Net Wage'] for entry in report_data),
        }

    def action_print_pdf_report(self):
        report_data = self._get_report_data()
        return self.env.ref('advicts_payroll_report.ad_payroll_report_action').report_action(self, data=report_data)

    def action_print_xlsx_report(self):
        report_data = self._get_report_data()
        return self.env.ref('advicts_payroll_report.ad_payroll_report_action_xlsx').report_action(self,
                                                                                                  data=report_data)


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    def open_payroll_report_wizard(self):
        """
        Opens the payroll report wizard with pre-filled dates based on the batch's start and end dates.
        """
        return {
            'name': 'Payroll Report Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'ad.payroll.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_start_date': self.date_start,
                'default_end_date': self.date_end,
            },
        }
