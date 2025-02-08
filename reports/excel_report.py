from odoo import models
import base64
import io
from PIL import Image


class PayrollReportXlsx(models.AbstractModel):
    _name = 'report.advicts_payroll_report.ad_payroll_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def _insert_image(self, field, sheet, row, col, sign=False):
        if field:
            product_image = io.BytesIO(base64.b64decode(field))
            img = Image.open(product_image)
            image_width, image_height = img.size
            target = 70
            xscale = ((target / image_width) * 100) / 100
            yscale = ((target / image_height) * 100) / 100
            if not sign:
                sheet.insert_image(f'{col}{row}', "image.png",
                                   {'image_data': product_image, "x_scale": 0.15, "y_scale": 0.30,
                                    'object_position': 1,
                                    "x_offset": 10,
                                    "y_offset": 7})
            else:
                sheet.insert_image(f'{col}{row}', "sign.png",
                                   {'image_data': product_image, "x_scale": 0.20, "y_scale": 0.40,
                                    'object_position': 1,
                                    "x_offset": 10,
                                    "y_offset": 7})

    def generate_xlsx_report(self, workbook, data, report):
        # Styles
        header_style = workbook.add_format({
            'bold': True,
            'bg_color': '#d3ad66',
            'border': 1,
            'valign': 'vcenter',
            'align': 'center'
        })

        data_style = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
        })

        total_style = workbook.add_format({
            'bold': True,
            'border': 1,
            'valign': 'vcenter',
            'align': 'right',
            'num_format': '#,##0.00'
        })

        percentage_style = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
            'num_format': '0.00%'
        })

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
        self._insert_image(data['logo'], sheet, 1, 'A')
        sheet.merge_range("A8:D8", title, header_style)
        sheet.write(8, 0, 'Report Period:', header_style)
        sheet.merge_range("B9:D9", f"{data['start_date']} to {data['end_date']}", data_style)
        sheet.write(8, 5, 'Total Net Wage:', header_style)
        sheet.write(8, 6, data['total_net_wage'], currency_style)
        # Column Headers
        headers = [
            '#', 'Employee', 'Job Title', 'Department',
            'Projects', '%', 'Work Days', 'Work Hours', 'Basic Wage', 'Paid Wage',
            'Food Allowance', 'Transport Allowance', 'Card Allowance', 'Accommodation',
            'Allowance', 'Gross Wage',
            'Deductions', 'Salary Advance Paid', 'Net Wage',
        ]

        # Write headers
        for col, header in enumerate(headers):
            sheet.write(10, col, header, header_style)

        # Write Data
        # Traffic violation
        row = 11
        sorted_data = sorted(data['data'], key=lambda x: (x['Code'] or '').lower())
        data['data'] = sorted_data
        for line in sorted_data:
            sheet.write(row, 0, line['Code'] if line['Code'] else 0, data_style)
            sheet.write(row, 1, line['Employee'], data_style)
            sheet.write(row, 2, line['Job Position'], data_style)
            sheet.write(row, 3, line['Department'], data_style)
            sheet.write(row, 4, line['analytic'], data_style)
            sheet.write(row, 5, round(line['analytic_percentage']), data_style)
            sheet.write(row, 6, round(line['Work Days']), data_style)
            sheet.write(row, 7, round(line['Work Hours'],2), data_style)
            sheet.write(row, 8, line.get('Basic Wage', 0), currency_style)
            sheet.write(row, 9, line.get('Paid Wage', 0), currency_style)
            sheet.write(row, 10, line.get('Food Allowance', 0), currency_style)
            sheet.write(row, 11, line.get('Transport Allowance', 0), currency_style)
            sheet.write(row, 12, line.get('Card Allowance', 0), currency_style)
            sheet.write(row, 13, line.get('Accommodation', 0), currency_style)
            sheet.write(row, 14, line.get('Allowance', 0), currency_style)
            sheet.write(row, 15, line['wage']['Gross Wage'], currency_style)
            sheet.write(row, 16, line.get('Deductions', 0), currency_style)
            sheet.write(row, 17, line.get('Salary Advance Paid', 0), currency_style)
            sheet.write(row, 18, line['wage']['Net Wage'], currency_style)
            row += 1

        # Adjust column widths
        sheet.set_column('A:B', 20)
        sheet.set_column('C:D', 15)
        sheet.set_column('E:F', 20)
        sheet.set_column('G:I', 15)
        sheet.set_column('J:K', 10)
        sheet.set_column('L:L', 15)

        # Department Distribution with Totals and Percentages
        department_data_row = row + 2
        sheet.write(department_data_row, 0, 'Net Wage by Department', header_style)

        # Column headers for department breakdown
        sheet.write(department_data_row, 0, 'Department', header_style)
        sheet.write(department_data_row, 1, 'Net Wage', header_style)
        sheet.write(department_data_row, 2, 'Percentage', header_style)

        department_wages = {}
        total_department_wages = 0

        # Calculate total wages first
        for line in data['data']:
            department = line['Department'] or 'Undefined'
            wage = line['wage']['Net Wage analytic']
            department_wages[department] = department_wages.get(department, 0) + wage
            total_department_wages += wage

        # Write department data with percentages
        department_row = department_data_row + 1
        for department, wage in department_wages.items():
            percentage = wage / total_department_wages if total_department_wages else 0
            sheet.write(department_row, 0, department, data_style)
            sheet.write(department_row, 1, wage, currency_style)
            sheet.write(department_row, 2, percentage, percentage_style)
            department_row += 1

        # Write total
        sheet.write(department_row, 0, 'Total', header_style)
        sheet.write(department_row, 1, total_department_wages, total_style)
        sheet.write(department_row, 2, 1, percentage_style)

        # Department chart
        chart_department = workbook.add_chart({'type': 'pie'})
        chart_department.add_series({
            'categories': [sheet.name, department_data_row + 1, 0, department_row - 1, 0],
            'values': [sheet.name, department_data_row + 1, 1, department_row - 1, 1],
            'data_labels': {'percentage': True},
        })
        sheet.insert_chart(f'E{department_row - 8}', chart_department, {'x_scale': 0.75, 'y_scale': 0.75})

        # Analytic Project Distribution with Totals and Percentages
        analytic_data_row = department_row + 10
        sheet.write(analytic_data_row, 0, 'Net Wage by Analytic Project', header_style)

        # Column headers for analytic breakdown
        sheet.write(analytic_data_row, 0, 'Analytic Project', header_style)
        sheet.write(analytic_data_row, 1, 'Net Wage', header_style)
        sheet.write(analytic_data_row, 2, 'Percentage', header_style)

        analytic_wages = {}
        total_analytic_wages = 0

        # Calculate total wages first
        for line in data['data']:
            analytic = line['analytic'] or 'No Project'
            wage = line['wage']['Net Wage analytic']
            analytic_wages[analytic] = analytic_wages.get(analytic, 0) + wage
            total_analytic_wages += wage

        # Write analytic data with percentages
        analytic_row = analytic_data_row + 1
        for analytic, wage in analytic_wages.items():
            percentage = wage / total_analytic_wages if total_analytic_wages else 0
            sheet.write(analytic_row, 0, analytic, data_style)
            sheet.write(analytic_row, 1, wage, currency_style)
            sheet.write(analytic_row, 2, percentage, percentage_style)
            analytic_row += 1

        # Write total
        sheet.write(analytic_row, 0, 'Total', header_style)
        sheet.write(analytic_row, 1, total_analytic_wages, total_style)
        sheet.write(analytic_row, 2, 1, percentage_style)

        # Analytic chart
        chart_analytic = workbook.add_chart({'type': 'pie'})
        chart_analytic.add_series({
            'categories': [sheet.name, analytic_data_row + 1, 0, analytic_row - 1, 0],
            'values': [sheet.name, analytic_data_row + 1, 1, analytic_row - 1, 1],
            'data_labels': {'percentage': True},
        })
        sheet.insert_chart(f'E{analytic_row - 5}', chart_analytic, {'x_scale': 0.75, 'y_scale': 0.75})

        return workbook
