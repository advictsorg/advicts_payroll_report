# -*- coding: utf-8 -*-
{
    'name': "Advicts Advance Payroll Report",
    'summary': """ Report to Calculate Payroll Report With Date (from - to) """,
    'description': """ Report to Calculate Payroll Report With Date (from - to) """,
    'author': "GhaithAhmed@Advicts",
    'website': "https://advicts.com",
    'category': 'Accounting',
    'version': '1.0',
    'depends': ['base', 'advicts_contract_analytic_distribution', 'hr_payroll', 'report_xlsx'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/report_wizard.xml',
        'views/views.xml',
        'reports/reports.xml',
        'reports/report_template.xml',
    ],
}
