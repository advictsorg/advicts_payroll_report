from odoo import models


class PayrollReportXlsx(models.AbstractModel):
    _name = 'report.advicts_payroll_report.ad_payroll_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, report):
        # Styles
        header_style = workbook.add_format({
            'bold': True,
            'bg_color': '#c9c5c5',
            'border': 1,
            'valign': 'vcenter',
            'align': 'center'
        })

        data_style = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
        })

        # Number format for currency
        currency_style = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'right',
            'num_format': '#,##0.00'
        })

        # Create worksheet
        title = 'Advance Payroll Report'
        sheet = workbook.add_worksheet(title[:31])

        # Report Header
        sheet.merge_range("A1:L1", title, header_style)

        # Report Period
        sheet.write(2, 0, 'Report Period:', header_style)
        sheet.merge_range("B3:D3", f"{data['start_date']} to {data['end_date']}", data_style)

        sheet.write(4, 0, 'Total Employees:', header_style)
        sheet.write(4, 1, data['total_employees'], data_style)

        sheet.write(4, 5, 'Total Net Wage:', header_style)
        sheet.write(4, 6, data['total_net_wage'], currency_style)

        # Column Headers
        headers = [
            'Employee', 'Department', 'Job Position', 'Period',
            'Analytic Project', 'Analytic %', 'Basic Wage',
            'Gross Wage', 'Net Wage', 'Work Days', 'Work Hours',
            'Work Type', 'Food Allowance', 'Transport Allowance', 'Card Allowance', 'Deductions', 'Salary Advance Paid',
            'Accommodation', 'Gross Salary', 'Total Allowance'
        ]

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(6, col, header, header_style)

        # Write Data
        row = 7
        for line in data['data']:
            sheet.write(row, 0, line['Employee'], data_style)
            sheet.write(row, 1, line['Department'], data_style)
            sheet.write(row, 2, line['Job Position'], data_style)
            sheet.write(row, 3, f"{line['Start Date']} - {line['End Date']}", data_style)
            sheet.write(row, 4, line['analytic'], data_style)
            sheet.write(row, 5, line['analytic_percentage'], data_style)
            sheet.write(row, 6, line['wage']['Basic Wage'], currency_style)
            sheet.write(row, 7, line['wage']['Gross Wage'], currency_style)
            sheet.write(row, 8, line['wage']['Net Wage'], currency_style)
            sheet.write(row, 9, line['Work Days'], data_style)
            sheet.write(row, 10, line['Work Hours'], data_style)
            sheet.write(row, 11, line['Work Type'], data_style)
            sheet.write(row, 12, line.get('Food Allowance', 0), data_style)
            sheet.write(row, 13, line.get('Transport Allowance', 0), data_style)
            sheet.write(row, 14, line.get('Card Allowance', 0), data_style)
            sheet.write(row, 15, line.get('Deductions', 0), data_style)
            sheet.write(row, 16, line.get('Salary Advance Paid', 0), data_style)
            sheet.write(row, 17, line.get('Accommodation', 0), data_style)
            sheet.write(row, 18, line.get('Gross Salary', 0), data_style)
            sheet.write(row, 19, line.get('Total Allowance', 0), data_style)
            row += 1

        # Adjust column widths
        sheet.set_column('A:B', 20)  # Employee, Department
        sheet.set_column('C:D', 15)  # Job Position, Period
        sheet.set_column('E:F', 20)  # Analytic Project, Percentage
        sheet.set_column('G:I', 15)  # Wages
        sheet.set_column('J:K', 10)  # Work Days, Work Hours
        sheet.set_column('L:L', 15)  # Work Type

        # Adding Pie Chart for Department Distribution
        chart_department = workbook.add_chart({'type': 'pie'})
        department_data_row = row + 2
        sheet.write(department_data_row, 0, 'Net Wage by Department', header_style)
        department_wages = {}
        for line in data['data']:
            department = line['Department'] or 'Undefined'
            department_wages[department] = department_wages.get(department, 0) + line['wage']['Net Wage']

        department_row = department_data_row + 1
        for department, wage in department_wages.items():
            sheet.write(department_row, 0, department, data_style)
            sheet.write(department_row, 1, wage, currency_style)
            department_row += 1

        chart_department.add_series({
            'categories': [sheet.name, department_data_row + 1, 0, department_row - 1, 0],
            'values': [sheet.name, department_data_row + 1, 1, department_row - 1, 1],
            'data_labels': {'percentage': True},
        })
        sheet.insert_chart(f'D{department_row - 3}', chart_department,
                           {'x_scale': 0.75, 'y_scale': 0.75})  # Smaller chart

        # Adding Pie Chart for Analytic Project Distribution
        chart_analytic = workbook.add_chart({'type': 'pie'})
        analytic_data_row = department_row + 10  # Leave space for the first chart
        sheet.write(analytic_data_row, 0, 'Net Wage by Analytic Project', header_style)
        analytic_wages = {}
        for line in data['data']:
            analytic = line['analytic'] or 'No Project'
            analytic_wages[analytic] = analytic_wages.get(analytic, 0) + line['wage']['Net Wage']

        analytic_row = analytic_data_row + 1
        for analytic, wage in analytic_wages.items():
            sheet.write(analytic_row, 0, analytic, data_style)
            sheet.write(analytic_row, 1, wage, currency_style)
            analytic_row += 1

        chart_analytic.add_series({
            'categories': [sheet.name, analytic_data_row + 1, 0, analytic_row - 1, 0],
            'values': [sheet.name, analytic_data_row + 1, 1, analytic_row - 1, 1],
            'data_labels': {'percentage': True},
        })
        sheet.insert_chart(f'D{analytic_row -3}', chart_analytic, {'x_scale': 0.75, 'y_scale': 0.75})  # Smaller chart

        return workbook
