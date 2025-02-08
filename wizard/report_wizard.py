from odoo import models, fields, _, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)


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
            raise ValidationError(_('Start Date cannot be after End Date.'))

        # Prepare domain for filtering
        domain = [
            ('date_from', '>=', self.start_date),
            ('date_to', '<=', self.end_date),
        ]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.employee_id:
            domain.append(('employee_id', '=', self.employee_id.id))

        # Read grouped payroll reports
        payroll_reports = self.env['hr.payroll.report'].sudo().read_group(
            domain,
            ['employee_id', 'date_from', 'date_to', 'count_work', 'count_work_hours',
             'count_leave', 'count_leave_unpaid', 'count_unforeseen_absence', 'basic_wage', 'gross_wage',
             'net_wage', 'leave_basic_wage', 'number_of_days', 'number_of_hours', 'work_type'],
            ['employee_id']
        )
        # _logger.info("-----------------------------------------------------")

        report_data = []
        for report in payroll_reports:
            # _logger.info(f"{report}")
            employee = self.env['hr.employee'].sudo().browse(report['employee_id'][0])
            # hr_pa = self.env['hr.payroll.report'].search(
            #     [('employee_id', '=', employee.id), ('date_from', '>=', self.start_date),
            #      ('date_to', '<=', self.end_date)], limit=1)
            hr_payslip = self.env['hr.payslip'].sudo().search(
                [('employee_id', '=', employee.id), ('date_from', '>=', self.start_date),
                 ('date_to', '<=', self.end_date)], limit=1)
            hr_payslip = self.env['hr.payslip'].sudo().search(
                [('employee_id', '=', employee.id), ('date_from', '>=', self.start_date),
                 ('date_to', '<=', self.end_date)], limit=1)

            try:
                analytic = employee.contract_id.analytic or '{}'
                analytic_distribution = json.loads(analytic) if isinstance(analytic, str) else analytic
            except Exception:
                analytic_distribution = {}
            if not analytic_distribution:
                analytic_distribution = {'0': 100}

            for analytic_id, percentage in analytic_distribution.items():
                project_names = 'No Project'
                try:
                    # Split and clean the analytic_id string
                    project_ids = [int(pid) for pid in analytic_id.split(',') if pid.strip()]

                    # Filter analytic accounts with the name 'projects'
                    projects = self.env['account.analytic.account'].sudo().search([
                        ('id', 'in', project_ids),
                        ('plan_id.name', '=', 'Projects')
                    ])

                    # Join the names of the filtered projects, or fallback to 'No Project'
                    project_names = ', '.join(projects.mapped('name') or ['No Project'])
                except Exception as e:
                    _logger.error(f"Error processing analytic distribution: {str(e)}")
                    pass
                report_entry = {
                    'Employee': report['employee_id'][1],
                    'Code': employee.x_studio_employee_code,
                    'Department': report['department_id'][1] if report.get(
                        'department_id') else employee.department_id.display_name,
                    'Job Position': report['job_id'][1] if report.get('job_id') else employee.job_id.name,
                    'Start Date': report.get('date_from') if report.get(
                        'date_from') else self.start_date,
                    'End Date': report.get('date_to') if report.get('date_to') else self.end_date,
                    'Work Days': report.get('count_work') or 0,
                    'Work Hours': report.get('count_work_hours') or 0,
                    'Days of Paid Time Off': report.get('count_leave') or 0,
                    'Days of Unpaid Time Off': report.get('count_leave_unpaid') or 0,
                    'Days of Unforeseen Absence': report['count_unforeseen_absence'] or 0,
                    'wage': {
                        'Basic Wage': (report['gross_wage'] or 0),
                        'Gross Wage': (report['gross_wage'] or 0),
                        'Net Wage': (report['net_wage'] or 0),
                        'Net Wage analytic': (report['net_wage'] or 0) * (percentage / 100)
                    },
                    'Basic Wage for Time Off': (report['leave_basic_wage'] or 0),
                    'Number of Days': report['number_of_days'] or 0,
                    'Number of Hours': report['number_of_hours'] or 0,
                    'Work Type': '',
                    'analytic': project_names,
                    'analytic_percentage': percentage
                }
                specific_rules = {
                    'Basic Wage': 'Basic Salary',
                    'Paid Wage': 'Paid Salary',
                    'Food Allowance': 'Food',
                    'Transport Allowance': 'Transport',
                    'Card Allowance': 'Card',
                    'Deductions': 'Deductions',
                    'Child Support': 'Child Support',
                    'Salary Advance Paid': 'Salary Advance Paid',
                    'Accommodation': 'Accommodation',
                    'Gross Salary': 'Gross',
                    # 'Total Allowance': 'Total Allowance',
                    'Allowance': 'Allowance',
                }
                for name, code in specific_rules.items():
                    line = sum(self.env['hr.payslip.line'].sudo().search(
                        [('slip_id.employee_id', '=', employee.id), ('slip_id.date_from', '>=', self.start_date),
                         ('slip_id.date_to', '<=', self.end_date), ('name', '=', code),
                         ('slip_id.state', 'not in', ['draft', 'cancel'])],
                        limit=1).mapped('total'))
                    report_entry[name] = line

                # salary_rules = self.env['hr.salary.rule'].sudo().search([('appears_on_payroll_report', '=', True)])
                # for rule in salary_rules:
                #     field_name = rule._get_report_field_name()
                #     report_entry[rule.name] = (getattr(employee, field_name, 0) or 0)
                #
                report_data.append(report_entry)
        # _logger.info("-----------------------------------------------------")
        sign = False
        ceo = self.env['res.users'].sudo().browse(29)
        if ceo:
            sign = ceo.sign_signature
        sorted_data = sorted(report_data, key=lambda x: (x['Code'] or '').lower())
        return {
            'data': sorted_data,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'logo': self.env.company.logo,
            'total_employees': len(set(entry['Employee'] for entry in report_data)),
            'total_net_wage': sum(entry['wage']['Net Wage analytic'] for entry in report_data),
            'sign': sign
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
