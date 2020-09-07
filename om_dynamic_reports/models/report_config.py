# -*- coding: utf-8 -*-
# License: Odoo Proprietary License v1.0

import io
import time
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models


try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter


class DynamicReportConfig(models.TransientModel):
    _name = 'dynamic.report.config'

    def get_xlsx_report(self, data, response):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        cell_format = workbook.add_format({'font_size': '12px', 'bold': True})

        txt = workbook.add_format({'font_size': '10px'})

        x = 0
        y = 0

        if data['filters']:
            filters = data['filters']
            if filters.get('date_from'):
                sheet.merge_range(y, x, y, x + 2, filters['date_from'],
                                  cell_format)
                x += 2
            if filters.get('date_to'):
                sheet.merge_range(y, x, y, x + 2, filters['date_to'],
                                  cell_format)

            x = 0
            if filters.get('date_from') or filters.get('date_to'):
                y += 1

            if filters.get('journal_ids'):
                sheet.merge_range(y, x, y, x + 4, filters['journal_ids'],
                                  cell_format)
                y += 1
            x = 0

            for f_val in filters:
                if f_val in ['date_from',
                             'date_to', 'journal_ids'] or not filters[f_val]:
                    continue
                sheet.merge_range(y, x, y, x + 2, filters[f_val],
                                  cell_format)
                y += 1

        y += 1
        col_style = cell_format
        col_width = {}
        new_vals = []
        for line in data.get('lines'):
            temp = {}
            for l_col in line:
                temp[int(l_col)] = line[l_col]
            new_vals.append(temp)

        for line in new_vals:
            x = 0
            for col in line:
                col_val = str(line[col]['value'])
                colspan = 0
                if line[col].get('colspan'):
                    colspan = int(line[col]['colspan'])

                col_level = 0
                if line[col].get('level'):
                    col_level = int(line[col]['level'])
                new_col_style = None
                if x == 0 and col_level > 0:
                    new_col_style = workbook.add_format({
                        'font_size': '10px'})

                    if data['report_name'] not in ['journals_audit',
                                                   'aged_partner',
                                                   'trial_balance',
                                                   'partner_ledger',
                                                   'general_ledger',
                                                   'tax_report']:
                        col_level = math.ceil(col_level / 2)
                    new_col_style.set_indent(col_level)

                if not new_col_style:
                    new_col_style = col_style

                sheet.write(y, x, col_val, new_col_style)

                x += colspan

                if col in col_width:
                    if col_width[col] < colspan:
                        col_width[col] = colspan
                else:
                    col_width[col] = 1

            col_style = txt
            sheet.set_row(y, 25)
            y += 1

        if data['report_name'] in ['journals_audit', 'aged_partner',
                                   'partner_ledger', 'general_ledger',
                                   'tax_report']:
            min_col_width = 15
        else:
            min_col_width = 30

        for col in col_width:
            width_val = col_width[col] * min_col_width
            if width_val > min_col_width:
                width_val = min_col_width
            sheet.set_column(int(col), int(col), width_val)
        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()

    @api.model
    def check_report(self, data):
        currency_data = {
            'symbol': '',
            'position': 'after',
            'decimal_places': 2,
            'company_id': [self.env.user.company_id.id,
                           self.env.user.company_id.name]
        }

        report_lines = []
        if self.env.user.company_id and self.env.user.company_id.currency_id:
            company_id = self.env.user.company_id
            currency_data[
                'symbol'] = company_id.currency_id.symbol
            currency_data[
                'position'] = company_id.currency_id.position
            currency_data[
                'decimal_places'] = company_id.currency_id.decimal_places

        if data['report_type'] == 'config':
            ReportObj = self.env[
                'report.accounting_pdf_reports.report_financial']
            report_lines = ReportObj.get_account_lines(data)
        else:
            if data['account_report_id'][0] == 'journals_audit':
                report_lines = {}

                j_ids = []
                for i in data.get('journal_ids'):
                    j_ids.append(int(i))
                data['journal_ids'] = j_ids
                data['used_context']['journal_ids'] = j_ids

                for journal in j_ids:
                    report_lines[journal] = []
            elif data['account_report_id'][0] == 'partner_ledger':
                ReportObj = self.env[
                    'report.accounting_pdf_reports.report_partnerledger']

                res = ReportObj._get_partner_ids({'form': data})

                partner_ids = res[1]
                data = res[0]

                report_lines = ReportObj._dynamic_report_lines(data,
                                                               partner_ids)
            elif data['account_report_id'][0] == 'general_ledger':
                ReportObj = self.env[
                    'report.accounting_pdf_reports.report_general_ledger']
                report_lines = ReportObj.get_ledger_data(data)
            elif data['account_report_id'][0] == 'trial_balance':
                ReportObj = self.env[
                    'report.accounting_pdf_reports.report_trialbalance']

                display_account = data.get('display_account')
                accounts = self.env['account.account'].search([])
                report_lines = ReportObj.with_context(
                    data.get('used_context')
                )._get_accounts_dynamic(accounts, display_account)
            elif data['account_report_id'][0] == 'aged_partner':
                res = {}
                ReportObj = self.env[
                    'report.accounting_pdf_reports.report_agedpartnerbalance']

                # build the interval lines
                start = datetime.strptime(data.get('date_from'),
                                          '%Y-%m-%d')
                period_length = int(data['period_length'])

                for i in range(5)[::-1]:
                    stop = start - relativedelta(days=period_length - 1)
                    res[str(i)] = {
                        'name': (i != 0 and (str(
                            (5 - (i + 1)) * period_length) + '-' + str(
                            (5 - i) * period_length)) or (
                                         '+' + str(4 * period_length))),
                        'stop': start.strftime('%Y-%m-%d'),
                        'start': (i != 0 and stop.strftime(
                            '%Y-%m-%d') or False),
                    }
                    start = stop - relativedelta(days=1)
                data.update(res)

                total = []

                target_move = data.get('target_move', 'all')
                date_from = data.get('date_from',
                                     time.strftime('%Y-%m-%d'))

                if data['result_selection'] == 'customer':
                    account_type = ['receivable']
                elif data['result_selection'] == 'supplier':
                    account_type = ['payable']
                else:
                    account_type = ['payable', 'receivable']

                movelines, total, dummy = ReportObj._get_partner_move_lines(
                    account_type, date_from, target_move,
                    int(data['period_length']))

                report_lines = ReportObj.dynamic_report_lines(data,
                                                              movelines,
                                                              total)
            elif data['account_report_id'][0] == 'tax_report':
                ReportObj = self.env[
                    'report.accounting_pdf_reports.report_tax']

                lines = ReportObj.get_lines(data)

                report_lines = ReportObj.process_lines(lines)

        return [report_lines, currency_data]


class ReportFinancialExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_journal_items(self, accounts):
        """ compute the journal entries
        """
        res = {}
        # for account in accounts:
        #     res[account.id] = dict.fromkeys(mapping, 0.0)
        if accounts:
            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get()
            tables = tables.replace('"', '') if tables else "account_move_line"
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            request = ("SELECT account_id,account_move_line.id as id, " +
                       "account_move_line.name,account_move_line.ref,"
                       " debit,credit," +
                       "debit-credit as balance" +
                       " FROM " + tables +
                       " WHERE account_id IN %s " +
                       filters +
                       " GROUP BY account_id,account_move_line.id," +
                       "account_move_line.name,debit,"
                       "credit,account_move_line.ref")
            params = (tuple(accounts._ids),) + tuple(where_params)
            self.env.cr.execute(request, params)
            for row in self.env.cr.dictfetchall():
                res[row['id']] = row
        return res

    def _compute_report_balance(self, reports):
        """returns a dictionary with key=the ID of a record
         and value=the credit, debit and balance amount
           computed for this record. If the record is of type :
               'accounts' : it's the sum of the linked accounts
               'account_type' : it's the sum of leaf accoutns with
                such an account_type
               'account_report' : it's the amount of the related report
               'sum' : it's the sum of the children of this record
                (aka a 'view' record)"""
        res = {}
        fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                res[report.id]['account'] = self._compute_account_balance(
                    report.account_ids)
                # res[report.id]['journal_items'] = self._compute_journal_items(
                #     report.account_ids)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account'].search(
                    [('user_type_id', 'in', report.account_type_ids.ids)])
                res[report.id]['account'] = self._compute_account_balance(
                    accounts)
                # res[report.id]['journal_items'] = self._compute_journal_items(
                #     accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._compute_report_balance(report.children_ids)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def _compute_report_balance(self, reports):
        """returns a dictionary with key=the ID of a record and
        value=the credit, debit and balance amount
           computed for this record. If the record is of type :
               'accounts' : it's the sum of the linked accounts
               'account_type' : it's the sum of leaf accoutns with
                such an account_type
               'account_report' : it's the amount of the related report
               'sum' : it's the sum of the children of this record
               (aka a 'view' record)"""
        res = {}
        fields = ['credit', 'debit', 'balance']
        for report in reports:
            if report.id in res:
                continue
            res[report.id] = dict((fn, 0.0) for fn in fields)
            if report.type == 'accounts':
                # it's the sum of the linked accounts
                res[report.id]['account'] = self._compute_account_balance(
                    report.account_ids)
                # res[report.id]['journal_items'] = self._compute_journal_items(
                #     report.account_ids)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_type':
                # it's the sum the leaf accounts with such an account type
                accounts = self.env['account.account'].search(
                    [('user_type_id', 'in', report.account_type_ids.ids)])
                res[report.id]['account'] = self._compute_account_balance(
                    accounts)
                # res[report.id]['journal_items'] = self._compute_journal_items(
                #     accounts)
                for value in res[report.id]['account'].values():
                    for field in fields:
                        res[report.id][field] += value.get(field)
            elif report.type == 'account_report' and report.account_report_id:
                # it's the amount of the linked report
                res2 = self._compute_report_balance(report.account_report_id)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
            elif report.type == 'sum':
                # it's the sum of the children of this account.report
                res2 = self._compute_report_balance(report.children_ids)
                for key, value in res2.items():
                    for field in fields:
                        res[report.id][field] += value[field]
        return res

    def get_account_lines(self, data):
        lines = []
        account_report = self.env['account.financial.report'].search(
            [('id', '=', data['account_report_id'][0])])
        child_reports = account_report._get_children_by_order()
        res = self.with_context(
            data.get('used_context'))._compute_report_balance(child_reports)
        if data['enable_filter']:
            comparison_res = self.with_context(
                data.get('comparison_context'))._compute_report_balance(
                child_reports)
            for report_id, value in comparison_res.items():
                res[report_id]['comp_bal'] = value['balance']
                report_acc = res[report_id].get('account')
                if report_acc:
                    for account_id, val in comparison_res[report_id].get(
                            'account').items():
                        report_acc[account_id]['comp_bal'] = val['balance']
        for report in child_reports:
            if account_report.id == report.id:
                active_id = 'root_line'
                parent_id = "false"
            else:
                parent_id = 'root_line'
                active_id = 'report_' + str(report.id)

            vals = {
                'name': report.name,
                'balance': res[report.id]['balance'] * float(report.sign),
                'type': 'report',
                'level': bool(
                    report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type or False,
                # used to underline the financial report balances
                'parent': parent_id,
                'active_id': active_id
            }
            if data['debit_credit']:
                vals['debit'] = res[report.id]['debit']
                vals['credit'] = res[report.id]['credit']

            if data['enable_filter']:
                vals['balance_cmp'] = res[report.id]['comp_bal'] * float(
                    report.sign)

            lines.append(vals)
            if report.display_detail == 'no_detail':
                # the rest of the loop is used to display the details of
                # the financial report, so it's not needed here.
                continue

            if res[report.id].get('account'):
                sub_lines = []
                for account_id, value in res[report.id]['account'].items():
                    # if there are accounts to display, we add them
                    # to the lines with a level equals to their level in
                    # the COA + 1 (to avoid having them with a too low
                    # level that would conflicts with the level of data
                    # financial reports for Assets, liabilities...)
                    flag = False
                    account = self.env['account.account'].browse(account_id)
                    vals = {
                        'name': account.code + ' ' + account.name,
                        'balance': value['balance'] * float(
                            report.sign) or 0.0,
                        'type': 'account',
                        'level': report.display_detail == 'detail_with_hierarchy' and 4,
                        'account_type': account.internal_type,
                        'parent': 'report_' + str(report.id),
                        'active_id': 'account_' + str(account_id),
                        'has_child_lines': True
                    }
                    if data['debit_credit']:
                        vals['debit'] = value['debit']
                        vals['credit'] = value['credit']
                        if not account.company_id.currency_id.is_zero(
                                vals['debit']
                        ) or not account.company_id.currency_id.is_zero(
                            vals['credit']):
                            flag = True
                    if not account.company_id.currency_id.is_zero(
                            vals['balance']):
                        flag = True
                    if data['enable_filter']:
                        vals['balance_cmp'] = value['comp_bal'] * float(
                            report.sign)
                        if not account.company_id.currency_id.is_zero(
                                vals['balance_cmp']):
                            flag = True
                    if flag:
                        sub_lines.append(vals)
                lines += sorted(sub_lines,
                                key=lambda sub_line: sub_line['name'])

        for rec in lines:
            if rec['type'] == 'journal_item':
                rec['name'] = rec['label']
                del rec['label']
        return lines

    @api.model
    def get_journal_data(self, account_id, level, debit_credit):
        accounts = self.env['account.account'].browse(account_id)
        return self.fetch_journal_items(
            account_id, self._compute_journal_items(accounts), level,
            debit_credit)

    def fetch_journal_items(self, account_id, journal_items, level,
                            debit_credit):
        result = []
        for rec in journal_items.values():
            if account_id == rec['account_id']:
                temp = {
                    'name': rec['name'] if rec['name'] else (
                            rec['ref'] or '/'),
                    'level': level + 1,
                    'balance': rec['balance'],
                    'type': 'journal_item',
                    'line_id': rec['id'],
                    'active_id': rec['id'],
                    'parent': 'account_' + str(account_id)
                }
                if debit_credit:
                    temp['debit'] = rec['debit']
                    temp['credit'] = rec['credit']
                result.append(temp)
        return result


class ReportTaxExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_tax'

    def process_lines(self, lines):
        report_lines = [{
            'name': 'Sale',
            'net': 'Net',
            'tax': 'Tax',
            'level': 1,
            'parent': 0,
            'id': 1,
            'active_id': 1
        }]

        i = 1
        for line in lines['sale']:
            i += 1
            report_lines.append({
                'name': line.get('name'),
                'net': line.get('net'),
                'tax': line.get('tax'),
                'level': 2,
                'parent': 1,
                'id': i,
                'active_id': i
            })

        i += 1
        report_lines.append({
            'name': 'Purchase',
            'net': ' ',
            'tax': ' ',
            'level': 1,
            'parent': 0,
            'active_id': i,
            'id': i
        })

        parent = i
        for line in lines['purchase']:
            i += 1
            report_lines.append({
                'name': line.get('name'),
                'net': line.get('net'),
                'tax': line.get('tax'),
                'level': 2,
                'parent': parent,
                'active_id': i,
                'id': i
            })

        return report_lines


class ReportAgedPartnerBalanceExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_agedpartnerbalance'

    def dynamic_report_lines(self, data, movelines, total):
        report_lines = []

        r_id = 1
        report_lines.append({
            'name': 'Partners',
            'direction': 'Not due',
            'l4': data['4']['name'],
            'l3': data['3']['name'],
            'l2': data['2']['name'],
            'l1': data['1']['name'],
            'l0': data['0']['name'],
            'total': 'Total',
            'line_type': 'font_bold',
            'id': r_id,
            'parent': 0
        })
        p_id = r_id
        if movelines:
            r_id += 1
            report_lines.append({
                'name': 'Account Total',
                'direction': total[6],
                'l4': total[4],
                'l3': total[3],
                'l2': total[2],
                'l1': total[1],
                'l0': total[0],
                'total': total[5],
                'line_type': 'font_bold',
                'id': r_id,
                'parent': 0
            })

            for rec in movelines:
                r_id += 1
                report_lines.append({
                    'name': rec['name'],
                    'direction': rec['direction'],
                    'l4': rec['4'],
                    'l3': rec['3'],
                    'l2': rec['2'],
                    'l1': rec['1'],
                    'l0': rec['0'],
                    'total': rec['total'],
                    'id': r_id,
                    'parent': 0
                })

        return report_lines


class ReportTrialBalanceExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_trialbalance'

    @api.model
    def get_accounts_child(self, account_id):
        account_res = []
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        journal_items = (
                "SELECT account_move_line.id AS res_id, account_id, " +
                "debit, credit, (debit - credit) AS" +
                " balance, account_move_line.ref, "
                "account_move_line.name as name " +
                " FROM " + tables +
                " WHERE account_id IN %s " + filters +
                " GROUP BY account_id, account_move_line.id," +
                " account_move_line.name, account_move_line.debit," +
                " account_move_line.credit, account_move_line.ref")
        params = (tuple([account_id]),) + tuple(where_params)
        self.env.cr.execute(journal_items, params)
        journal_items = {}
        for rec in self.env.cr.dictfetchall():
            # rec['level'] = 2
            if rec['account_id'] in journal_items:
                journal_items[rec['account_id']].append(rec)
            else:
                journal_items[rec['account_id']] = [rec]

        if account_id in journal_items:
            account = self.env['account.account'].browse(int(account_id))
            for j_line in journal_items[account_id]:
                new_val = {
                    'level': 2,
                    'code': j_line['ref'] if j_line['ref'] else (
                            j_line['name'] or '/'),
                    'name': account.name,
                    'debit': j_line['debit'],
                    'credit': j_line['credit'],
                    'balance': j_line['balance'],
                    'res_id': j_line['res_id'],
                    'line_type': 'journal_item'
                }
                account_res.append(new_val)

        return account_res

    def _get_accounts_dynamic(self, accounts, display_account):
        """ compute the balance, debit and credit for the provided accounts
            :Arguments:
                `accounts`: list of accounts record,
                `display_account`: it's used to display either all accounts or
                 those accounts which balance is > 0
            :Returns a list of dictionary of Accounts with following key and
                value.
                `name`: Account name,
                `code`: Account code,
                `credit`: total amount of credit,
                `debit`: total amount of debit,
                `balance`: total amount of balance,
        """

        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env[
            'account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)

        params = (tuple(accounts.ids),) + tuple(where_params)
        request = ("SELECT account_id AS id, SUM(debit) AS debit, " +
                   "SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS" +
                   " balance FROM " + tables +
                   " WHERE account_id IN %s " + filters +
                   " GROUP BY account_id")

        self.env.cr.execute(request, params)
        for row in self.env.cr.dictfetchall():
            account_result[row.pop('id')] = row

        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = (account.currency_id and account.currency_id or
                        account.company_id.currency_id)
            res['code'] = account.code
            res['name'] = account.name
            res['active_id'] = account.id
            res['has_child_lines'] = True
            res['level'] = 1
            # res['res_id'] = account.id
            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (not currency.is_zero(
                        res['debit']) or not currency.is_zero(res['credit'])):
                account_res.append(res)
        return account_res


class ReportPartnerLedgerExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_partnerledger'

    def _get_partner_ref(self, partner_id):
        res = []
        if partner_id.ref:
            res.append(str(partner_id.ref))
        if partner_id.name:
            res.append(partner_id.name)
        return "-".join(res)

    def _dynamic_report_lines(self, data, partner_ids):
        result = []

        for p_id in partner_ids:
            result.append({
                'line_type': 'section_heading',
                'date': self._get_partner_ref(p_id),
                'debit': self._sum_partner(data, p_id, 'debit'),
                'credit': self._sum_partner(data, p_id, 'credit'),
                'balance': self._sum_partner(data, p_id, 'debit - credit'),
            })
            result += self._lines(data, p_id)
        return result

    def _get_partner_ids(self, data=None):
        data['computed'] = {}

        obj_partner = self.env['res.partner']
        query_get_data = self.env['account.move.line'].with_context(
            data['form'].get('used_context', {}))._query_get()
        data['computed']['move_state'] = ['draft', 'posted']
        if data['form'].get('target_move', 'all') == 'posted':
            data['computed']['move_state'] = ['posted']
        result_selection = data['form'].get('result_selection', 'customer')
        if result_selection == 'supplier':
            data['computed']['ACCOUNT_TYPE'] = ['payable']
        elif result_selection == 'customer':
            data['computed']['ACCOUNT_TYPE'] = ['receivable']
        else:
            data['computed']['ACCOUNT_TYPE'] = ['payable', 'receivable']

        self.env.cr.execute("""
        SELECT a.id
        FROM account_account a
        WHERE a.internal_type IN %s
        AND NOT a.deprecated""",
                            (tuple(data['computed']['ACCOUNT_TYPE']),))
        data['computed']['account_ids'] = [a for (a,) in
                                           self.env.cr.fetchall()]
        params = [tuple(data['computed']['move_state']),
                  tuple(data['computed']['account_ids'])] + query_get_data[
                     2]
        reconcile_clause = "" if data['form'][
            'reconciled'
        ] else ' AND "account_move_line".full_reconcile_id IS NULL '
        query = """
        SELECT DISTINCT "account_move_line".partner_id
        FROM """ + query_get_data[0] + """, account_account AS account,
         account_move AS am
        WHERE "account_move_line".partner_id IS NOT NULL
            AND "account_move_line".account_id = account.id
            AND am.id = "account_move_line".move_id
            AND am.state IN %s
            AND "account_move_line".account_id IN %s
            AND NOT account.deprecated
            AND """ + query_get_data[1] + reconcile_clause
        self.env.cr.execute(query, tuple(params))
        partner_ids = [res['partner_id'] for res in
                       self.env.cr.dictfetchall()]
        partners = obj_partner.browse(partner_ids)
        partners = sorted(partners,
                          key=lambda x: (x.ref or '', x.name or ''))

        return [data, partners]


class ReportGenLedgerExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_general_ledger'

    @api.model
    def get_account_data(self, data, account_id):
        account = self.env['account.account'].browse(int(account_id))
        init_balance = data.get('init_balance')
        sortby = data.get('sortby')
        display_account = data.get('display_account')
        return self.with_context(
            data.get('used_context', {})
        )._get_account_move_entry(account,
                                  init_balance,
                                  sortby,
                                  display_account)

    def get_ledger_data(self, data):
        report_lines = []
        init_balance = data.get('initial_balance', True)
        sortby = data.get('sortby', 'sort_date')
        display_account = data.get('display_account', 'movement')

        accounts = self.env['account.account'].search([])

        cr = self.env.cr
        MoveLine = self.env['account.move.line']
        move_lines = {x: [] for x in accounts.ids}

        # Prepare initial sql query and Get the initial move lines
        if init_balance:
            init_tables, init_where_clause, init_where_params = MoveLine.with_context(
                date_from=self.env.context.get('date_from'),
                date_to=False, initial_bal=True)._query_get()
            init_wheres = [""]
            if init_where_clause.strip():
                init_wheres.append(init_where_clause.strip())
            init_filters = " AND ".join(init_wheres)
            filters = init_filters.replace(
                'account_move_line__move_id', 'm').replace(
                'account_move_line', 'l')
            sql = ("""SELECT 0 AS lid, l.account_id AS account_id, '' AS ldate,
                '' AS lcode, 0.0 AS amount_currency, '' AS lref, 
                'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS 
                debit, COALESCE(SUM(l.credit),0.0) AS credit, 
                COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as 
                balance, '' AS lpartner_id,\
                '' AS move_name, '' AS mmove_id, '' AS currency_code,\
                NULL AS currency_id,\
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,\
                '' AS partner_name\
                FROM account_move_line l\
                LEFT JOIN account_move m ON (l.move_id=m.id)\
                LEFT JOIN res_currency c ON (l.currency_id=c.id)\
                LEFT JOIN res_partner p ON (l.partner_id=p.id)\
                JOIN account_journal j ON (l.journal_id=j.id)\
                WHERE l.account_id IN %s""" + filters +
                   ' GROUP BY l.account_id')
            params = (tuple(accounts.ids),) + tuple(init_where_params)
            cr.execute(sql, params)
            for row in cr.dictfetchall():
                move_lines[row.pop('account_id')].append(row)

        sql_sort = 'l.date, l.move_id'
        if sortby == 'sort_journal_partner':
            sql_sort = 'j.code, p.name, l.move_id'

        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = MoveLine._query_get()
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        filters = filters.replace('account_move_line__move_id',
                                  'm').replace('account_move_line',
                                               'l')

        # Get move lines base on sql query and Calculate the total
        # balance of move lines
        sql = ('''SELECT l.id AS lid, l.account_id AS account_id, l.date AS 
            ldate, j.code AS lcode, l.currency_id, l.amount_currency, l.ref AS
             lref, l.name AS lname, COALESCE(l.debit,0) AS debit, 
             COALESCE(l.credit,0) AS credit, COALESCE(SUM(l.debit),0) - 
             COALESCE(SUM(l.credit), 0) AS balance,\
            m.name AS move_name, c.symbol AS currency_code, p.name AS 
            partner_name FROM account_move_line l\
            JOIN account_move m ON (l.move_id=m.id)\
            LEFT JOIN res_currency c ON (l.currency_id=c.id)\
            LEFT JOIN res_partner p ON (l.partner_id=p.id)\
            JOIN account_journal j ON (l.journal_id=j.id)\
            JOIN account_account acc ON (l.account_id = acc.id) \
            WHERE l.account_id IN %s ''' + filters + ''' GROUP BY l.id, 
            l.account_id, l.date, j.code, l.currency_id, l.amount_currency, 
            l.ref, l.name, m.name, c.symbol, p.name ORDER BY ''' + sql_sort)
        params = (tuple(accounts.ids),) + tuple(where_params)
        cr.execute(sql, params)

        for row in cr.dictfetchall():
            balance = 0
            for line in move_lines.get(row['account_id']):
                balance += line['debit'] - line['credit']
            row['balance'] += balance
            move_lines[row.pop('account_id')].append(row)
        for account in accounts:
            currency = (account.currency_id and account.currency_id or
                        account.company_id.currency_id)
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            res['code'] = account.code
            res['active_id'] = account.id
            res['name'] = account.name
            res['has_child_lines'] = True
            res['move_lines'] = []
            # res['move_lines'] = move_lines[account.id]
            for line in move_lines[account.id]:
                res['debit'] += line['debit']
                res['credit'] += line['credit']
                res['balance'] = line['balance']
            if display_account == 'all':
                report_lines.append(res)
            if display_account == 'movement' and move_lines[account.id]:
                report_lines.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                report_lines.append(res)
        return report_lines


class ReportJournalExt(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_journal'

    def get_total(self, data, journal_id):
        return {
            'line_type': 'font_bold',
            'move_id': 'Total',
            'date': "",
            'account_id': "",
            'partner_id': '',
            'name': '',
            'debit': self._sum_debit(data, journal_id),
            'credit': self._sum_credit(data, journal_id),
        }

    def get_tax_declaration(self, data, journal_id):
        result = list()

        result.append({
            'line_type': 'font_bold',
            'move_id': 'Tax Declaration',
            'date': "",
            'account_id': "",
            'partner_id': '',
            'name': '',
            'debit': "",
            'credit': "",
        })

        result.append({
            'line_type': 'font_bold',
            'move_id': 'name',
            'date': "",
            'account_id': "Base Amount",
            'partner_id': 'Tax Amount',
            'name': '',
            'debit': "",
            'credit': "",
        })

        taxes = self._get_taxes(data, journal_id)
        for tax in taxes:
            result.append({
                'line_type': 'font_bold',
                'move_id': tax.name,
                'date': "",
                'account_id': taxes[tax]['base_amount'],
                'partner_id': taxes[tax]['tax_amount'],
                'name': '',
                'debit': "",
                'credit': "",
            })

        return result

    @api.model
    def lines_dynamic(self, target_move, journal_id, sort_selection, data):
        journal_ids = [journal_id]

        move_state = ['draft', 'posted']
        if target_move == 'posted':
            move_state = ['posted']

        query_get_clause = self._get_query_get_clause(data)
        params = [tuple(move_state), tuple(journal_ids)] + \
                 query_get_clause[2]
        query = ('SELECT "account_move_line".id FROM ' + query_get_clause[
            0] +
                 ', account_move am, account_account acc WHERE ' +
                 '"account_move_line".account_id = acc.id AND ' +
                 '"account_move_line".move_id=am.id AND am.state IN %s AND ' +
                 '"account_move_line".journal_id IN %s AND ' +
                 query_get_clause[1] + ' ORDER BY ')
        if sort_selection == 'date':
            query += '"account_move_line".date'
        else:
            query += 'am.name'
        query += ', "account_move_line".move_id, acc.code'

        self.env.cr.execute(query, tuple(params))
        ids = (x[0] for x in self.env.cr.fetchall())

        result = []
        target_fields = ['id', 'move_id', 'date', 'account_id',
                         'partner_id',
                         'name', 'debit', 'credit', 'currency_id']

        for rec in self.env['account.move.line'].browse(ids):
            temp = {}
            for f_key in target_fields:
                if f_key in ['move_id', 'partner_id']:
                    temp[f_key] = rec[f_key].name if rec[f_key] else ""
                elif f_key == 'currency_id':
                    temp[f_key] = rec[f_key].symbol if rec[f_key] else ""
                elif f_key == 'id':
                    temp['res_id'] = rec[f_key]
                elif f_key == 'account_id':
                    temp[f_key] = rec[f_key].code if rec[f_key] else ""
                else:
                    temp[f_key] = rec[f_key]
            result += [temp]

        journal_obj = self.env['account.journal'].sudo().browse(int(journal_id))
        result += [self.get_total(data, journal_obj)]
        result += self.get_tax_declaration(data, journal_obj)
        return result
