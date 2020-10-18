from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta , date


class account_payment(models.Model):
    _inherit = 'account.payment'
    
    invoice_lines = fields.One2many('payment.invoice.line', 'payment_id', string="Invoice Line")
    pdc_account = fields.Many2one('account.account',string="PDC Account",copy=False)
    bank_reference = fields.Char(copy=False)
    cheque_reference = fields.Char(copy=False)
    effective_date = fields.Date('Effective Date',
                                 help='Effective date of PDC', copy=False,
                                 default=False)
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Validated'),('reverse', 'Reversed'), ('sent', 'Sent'), ('reconciled', 'Reconciled'), ('cancelled', 'Cancelled')], readonly=True, default='draft', copy=False, string="Status")

    # @api.multi
    def update_invoice_lines(self):
        for inv in self.invoice_lines:
            inv.open_amount = inv.invoice_id.amount_residual
        self.onchange_partner_id()


    @api.onchange('invoice_lines.allocation')
    def _onchange_invoices_lines(self):
        for rec in self:
            if rec.invoice_lines:
                alloc = 0.0
                for inv in rec.invoice_lines:
                    alloc += inv.allocation
                if alloc > rec.amount:
                    raise UserError('The total allocation you assigned is more than payment amount please check your allocation values')
             


    # def write(self,vals):
    #     res = super(account_payment,self).write(vals)
    #     line = []
    #     if self.invoice_lines:
    #         for inv in self.invoices_lines:
    #             line.append(inv.invoice_id.id)
    #         self.invoice_ids.wri[(6,0,line)]
    #     return vals



    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        # Set partner_id domain
        if self.partner_type:
            if not self.env.context.get('default_invoice_ids'):
                self.partner_id = False
            if self.partner_type == 'supplier':

                return {'domain': {'partner_id': [('supplier_rank', '>', 0)]}}
            else:
                return {'domain': {'partner_id': [('customer_rank', '>', 0)]}}

    @api.onchange('partner_id', 'currency_id')
    def onchange_partner_id(self):
        if self.partner_id and self.payment_type != 'transfer':
            vals = {}
            line = [(6, 0, [])]
            invoice_ids = []
            if self.payment_type == 'outbound' and self.partner_type == 'supplier':
                invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                  ('state', '=','posted'),
                                                                  ('type','=', 'in_invoice'),('amount_residual','!=',0.0),
                                                                  ('currency_id', '=', self.currency_id.id)])
            if self.payment_type == 'inbound' and self.partner_type == 'supplier':
                invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                  ('state', '=','posted'),
                                                                  ('type','=', 'in_refund'),('amount_residual','!=',0.0),
                                                                  ('currency_id', '=', self.currency_id.id)])
            if self.payment_type == 'inbound' and self.partner_type == 'customer':
                invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                  ('state', '=','posted'),
                                                                  ('type','=', 'out_invoice'),('amount_residual','!=',0.0),
                                                                  ('currency_id', '=', self.currency_id.id)])
            if self.payment_type == 'outbound' and self.partner_type == 'customer':
                invoice_ids = self.env['account.move'].search([('partner_id', 'in', [self.partner_id.id]),
                                                                  ('state', '=','posted'),
                                                                  ('type','=', 'out_refund'),('amount_residual','!=',0.0),
                                                                  ('currency_id', '=', self.currency_id.id)])

            for inv in invoice_ids[::-1]:
                vals = {
                       'invoice_id': inv.id,
                       }
                line.append((0, 0, vals))
            self.invoice_lines = line
            self.onchnage_amount() 
        
    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if self.payment_type == 'transfer':
            self.invoice_lines = [(6, 0, [])]
            
        if not self.invoice_ids:
            # Set default partner type for the payment type
            if self.payment_type == 'inbound':
                self.partner_type = 'customer'
            elif self.payment_type == 'outbound':
                self.partner_type = 'supplier'
        # Set payment method domain
        res = self._onchange_journal()
        if not res.get('domain', {}):
            res['domain'] = {}
        res['domain']['journal_id'] = self.payment_type == 'inbound' and [('at_least_one_inbound', '=', True)] or [('at_least_one_outbound', '=', True)]
        res['domain']['journal_id'].append(('type', 'in', ('bank', 'cash')))
        return res
    
    @api.onchange('amount')
    def onchnage_amount(self):
        total = 0.0
        remain = self.amount
        for line in self.invoice_lines:
            if line.open_amount <= remain:
                line.allocation = line.open_amount
                remain -= line.allocation
            else:
                line.allocation = remain
                remain -= line.allocation
            total += line.allocation

    # @api.multi
#     def post(self):
#         """"Override to process multiple invoice using single payment."""
#         for rec in self:
#             # code start
# #             total = 0.0
# #             for line in rec.invoice_lines:
# #                 if line.allocation < 0:
# #                     raise ValidationError(_("Negative allocation amount not allowed!"))
# #                 if line.allocation > line.open_amount:
# #                     raise UserError("Allocation amount %s is greater then open amount %s of Invoice." % (line.allocation, line.open_amount))
# #                 total += line.allocation
# #                 if line.open_amount != line.invoice_id.residual:
# #                     raise UserError("Due amount changed.\n Please click 'Update Invoice' button to update amount")
# #                  
# #             if total > rec.amount:
# #                 raise UserError("Total allocation %s is more then payment amount %s" % (total, rec.amount))
#             amt = 0
#             if rec.invoice_lines:
                 
#                 for line in rec.invoice_lines:
#                     amt += line.allocation
#                 # if rec.amount < amt:
#                 #     raise ValidationError(("Payment amount must be greater then or equal to '%s'") %(amt))
#                 # if rec.amount > amt:
#                 #     for line in rec.invoice_lines:
#                 #         line.allocation = line.allocation + (rec.amount - amt)
#                 #         break
#         return  super(account_payment,self).post()



    def _prepare_payment_moves(self):
        ''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
        to the 'create' method.

        Example 1: outbound with write-off:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |   900.0   |
        RECEIVABLE          |           |   1000.0
        WRITE-OFF ACCOUNT   |   100.0   |

        Example 2: internal transfer from BANK to CASH:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |           |   1000.0
        TRANSFER            |   1000.0  |
        CASH                |   1000.0  |
        TRANSFER            |           |   1000.0

        :return: A list of Python dictionary to be passed to env['account.move'].create.
        '''
        all_move_vals = []
        for payment in self:
            
            amount = 0.0
            offwrite = 0.0
            for inv in payment.invoice_lines:
                company_currency = payment.company_id.currency_id
                move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None
                amount += inv.allocation
                # Compute amounts.
                offwrite = inv.invoice_id.amount_residual_signed - inv.allocation
                write_off_amount = payment.payment_difference_handling == 'reconcile' and -offwrite or 0.0
                if payment.payment_type in ('outbound', 'transfer'):
                    counterpart_amount = inv.allocation
                    if payment.pdc_account and payment.payment_method_code == 'pdc':
                        liquidity_line_account = payment.pdc_account
                    else:
                        liquidity_line_account = payment.journal_id.default_debit_account_id
                else:
                    counterpart_amount = -inv.allocation
                    if payment.pdc_account and payment.payment_method_code == 'pdc':
                        liquidity_line_account = payment.pdc_account
                    else:
                        liquidity_line_account = payment.journal_id.default_credit_account_id

                # Manage currency.
                if payment.currency_id == company_currency:
                    # Single-currency.
                    balance = counterpart_amount
                    write_off_balance = write_off_amount
                    counterpart_amount = write_off_amount = 0.0
                    currency_id = False
                else:
                    # Multi-currencies.
                    balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
                    write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
                    currency_id = payment.currency_id.id

                # Manage custom currency on journal for liquidity line.
                if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                    # Custom currency on journal.
                    if payment.journal_id.currency_id == company_currency:
                        # Single-currency
                        liquidity_line_currency_id = False
                    else:
                        liquidity_line_currency_id = payment.journal_id.currency_id.id
                    liquidity_amount = company_currency._convert(
                        balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
                else:
                    # Use the payment currency.
                    liquidity_line_currency_id = currency_id
                    liquidity_amount = counterpart_amount

                # Compute 'name' to be used in receivable/payable line.
                rec_pay_line_name = ''
                if payment.payment_type == 'transfer':
                    rec_pay_line_name = payment.name
                else:
                    if payment.partner_type == 'customer':
                        if payment.payment_type == 'inbound':
                            rec_pay_line_name += _("Customer Payment")
                        elif payment.payment_type == 'outbound':
                            rec_pay_line_name += _("Customer Credit Note")
                    elif payment.partner_type == 'supplier':
                        if payment.payment_type == 'inbound':
                            rec_pay_line_name += _("Vendor Credit Note")
                        elif payment.payment_type == 'outbound':
                            rec_pay_line_name += _("Vendor Payment")
                    if payment.invoice_ids:
                        # rec_pay_line_name += ': %s' % ', '.join(inv.invoice_id.mapped('name'))
                        rec_pay_line_name += ': %s' %(inv.invoice_id.name)
                liquidity_line_name = ''
                # Compute 'name' to be used in liquidity line.
                if payment.payment_type == 'transfer':
                    liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
                else:
                    liquidity_line_name = payment.name
                    liquidity_line_name += ': %s' %(inv.invoice_id.name)

                # ==== 'inbound' / 'outbound' ====

                move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'journal_id': payment.journal_id.id,
                    'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                    'partner_id': payment.partner_id.id,
                    'line_ids': [
                        # Receivable / Payable / Transfer line.
                        (0, 0, {
                            'name': rec_pay_line_name,
                            'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                            'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_account_id.id,
                            'payment_id': payment.id,
                        }),
                        # Liquidity line.
                        (0, 0, {
                            'name': liquidity_line_name,
                            'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': liquidity_line_account.id,
                            'payment_id': payment.id,
                        }),
                    ],
                }
                if write_off_balance :
                    # if offwrite == 0:
                        # Write-off line.
                    move_vals['line_ids'].append((0, 0, {
                        'name': payment.writeoff_label + ' : '+ inv.invoice_id.name,
                        'amount_currency': -write_off_amount,
                        'currency_id': currency_id,
                        'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                        'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': payment.writeoff_account_id.id,
                        'payment_id': payment.id,
                    }))
                        # offwrite = 1


                if move_names:
                    move_vals['name'] = ''
                    move_vals['name'] = move_names[0]
                    move_vals['name'] += ': %s' %(inv.invoice_id.name)

                all_move_vals.append(move_vals)
            if amount:
                payment.amount = amount
            # ==== 'transfer' ====
            if payment.payment_type == 'transfer':
                journal = payment.destination_journal_id

                # Manage custom currency on journal for liquidity line.
                if journal.currency_id and payment.currency_id != journal.currency_id:
                    # Custom currency on journal.
                    liquidity_line_currency_id = journal.currency_id.id
                    transfer_amount = company_currency._convert(balance, journal.currency_id, payment.company_id, payment.payment_date)
                else:
                    # Use the payment currency.
                    liquidity_line_currency_id = currency_id
                    transfer_amount = counterpart_amount

                transfer_move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.destination_journal_id.id,
                    'line_ids': [
                        # Transfer debit line.
                        (0, 0, {
                            'name': payment.name,
                            'amount_currency': -counterpart_amount if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.company_id.transfer_account_id.id,
                            'payment_id': payment.id,
                        }),
                        # Liquidity credit line.
                        (0, 0, {
                            'name': _('Transfer from %s') % payment.journal_id.name,
                            'amount_currency': transfer_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance > 0.0 and balance or 0.0,
                            'credit': balance < 0.0 and -balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_journal_id.default_credit_account_id.id,
                            'payment_id': payment.id,
                        }),
                    ],
                }

                if move_names and len(move_names) == 2:
                    transfer_move_vals['name'] = move_names[1]

                all_move_vals.append(transfer_move_vals)
        return all_move_vals



    def post(self):
        """ Create the journal items for the payment and update the payment's state to 'posted'.
            A journal entry is created containing an item in the source liquidity account (selected journal's default_debit or default_credit)
            and another in the destination reconcilable account (see _compute_destination_account_id).
            If invoice_ids is not empty, there will be one reconcilable move line per invoice to reconcile with.
            If the payment is a transfer, a second journal entry is created in the destination journal to receive money from the transfer account.
        """
        AccountMove = self.env['account.move'].with_context(default_type='entry')
        for rec in self:

            if rec.state != 'draft':
                raise UserError(_("Only a draft payment can be posted."))

            if any(inv.state != 'posted' for inv in rec.invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))

            # keep the name in case of a payment reset to draft
            if not rec.name:
                # Use the right sequence to set the name
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.payment_date)
                if not rec.name and rec.payment_type != 'transfer':
                    raise UserError(_("You have to define a sequence for %s in your company.") % (sequence_code,))

            moves = AccountMove.create(rec._prepare_payment_moves())
            moves.filtered(lambda move: move.journal_id.post_at != 'bank_rec').post()

            # Update the state / move before performing any reconciliation.
            move_name = self._get_move_name_transfer_separator().join(moves.mapped('name'))
            rec.write({'state': 'posted', 'move_name': move_name})

            if rec.payment_type in ('inbound', 'outbound'):
                # ==== 'inbound' / 'outbound' ====
                i = 0
                if rec.invoice_ids:
                    for inv in rec.invoice_lines:
                        (moves[i] + inv.invoice_id).line_ids \
                            .filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id and not (line.account_id == line.payment_id.writeoff_account_id and line.name == line.payment_id.writeoff_label))\
                            .reconcile()
                        i = i + 1
                # if rec.invoice_lines:
                #     for inv in rec.invoice_lines:
                #         (moves[0] + inv.invoice_id).line_ids \
                #         .filtered(lambda line: not line.reconciled and line.account_id == rec.destination_account_id and not (line.account_id == line.payment_id.writeoff_account_id and line.name == line.payment_id.writeoff_label))\
                #         .reconcile()

            elif rec.payment_type == 'transfer':
                # ==== 'transfer' ====
                moves.mapped('line_ids')\
                    .filtered(lambda line: line.account_id == rec.company_id.transfer_account_id)\
                    .reconcile()

        return True


    def _prepare_default_reversal(self, move):
        return {
            'ref': _('Reversal of: %s') % (move.name),
            'date': date.today(),
            'invoice_date': move.is_invoice(include_receipts=True) and move.date or False,
            'journal_id': move.journal_id.id,
            'invoice_payment_term_id': None,
            'auto_post': True if date.today() > fields.Date.context_today(self) else False,
            'invoice_user_id': move.invoice_user_id.id,
        }

    def reverse_moves(self):
        # moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        moves = self.mapped('move_line_ids.move_id')
        moves = moves.filtered(lambda move: move.state == 'posted')
        # moves.with_context(force_delete=True).unlink()
        # self.write({'state': 'draft', 'invoice_ids': False})
        # Create default values.
        
        # for move in moves:
        refund_method = (len(moves) > 1 or moves.type == 'entry') and 'cancel' or 'refund'
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

        # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': date.today()})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)
                for res in new_moves:
                    for rec in res.line_ids:
                        rec.write({'payment_id':self.id})

            moves_to_redirect |= new_moves

        self.write({'state': 'reverse'})

            # # Create action.
            # action = {
            #     'name': _('Reverse Moves'),
            #     'type': 'ir.actions.act_window',
            #     'res_model': 'account.move',
            # }
            # if len(moves_to_redirect) == 1:
            #     action.update({
            #         'view_mode': 'form',
            #         'res_id': moves_to_redirect.id,
            #     })
            # else:
            #     action.update({
            #         'view_mode': 'tree,form',
            #         'domain': [('id', 'in', moves_to_redirect.ids)],
            #     })
            # return action
            

    # def _prepare_payment_moves(self):
    #     ''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
    #     to the 'create' method.

    #     Example 1: outbound with write-off:

    #     Account             | Debit     | Credit
    #     ---------------------------------------------------------
    #     BANK                |   900.0   |
    #     RECEIVABLE          |           |   1000.0
    #     WRITE-OFF ACCOUNT   |   100.0   |

    #     Example 2: internal transfer from BANK to CASH:

    #     Account             | Debit     | Credit
    #     ---------------------------------------------------------
    #     BANK                |           |   1000.0
    #     TRANSFER            |   1000.0  |
    #     CASH                |   1000.0  |
    #     TRANSFER            |           |   1000.0

    #     :return: A list of Python dictionary to be passed to env['account.move'].create.
    #     '''
    #     all_move_vals = []
    #     for payment in self:
    #         company_currency = payment.company_id.currency_id
    #         move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

    #         # Compute amounts.
    #         write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
    #         if payment.payment_type in ('outbound', 'transfer'):
    #             counterpart_amount = payment.amount
    #             if payment.pdc_account and payment.payment_method_code == 'pdc':
    #                 liquidity_line_account = payment.pdc_account
    #             else:
    #                 liquidity_line_account = payment.journal_id.default_debit_account_id
    #         else:
    #             counterpart_amount = -payment.amount
    #             if payment.pdc_account and payment.payment_method_code == 'pdc':
    #                 liquidity_line_account = payment.pdc_account
    #             else:
    #                 liquidity_line_account = payment.journal_id.default_credit_account_id

    #         # Manage currency.
    #         if payment.currency_id == company_currency:
    #             # Single-currency.
    #             balance = counterpart_amount
    #             write_off_balance = write_off_amount
    #             counterpart_amount = write_off_amount = 0.0
    #             currency_id = False
    #         else:
    #             # Multi-currencies.
    #             balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
    #             write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
    #             currency_id = payment.currency_id.id

    #         # Manage custom currency on journal for liquidity line.
    #         if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
    #             # Custom currency on journal.
    #             if payment.journal_id.currency_id == company_currency:
    #                 # Single-currency
    #                 liquidity_line_currency_id = False
    #             else:
    #                 liquidity_line_currency_id = payment.journal_id.currency_id.id
    #             liquidity_amount = company_currency._convert(
    #                 balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
    #         else:
    #             # Use the payment currency.
    #             liquidity_line_currency_id = currency_id
    #             liquidity_amount = counterpart_amount

    #         # Compute 'name' to be used in receivable/payable line.
    #         rec_pay_line_name = ''
    #         if payment.payment_type == 'transfer':
    #             rec_pay_line_name = payment.name
    #         else:
    #             if payment.partner_type == 'customer':
    #                 if payment.payment_type == 'inbound':
    #                     rec_pay_line_name += _("Customer Payment")
    #                 elif payment.payment_type == 'outbound':
    #                     rec_pay_line_name += _("Customer Credit Note")
    #             elif payment.partner_type == 'supplier':
    #                 if payment.payment_type == 'inbound':
    #                     rec_pay_line_name += _("Vendor Credit Note")
    #                 elif payment.payment_type == 'outbound':
    #                     rec_pay_line_name += _("Vendor Payment")
    #             if payment.invoice_ids:
    #                 rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))

    #         # Compute 'name' to be used in liquidity line.
    #         if payment.payment_type == 'transfer':
    #             liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
    #         else:
    #             liquidity_line_name = payment.name

    #         # ==== 'inbound' / 'outbound' ====

    #         move_vals = {
    #             'date': payment.payment_date,
    #             'ref': payment.communication,
    #             'journal_id': payment.journal_id.id,
    #             'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
    #             'partner_id': payment.partner_id.id,
    #             'line_ids': [
    #                 # Receivable / Payable / Transfer line.
    #                 (0, 0, {
    #                     'name': rec_pay_line_name,
    #                     'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
    #                     'currency_id': currency_id,
    #                     'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
    #                     'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
    #                     'date_maturity': payment.payment_date,
    #                     'partner_id': payment.partner_id.commercial_partner_id.id,
    #                     'account_id': payment.destination_account_id.id,
    #                     'payment_id': payment.id,
    #                 }),
    #                 # Liquidity line.
    #                 (0, 0, {
    #                     'name': liquidity_line_name,
    #                     'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
    #                     'currency_id': liquidity_line_currency_id,
    #                     'debit': balance < 0.0 and -balance or 0.0,
    #                     'credit': balance > 0.0 and balance or 0.0,
    #                     'date_maturity': payment.payment_date,
    #                     'partner_id': payment.partner_id.commercial_partner_id.id,
    #                     'account_id': liquidity_line_account.id,
    #                     'payment_id': payment.id,
    #                 }),
    #             ],
    #         }
    #         if write_off_balance:
    #             # Write-off line.
    #             move_vals['line_ids'].append((0, 0, {
    #                 'name': payment.writeoff_label,
    #                 'amount_currency': -write_off_amount,
    #                 'currency_id': currency_id,
    #                 'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
    #                 'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
    #                 'date_maturity': payment.payment_date,
    #                 'partner_id': payment.partner_id.commercial_partner_id.id,
    #                 'account_id': payment.writeoff_account_id.id,
    #                 'payment_id': payment.id,
    #             }))

    #         if move_names:
    #             move_vals['name'] = move_names[0]

    #         all_move_vals.append(move_vals)

    #         # ==== 'transfer' ====
    #         if payment.payment_type == 'transfer':
    #             journal = payment.destination_journal_id

    #             # Manage custom currency on journal for liquidity line.
    #             if journal.currency_id and payment.currency_id != journal.currency_id:
    #                 # Custom currency on journal.
    #                 liquidity_line_currency_id = journal.currency_id.id
    #                 transfer_amount = company_currency._convert(balance, journal.currency_id, payment.company_id, payment.payment_date)
    #             else:
    #                 # Use the payment currency.
    #                 liquidity_line_currency_id = currency_id
    #                 transfer_amount = counterpart_amount

    #             transfer_move_vals = {
    #                 'date': payment.payment_date,
    #                 'ref': payment.communication,
    #                 'partner_id': payment.partner_id.id,
    #                 'journal_id': payment.destination_journal_id.id,
    #                 'line_ids': [
    #                     # Transfer debit line.
    #                     (0, 0, {
    #                         'name': payment.name,
    #                         'amount_currency': -counterpart_amount if currency_id else 0.0,
    #                         'currency_id': currency_id,
    #                         'debit': balance < 0.0 and -balance or 0.0,
    #                         'credit': balance > 0.0 and balance or 0.0,
    #                         'date_maturity': payment.payment_date,
    #                         'partner_id': payment.partner_id.commercial_partner_id.id,
    #                         'account_id': payment.company_id.transfer_account_id.id,
    #                         'payment_id': payment.id,
    #                     }),
    #                     # Liquidity credit line.
    #                     (0, 0, {
    #                         'name': _('Transfer from %s') % payment.journal_id.name,
    #                         'amount_currency': transfer_amount if liquidity_line_currency_id else 0.0,
    #                         'currency_id': liquidity_line_currency_id,
    #                         'debit': balance > 0.0 and balance or 0.0,
    #                         'credit': balance < 0.0 and -balance or 0.0,
    #                         'date_maturity': payment.payment_date,
    #                         'partner_id': payment.partner_id.commercial_partner_id.id,
    #                         'account_id': payment.destination_journal_id.default_credit_account_id.id,
    #                         'payment_id': payment.id,
    #                     }),
    #                 ],
    #             }

    #             if move_names and len(move_names) == 2:
    #                 transfer_move_vals['name'] = move_names[1]

    #             all_move_vals.append(transfer_move_vals)
    #     return all_move_vals


    # # @api.multi
    # def _create_payment_entry(self, amount):
    #     """ Create a journal entry related to a payment"""
    #     # If group data
    #     if self.invoice_ids and self.invoice_lines:
    #         aml_obj = self.env['account.move.line'].\
    #             with_context(check_move_validity=False)
    #         invoice_currency = False
    #         if self.invoice_ids and\
    #                 all([x.currency_id == self.invoice_ids[0].currency_id
    #                      for x in self.invoice_ids]):
    #             # If all the invoices selected share the same currency,
    #             # record the paiement in that currency too
    #             invoice_currency = self.invoice_ids[0].currency_id
    #         move = self.env['account.move'].create(self._get_move_vals())
    #         p_id = str(self.partner_id.id)
    #         for inv in self.invoice_ids:
    #             amt = 0
    #             if self.partner_type == 'customer':
    #                 for line in self.invoice_lines:
    #                     if line.invoice_id.id == inv.id:
    #                         if inv.type == 'out_invoice':
    #                             amt = -(line.allocation)
    #                         else:
    #                             amt = line.allocation
    #             else:
    #                 for line in self.invoice_lines:
    #                     if line.invoice_id.id == inv.id:
    #                         if inv.type == 'in_invoice':
    #                             amt = line.allocation
    #                         else:
    #                             amt = -(line.allocation)

    #             debit, credit, amount_currency, currency_id =\
    #                 aml_obj.with_context(date=self.payment_date).\
    #                 _compute_amount_fields(amt, self.currency_id,
    #                                       self.company_id.currency_id,
    #                                       )
    #             # Write line corresponding to invoice payment
    #             counterpart_aml_dict =\
    #                 self._get_shared_move_line_vals(debit,
    #                                                 credit, amount_currency,
    #                                                 move.id, False)
    #             counterpart_aml_dict.update(
    #                 self._get_counterpart_move_line_vals(inv))
    #             counterpart_aml_dict.update({'currency_id': currency_id})
    #             counterpart_aml = aml_obj.create(counterpart_aml_dict)
    #             # Reconcile with the invoices and write off
    #             if self.partner_type == 'customer':
    #                 handling = 'open'
    #                 for line in self.invoice_lines:
    #                     if line.invoice_id.id == inv.id:
    #                         payment_difference = line.open_amount - line.allocation
    #                 writeoff_account_id = self.journal_id and self.journal_id.id or False
    #                 if handling == 'reconcile' and\
    #                         payment_difference:
    #                     writeoff_line =\
    #                         self._get_shared_move_line_vals(0, 0, 0, move.id,
    #                                                         False)
    #                     debit_wo, credit_wo, amount_currency_wo, currency_id =\
    #                         aml_obj.with_context(date=self.payment_date).\
    #                         _compute_amount_fields(
    #                             payment_difference,
    #                             self.currency_id,
    #                             self.company_id.currency_id,
    #                             )
    #                     writeoff_line['name'] = _('Counterpart')
    #                     writeoff_line['account_id'] = writeoff_account_id
    #                     writeoff_line['debit'] = debit_wo
    #                     writeoff_line['credit'] = credit_wo
    #                     writeoff_line['amount_currency'] = amount_currency_wo
    #                     writeoff_line['currency_id'] = currency_id
    #                     writeoff_line = aml_obj.create(writeoff_line)
    #                     if counterpart_aml['debit']:
    #                         counterpart_aml['debit'] += credit_wo - debit_wo
    #                     if counterpart_aml['credit']:
    #                         counterpart_aml['credit'] += debit_wo - credit_wo
    #                     counterpart_aml['amount_currency'] -=\
    #                         amount_currency_wo
    #             inv.register_payment(counterpart_aml)
    #             # Write counterpart lines
    #             if not self.currency_id != self.company_id.currency_id:
    #                 amount_currency = 0
    #             liquidity_aml_dict =\
    #                 self._get_shared_move_line_vals(credit, debit,
    #                                                 -amount_currency, move.id,
    #                                                 False)
    #             liquidity_aml_dict.update(
    #                 self._get_liquidity_move_line_vals(-amount))
    #             aml_obj.create(liquidity_aml_dict)
    #         move.post()
    #         return move

    #     return super(account_payment, self)._create_payment_entry(amount)
    
    @api.model
    def create(self,vals):
        res = super(account_payment,self).create(vals)
        if vals.get('invoice_lines'):
            res.invoice_ids = res.invoice_lines.mapped('invoice_id')
            alloc = 0.0
            for inv in res.invoice_lines:
                alloc += inv.allocation
            if alloc > res.amount:
                raise UserError('The total allocation you assigned is more than payment amount please check your allocation values')
        return res
    
    # @api.multi
    def write(self,vals):
        res = super(account_payment,self).write(vals)
        if vals.get('invoice_lines'):
            self.invoice_ids = self.invoice_lines.mapped('invoice_id')
            alloc = 0.0
            for inv in self.invoice_lines:
                alloc += inv.allocation
            if alloc > self.amount:
                raise UserError('The total allocation you assigned is more than payment amount please check your allocation values')
        
        return res

class PaymentInvoiceLine(models.Model):
    _name = 'payment.invoice.line'


    sequence = fields.Integer('Sequence')
    payment_id = fields.Many2one('account.payment', string="Payment")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    invoice = fields.Char(related='invoice_id.name', string="Invoice Number")
    account_id = fields.Many2one('account.account', string="Account")
    date = fields.Date(string='Invoice Date', compute='_get_invoice_data', store=True)
    due_date = fields.Date(string='Due Date', compute='_get_invoice_data', store=True)
    total_amount = fields.Float(string='Total Amount', compute='_get_invoice_data', store=True)
    open_amount = fields.Float(string='Due Amount', compute='_get_invoice_data', store=True)
    allocation = fields.Float(string='Allocation Amount')
    
    # @api.multi
    @api.depends('invoice_id')
    def _get_invoice_data(self):
        for data in self:
            invoice_id = data.invoice_id
            data.date = invoice_id.invoice_date
            data.due_date = invoice_id.invoice_date_due
            data.total_amount = invoice_id.amount_total 
            data.open_amount = invoice_id.amount_residual
