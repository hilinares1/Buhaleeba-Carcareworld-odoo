odoo.define('om_dynamic_reports.DynamicReports', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var Qweb = core.qweb;
    var framework = require('web.framework');

    var rpc = require("web.rpc");

	var balance_sheet_fields = {
		'name': 'Name',
		'debit': 'Debit',
		'credit': 'Credit',
		'balance': 'Balance',
	};
    var journals_audit_fields = {
        'move_id': 'Move',
        'date': "Date",
        'account_id': "Account",
        'partner_id': 'Partner',
        'name': 'Label',
        'debit': 'Debit',
        'credit': 'Credit',
    };

    var p_ledger_fields = {
        'date': 'Date',
        'code': 'JRNL',
        'a_code': 'Account',
        'displayed_name': 'Ref',
        'debit': 'Debit',
        'credit': 'Credit',
        'balance': 'Balance',
        'progress': 'Balance',
    };
    var g_ledger_fields = {
        'ldate': 'Date',
        'lcode': 'JRNL',
        'partner_name': 'Partner',
        'lref': 'Ref',
        'move_name': 'Move',
        'lname': 'Entry Label',
        'debit': 'Debit',
        'credit': 'Credit',
        'balance': 'Balance',
    };

    var trial_balance_fields = {
        'code': 'Code',
        'name': 'Account',
        'debit': 'Debit',
        'credit': 'Credit',
        'balance': 'Balance',
    };
    var aged_partner_fields = {
        'name': 'Partners',
        'direction': 'Not due',
        'l4': 'Credit',
        'l3': 'Balance',
        'l2': 'Balance',
        'l1': 'Balance',
        'l0': 'Balance',
        'total': 'Total',
    };
    var tax_report_fields = {
        'name': 'Partners',
        'net': 'Net',
        'tax': 'Tax'
    };

    var DynamicReportAction = AbstractAction.extend({
        events: {
            'click .fetch_report_btn': '_getReportContent',
            'change select, input': 'onChangeReportData',
            'click tr.r_line': 'toggleReportLine',
            'click .report_buttons div': 'printReport',
        },
        init: function () {
            this._super.apply(this, arguments);
            this.report_type = [];
            this.fixed_reports = [];
            this.journal_ids = [];
            this.report_data = {};
            this.line_count = 0;
            this.current_level = 0;
            this.previous_level = 0;

            this.report_lines = {};
            this.report_line_ids = {};
            this.line_status = {};
            this.levels = {};
            this.currency_data = {};
        },
        willStart: function () {
            var self = this;
            var def = [];
            var report_def = rpc.query({
                model: 'account.financial.report',
                method: 'search_read',
                fields: ['name'],
                domain: [['parent_id', '=', false]]
            }).then(function (result) {
                self.report_type = result;

                for (var i=0;i<result.length;i++) {
                    result[i].type = 'config';
                }

                var other_reports = self._fetchOtherReports();

                self.fixed_reports = $.map(other_reports, function(rec) {
                    return rec.id;
                });

                self.report_type = self.report_type.concat(other_reports);
            });

            var config_def = rpc.query({
                model: 'account.journal',
                method: 'search_read',
                fields: ['name']
            }).then(function (result) {
                self.journal_ids = result;
            });

            return $.when($, report_def, config_def);
        },
        start: function () {
            var self = this;
            this._super.apply(this, arguments).then(function () {
                self._updateReportController();
            });
        },
        _updateReportController: function () {
            this.$el.html(
                Qweb.render('om_dynamic_reports.DynamicReports', {
                    'widget': this
                }
            ));

            this.$el.find('select').select2();

            this.$el.find('.report_buttons').hide();
        },
        /*events*/
        _fetchOtherReports: function () {
            return [{
                id: 'journals_audit',
                name: 'Journals Audit',
                type: 'fixed'
            }, {
                id: 'partner_ledger',
                name: 'Partner Ledger',
                type: 'fixed'
            }, {
                id: 'general_ledger',
                name: 'General Ledger',
                type: 'fixed'
            }, {
                id: 'trial_balance',
                name: 'Trial Balance',
                type: 'fixed'
            }, {
                id: 'aged_partner',
                name: 'Aged Partner Balance',
                type: 'fixed'
            }, {
                id: 'tax_report',
                name: 'Tax Report',
                type: 'fixed'
            }];
        },
        onChangeReportData: function (e) {
            var self = this;
            var active_el = $(e.currentTarget);

			this.strict_range = true;
			if (active_el.attr('name') == 'account_report_id') {
                if (!active_el.val()) {
                    this.report_data = {};
                    this.$el.find('.report_buttons').hide();
                }
                else {
                    this.report_data.account_report_id = [
                        active_el.val(),
                        this._getReportName(active_el.val())];
                    switch (active_el.val()) {
                        case 'journals_audit': {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('journals_audit', {widget: this})));
                            this.addField('target_move', 'select');
                            this.addField('sort_selection', 'select');
                            this.addField('date_from', 'input');
                            this.addField('date_to', 'input');
                            this.addField('journal_ids', 'select');

                            break;
                        };
                        case 'partner_ledger': {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('partner_ledger', {widget: this})));

                            this.addField('target_move', 'select');
                            this.addField('result_selection', 'select');
                            this.addField('reconciled', 'checkbox');
                            this.addField('date_from', 'input');
                            this.addField('date_to', 'input');
                            this.addField('journal_ids', 'select');

                            break;
                        };
                        case 'general_ledger': {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('general_ledger', {widget: this})));

                            this.addField('target_move', 'select');
                            this.addField('sortby', 'select');
                            this.addField('display_account', 'select');
                            this.addField('initial_balance', 'checkbox');
                            this.addField('date_from', 'input');
                            this.addField('date_to', 'input');
                            this.addField('journal_ids', 'select');

                            break;
                        };
                        case 'trial_balance': {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('trial_balance', {widget: this})));

                            this.addField('target_move', 'select');
                            this.addField('display_account', 'select');
                            this.addField('date_from', 'input');
                            this.addField('date_to', 'input');
                            break;
                        };
                        case 'aged_partner': {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('aged_partner', {widget: this})));

                            this.addField('target_move', 'select');
                            this.addField('result_selection', 'select');
                            this.addField('date_from', 'input');
                            this.addField('period_length', 'input');

                            this.$el.find('.ctrl_body .date_from').addClass('o_required');
                            this.$el.find('.ctrl_body .period_length').addClass('o_required');

                            break;
                        };
                        case 'tax_report': {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('tax_report', {widget: this})));
                            this.addField('date_from', 'input');
                            this.addField('date_to', 'input');

							this.$el.find('.ctrl_body .date_from').addClass('o_required');
                            this.$el.find('.ctrl_body .date_to').addClass('o_required');

                            break;
                        };
                        default: {
                            this.$el.find('.ctrl_body').replaceWith($(Qweb.render('profit_loss', {widget: this})));

                            this.addField('target_move', 'select');
                            this.addField('debit_credit', 'checkbox');
                            this.addField('date_from', 'input');
                            this.addField('date_to', 'input');
                        };
                    };

                    this.$el.find('select.account_report_id').val(this.report_data.account_report_id[0]);
                }
                this.$el.find('select').select2();
            }

			else {
	            /*caching the changed value*/
	            if (active_el.attr('type') == 'checkbox') {
	                this.report_data[active_el.attr('name')] = active_el.is(":checked");
	            }
	            else if (active_el.attr('name') == 'journal_ids') {
	                this.report_data[active_el.attr('name')] = [];
	                _.each(active_el.val(), function (val) {
	                    self.report_data[active_el.attr('name')].push(parseInt(val));
	                });
	            }
	            else {
	                this.report_data[active_el.attr('name')] = active_el.val();
	            }
            }
        },
        addField: function (name, type) {
            var self = this;
            if (name == 'journal_ids') {
                this.report_data[name] = [];
                _.each(this.$el.find('.dynamic_control_header select.journal_ids').val(), function (val) {
                    self.report_data[name].push(parseInt(val));
                });
            }
            else if (name == 'date_from' || name == 'date_to') {
                this.report_data[name] = this.$el.find('.dynamic_control_header .'+name).val();
            }
            else if (type == 'checkbox') {
                this.report_data[name] = this.$el.find('.dynamic_control_header .' + name).is(":checked");
            }
            else if (type == 'select') {
                this.report_data[name] = this.$el.find('.dynamic_control_header select.'+name).val();
            }
            else {
                this.report_data[name] = this.$el.find('.dynamic_control_header .'+name).val();
            }
        },
        toggleReportController: function (e) {
            this.$el.find('.dynamic_control_header .h_row').toggleClass('hidden');

            this.$el.find('.dynamic_control_header .h_row.ctrl').toggleClass('hidden ');

            var active_el = $(e.currentTarget);
            active_el.toggleClass('fa-angle-up');
            active_el.toggleClass('fa-angle-down');
        },
        toggleReportLine: function (e) {
            $('body').addClass('loading');
            var active_el = $(e.currentTarget);
            var parent_id = parseInt(active_el.data('id'));

            var att_res_id = active_el.attr('res_id');
            if (att_res_id != null && parseInt(att_res_id) > 0) {
                $('body').removeClass('loading');
                return this.openJournalItem(att_res_id);
            }
            /*child status*/
            if (this.line_status[parent_id] == 'open') {
                this.line_status[parent_id] = 'closed';
                this._hideChildren(parent_id);
                $('body').removeClass('loading');
            }
            else if (this.line_status[parent_id] == 'closed') {
                this.line_status[parent_id] = 'open';
                if (!this.levels[parent_id] && this.report_lines[parent_id] && this.report_lines[parent_id].has_child_lines) {
                    var level = active_el.attr('level');
                    this.fetchLineData(parent_id, level);
                }
                else {
                    this._showChildren(parent_id);
                    $('body').removeClass('loading');
                }
            }
        },

        /*other methods*/
        fetchLineData: function (line_id, level) {
            $('body').addClass('loading');
            this.toggleCaretIcon(line_id);
            var model = '', method_name='', active_id = '', self = this;
            var report_id = this.report_data.account_report_id[0], args_list = [], kwargs=[];
            if (this.report_data.report_type == 'config') {
                model = 'report.accounting_pdf_reports.report_financial';
                method_name = 'get_journal_data';
                active_id = this.report_lines[line_id].active_id;
                active_id = active_id.split('_')[1];
                args_list = [parseInt(active_id), parseInt(level), self.report_data.debit_credit];
            }
            else if (report_id == 'journals_audit') {
                model = 'report.accounting_pdf_reports.report_journal';
                method_name = 'lines_dynamic';
                active_id = this.report_lines[line_id].active_id;
                var r_input = this._getReportInput();
                for (var i in r_input['journal_ids']) {
                    r_input[i] = parseInt(r_input[i]);
                }
                r_input['used_context']['journal_ids'] = r_input['journal_ids'];
                var data = {'form': r_input}
                args_list = [this.report_data.target_move, active_id, this.report_data.sort_selection, data];
            }
            else if (report_id == 'general_ledger') {
                model = 'report.accounting_pdf_reports.report_general_ledger';
                method_name = 'get_account_data';
                active_id = this.report_lines[line_id].active_id;
                var r_input = this._getReportInput();
                args_list = [r_input, active_id];
                kwargs = {context: this.report_data.used_context};
            }
            else if (report_id == 'trial_balance') {
                model = 'report.accounting_pdf_reports.report_trialbalance';
                method_name = 'get_accounts_child';
                active_id = this.report_lines[line_id].active_id;
                args_list = [active_id];
                kwargs = {context: this.report_data.used_context};
            }
            rpc.query({
                model: model,
                method: method_name,
                args: args_list,
                kwargs: kwargs
            }).then(function(res) {
                self.levels[line_id] = res;
                var report_lines = "";
                if (self.report_data.report_type == 'config') {
                    for (var i in res) {
                        report_lines += self._build_line(res[i]);
                    }
                }
                else if (report_id == 'journals_audit') {
                    self.line_count++;
                    var section_line = Object.assign(
                        {},
                        journals_audit_fields);
                    section_line.id = self.line_count;
                    section_line.active_id = self.line_count;
                    section_line.parent = line_id;
                    section_line.level = 1;
                    section_line.line_type = 'section_heading';

                    self.report_line_ids[line_id] = self.line_count;
                    report_lines += self._build_line(section_line);
                    for (var j=0;j<res.length;j++) {
                        self.line_count++;
                        res[j].parent = line_id;
                        res[j].level = 2;
                        res[j].id = self.line_count;
                        res[j].active_id = self.line_count;
                        report_lines += self._build_line(res[j]);
                    }
                }
                else if (report_id == 'general_ledger') {
                    var line_data = [];
                    if (!res || res.length == 0)
                        return
                    for (var j=0;j<res[0]['move_lines'].length;j++) {
                        self.line_count++;
                        var temp = res[0]['move_lines'][j];

                        for (var k in g_ledger_fields) {
                            if (temp[k] == null) {
                                temp[k] = '';
                            }
                        }

                        temp.res_id = temp.lid;
                        temp.id = self.line_count;
                        temp.active_id = self.line_count;
                        temp.parent = line_id;
                        temp.level = 1;

                        report_lines += self._build_line(temp);
                    }
                }
                else if (report_id == 'trial_balance') {
                    for (var j=0;j<res.length;j++) {
                        self.line_count++;
                        res[j].parent = line_id;
                        res[j].id = self.line_count;
                        res[j].active_id = self.line_count;
                        report_lines += self._build_line(res[j]);
                    }
                }

                var $tr = self.$el.find('tr[data-id="'+line_id+'"]');
                $tr.after(report_lines);
                $('body').removeClass('loading');
            })
        },
        openJournalItem: function (res_id) {
            if (isNaN(res_id) || parseInt(res_id) < 1) {
                return;
            }
            return this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'account.move.line',
                views: [[false, 'form']],
                target: 'current',
                res_id: parseInt(res_id)
            });
        },
        _getReportName: function (r_id) {
            if (!r_id) {
                return "";
            }
            else {
                var r_name = "";

                for (var i=0;i<this.report_type.length;i++) {
                    if (this.report_type[i].id == r_id) {
                        r_name = this.report_type[i].name;
                        break;
                    }
                }

                return r_name;
            }
        },
        _showChildren: function (parent_id) {
            var parent = this.report_lines[parent_id];
            if (!parent)
                return;
            if (this.levels[parent_id]) {
                this.toggleCaretIcon(parent_id);
                var report_id = this.report_data.account_report_id[0], args_list = [], $tr = null;
                if (this.report_data.report_type == 'config') {
                    $tr = this.$el.find('tr[parent="'+parent.active_id+'"]');
                }
                else if (['journals_audit', 'general_ledger', 'trial_balance'].includes(report_id)) {
                    $tr = this.$el.find('tr[parent="'+parent.id+'"]');
                }
                $tr ? $tr.show() : null;
                return;
            }
            else {
                var line_length = this.line_count;
                this.toggleCaretIcon(parent_id);

                for (var i=parent_id + 1;i<=line_length;i++) {
                    if (this.report_lines[i] && this.report_lines[i].parent == parent.active_id) {
                        this.$el.find('tr[data-id="'+this.report_lines[i].id+'"]').show();

                    }
                }
            }
        },
        _hideChildren: function (parent_id) {
            var parent = this.report_lines[parent_id];
            if (!parent)
                return;
            if (this.levels[parent_id]) {
                this.toggleCaretIcon(parent_id);
                var $tr = null;
                var report_id = this.report_data.account_report_id[0];
                if (this.report_data.report_type == 'config') {
                    $tr = this.$el.find('tr[parent="'+parent.active_id+'"]');
                }
                else if (['journals_audit', 'general_ledger', 'trial_balance'].includes(report_id)) {
                    $tr = this.$el.find('tr[parent="'+parent.id+'"]');
                }

                $tr ? $tr.hide(): null;
                return;
            }
            else {
                var line_length = this.line_count;
                if (this.report_line_ids[parent.active_id] != null) {
                    this.toggleCaretIcon(parent_id);
                }

                for (var i=parent_id + 1;i<=line_length;i++) {
                    if (this.report_lines[i] && this.report_lines[i].parent == parent.active_id) {
                        var $tr = this.$el.find('tr[data-id="'+this.report_lines[i].id+'"]');
                        $tr.hide();
                        /*check inner childs*/
                        if (this.line_status[this.report_lines[i].id] == 'open') {
                            this.line_status[this.report_lines[i].id] = 'closed';
                            this._hideChildren(this.report_lines[i].id);
                        }
                    }
                }
            }
        },
        toggleCaretIcon: function (parent_id) {
            var parent_el = this.$el.find("tr[data-id='"+parent_id+"']");
            var $td = $(parent_el.find('td')[0]);
            $td.find('i').toggleClass('fa-caret-right');
            $td.find('i').toggleClass('fa-caret-down');
            return;
        },
        _getReportContent: function (e) {
            var self = this;

            var data = this._getReportInput();
            self.current_report_data = Object.assign({}, {});
            if (data) {
                framework.blockUI();
                rpc.query({
                    model: 'dynamic.report.config',
                    method: 'check_report',
                    args: [data]
                }).then(function (result) {
                    self.line_status = {};
                    self.levels = {};
                    self.current_report_data = Object.assign({}, self.report_data);
                    self.currency_data = result[1];
                    self.updateReportBody(result[0]);

                    self.updateResizable();

                    self.$el.find('.report_buttons').show();
                    framework.unblockUI();
                });
            }
        },
        getCurrentReport: function () {
            if (!this.report_data.account_report_id) {
                alert("No report selected");
                return;
            }

            for (var i=0;i<this.report_type.length;i++) {
                if (this.report_type[i].id == this.report_data.account_report_id[0]) {
                    return this.report_type[i];
                }
            }

            alert("Error occurred, please try again");
            return;
        },
        checkRequiredFields: function () {
            var $el = this.$el.find('.dynamic_control_header .o_required');

			var fields_missing = false;
            for (var i=0;i<$el.length;i++) {
                var el_name = $($el[i]).attr('name');
                if (!el_name) {continue;}
                if (!$($el[i]).val()) {
                    fields_missing = true;
                    if ($($el[i]).hasClass('select_2')) {
                        this.$el.find('.dynamic_control_header .' + el_name).css('border', '1px solid red');
                    }
                    else {
                        $($el[i]).css('border', '1px solid red');
                    }
                }
                else {
                    if ($($el[i]).hasClass('select_2')) {
                        this.$el.find('.dynamic_control_header .' + el_name).css('border', '1px solid #aaa');
                    }
                    else {
                        $($el[i]).css('border', '1px solid #aaa');
                    }
                }
            }

            return fields_missing;
        },
        _getReportInput: function () {
            if (this.checkRequiredFields()) {
                return false;
            }

            var report = this.getCurrentReport();

            this.report_data.company_id = this.currency_data.company_id ? this.currency_data.company_id : [1, ''];
            this.report_data.filter_cmp = 'filter_no';
            this.report_data.enable_filter = false;
            this.report_data.label_filter = false;

            this.report_data.date_from_cmp = false;
//            this.report_data.debit_credit = false;
            this.report_data.date_to_cmp = false;

            this.report_data.date_from = this.report_data.date_from ? this.report_data.date_from : false;
            this.report_data.date_to = this.report_data.date_to ? this.report_data.date_to : false;

            this.report_data.used_context = {
                'journal_ids': this.report_data.journal_ids,
                'state': this.report_data.target_move,
                'sort_selection': this.report_data.sort_selection,
                'result_selection': this.report_data.result_selection,
                'reconciled': this.report_data.reconciled,
                'date_from': this.report_data.date_from,
                'date_to': this.report_data.date_to,
                'strict_range': this.strict_range,
                'company_id': this.report_data.company_id[0],
            };

            if (report && report.type == 'config') {
                /*P & L or Balance sheet*/
                /*doing nothing right now*/
                this.report_data.report_type = 'config';
            }
            else {
                /*other reports*/
                this.report_data.report_type = 'fixed';
                this.report_data.amount_currency = true;
            }


            return this.report_data;
        },
        _findParent: function (index, req_type, o_index) {
            /*reverse parse the lines and find immediate parent*/
            if (index == 0 && !req_type) {
                return false;
            }
            else if (index == 0 && req_type == 'recursive') {
                return this.report_lines[0].id;
            }

            for(var i=index-1;i>=0;i--) {
                if (this.report_lines[i].level < this.report_lines[index].level &&
                        this.report_lines[i].level < this.report_lines[o_index].level) {
                    return this.report_lines[i].id;
                }
                else {
                    return this._findParent(i, 'recursive', o_index);
                }
            }

            return false;
        },
        _processData: function (report_lines, report_type) {
            this.report_lines = {};
            this.report_line_ids = {};
            this.line_count = 0;

            if (report_type == 'fixed') {
                var report_id = this.report_data.account_report_id[0];

                switch (report_id) {
                    case 'journals_audit': this._process_journals_audit(report_lines); break;
                    case 'partner_ledger': this._process_partner_ledger(report_lines); break;
                    case 'general_ledger': this._process_general_ledger(report_lines); break;
                    case 'trial_balance': this._process_trial_balance(report_lines); break;
                    case 'aged_partner': this._process_aged_partner(report_lines); break;
                    case 'tax_report': this._process_tax_report(report_lines); break;
                    default : {};
                };
            }
            else {
                for (var i=0;i<report_lines.length;i++) {
                    report_lines[i].id = i;
                    report_lines[i].level = parseInt(report_lines[i].level);
                    this.report_lines[i] = report_lines[i];

                    this.report_line_ids[report_lines[i].parent] = i;
                }

                this.line_count = i > 0 ? (i -1) : 0;
            }

            return;
        },
        _build_root_line: function (colspan) {
            this.report_lines[0] = {
                id: 0,
                active_id: 0,
                parent: false,
                title: this.report_data.account_report_id[1],
                level:0,
                res_id: -1,
                colspan: colspan,
                line_type: 'root'
            };
            this.report_line_ids[false] = 0;
        },
        _process_trial_balance: function (report_lines) {
            this._build_root_line(2);
            /*sum of debit credit and balance columns*/
            this.report_lines[0] = Object.assign(this.report_lines[0], {
                debit: 0,
                credit: 0,
                balance: 0,
            });

            for (var l=0;l<report_lines.length;l++) {
                if (report_lines[l].line_type != 'journal_item') {
                    this.report_lines[0]['debit'] += report_lines[l].debit;
                    this.report_lines[0]['credit'] += report_lines[l].credit;
                    this.report_lines[0]['balance'] += report_lines[l].balance;
                }
            }

            this.line_count++;
            this.report_lines[this.line_count] = Object.assign(
                {},
                trial_balance_fields)

            this.report_lines[this.line_count].id = this.line_count;
            this.report_lines[this.line_count].active_id = this.line_count;
            this.report_lines[this.line_count].parent = 0;
            this.report_lines[this.line_count].level = 1;
            this.report_lines[this.line_count].res_id = -1;
            this.report_lines[this.line_count].line_type = 'section_heading';

            this.report_line_ids[0] = this.line_count;
			var parent_id = 0, l_id;
            for (var i=0;i<report_lines.length;i++) {
                this.line_count++;

                report_lines[i].id = this.line_count;

                this.report_lines[this.line_count] = report_lines[i];
//                if (report_lines[i].level == 1) {
                l_id = 	this.line_count;
                report_lines[i].parent = parent_id;
                this.report_line_ids[parent_id] = this.line_count;
//                }
//                else {
//                    report_lines[i].parent = l_id;
//                    this.report_line_ids[l_id] = this.line_count;
//                }
            }
        },
        _process_aged_partner: function (report_lines) {
            this._build_root_line(8);

            for (var i=0;i<report_lines.length;i++) {
                this.line_count++;

                report_lines[i].level = 1;

                this.report_lines[this.line_count] = report_lines[i]
                this.report_line_ids[0] = this.line_count;
            }
        },
        _process_tax_report: function (report_lines) {
            this._build_root_line(3);

            for (var i=0;i<report_lines.length;i++) {
                this.line_count++;
                this.report_lines[this.line_count] = report_lines[i]
                this.report_line_ids[report_lines[i].parent] = this.line_count;
            }
        },
        _process_partner_ledger: function (report_lines) {
            this._build_root_line(7);

            this.line_count++;
            this.report_lines[this.line_count] = Object.assign(
                {},
                p_ledger_fields)

            /*because in the child lines, the field name is 'progress'*/
            delete this.report_lines[this.line_count].progress;

            this.report_lines[this.line_count].id = this.line_count;
            this.report_lines[this.line_count].active_id = this.line_count;
            this.report_lines[this.line_count].line_type = 'font_bold';
            this.report_lines[this.line_count].parent = 0;
            this.report_lines[this.line_count].level = 0;
            this.report_lines[this.line_count].res_id = -1;

            this.report_line_ids[0] = this.line_count;

            var parent_id = 0;

            for (var i=0;i<report_lines.length;i++) {
                this.line_count++;

                if (report_lines[i].line_type == 'section_heading') {
                    report_lines[i].id = this.line_count;
                    report_lines[i].active_id = this.line_count;
                    report_lines[i].parent = 0;
                    report_lines[i].level = 0;
                    report_lines[i].res_id = -1;

                    this.report_lines[this.line_count] = report_lines[i]
                    this.report_line_ids[0] = this.line_count;

                    parent_id = this.line_count;
                }
                else {
                    report_lines[i].res_id = report_lines[i].id;
                    report_lines[i].id = this.line_count;
                    report_lines[i].active_id = this.line_count;
                    report_lines[i].parent = parent_id;
                    report_lines[i].level = 1;

                    this.report_lines[this.line_count] = report_lines[i]
                    this.report_line_ids[parent_id] = this.line_count;
                }
            }
        },
        _process_general_ledger: function (report_lines) {
            this._build_root_line(9);

            this.line_count++;
            this.report_lines[this.line_count] = Object.assign(
                {},
                g_ledger_fields)

            this.report_lines[this.line_count].id = this.line_count
            this.report_lines[this.line_count].active_id = this.line_count
            this.report_lines[this.line_count].parent = 0
            this.report_lines[this.line_count].level = 0
            this.report_lines[this.line_count].res_id = -1
            this.report_lines[this.line_count].line_type = 'font_bold'

            this.report_line_ids[0] = this.line_count;

            var parent_id = 0;

            for (var i=0;i<report_lines.length;i++) {
                this.line_count++;

				var temp_line = {
					id: this.line_count,
					active_id: report_lines[i].active_id,
					parent: 0,
					level: 0,
					res_id: -1,
					line_type: "section_heading",
					ldate: report_lines[i].code + " " + report_lines[i].name,
					debit: report_lines[i].debit,
					credit: report_lines[i].credit,
					balance: report_lines[i].balance,
					has_child_lines: report_lines[i].has_child_lines
				};

                this.report_lines[this.line_count] = temp_line;
                this.report_line_ids[0] = this.line_count;

                parent_id = this.line_count;
            }
        },
        _process_journals_audit: function (report_lines) {
            this._build_root_line(7);

            for (var i in report_lines) {
                this.line_count++;
                this.report_lines[this.line_count] = {
                    id: this.line_count,
                    active_id: i,
                    parent: 0,
                    move_id: this.getJournalName(i),
                    level: 0,
                    res_id: -1,
                    line_type: 'section_heading',
                    has_child_lines: true
                };
                this.report_line_ids[0] = this.line_count;

                var parent_id = this.line_count;
            }
            return;
        },
        updateReportBody: function (result) {
            /*process the report lines, setup parent - child relation*/
            if (this.report_data.report_type == 'config') {
                this._processData(result);
            }
            else {
                this._processData(result, 'fixed');
            }

            var report_body = this.build_report_lines();

            this.$el.find('.dynamic_report_body').html(report_body);

            this._updateAfterRender();

            return;
        },
        _updateAfterRender: function () {
            var report_id = this.report_data.account_report_id[0];
            if (report_id == 'journals_audit') {
                var $root_line = this.$el.find('.dynamic_report_body tr[parent="0"]');
            }
            else if (['partner_ledger', 'general_ledger', 'trial_balance'].includes(report_id)) {
                var $root_line = this.$el.find('.dynamic_report_body tr[parent="0"]');
                for (var i=0;i<$root_line.length;i++)
                    $($root_line[i]).trigger('click')
            }
            else if (report_id != 'aged_partner' && report_id != 'tax_report') {
                var $root_line = this.$el.find('.dynamic_report_body tr[data-id="0"]');
                $root_line.length > 0 ? $root_line.trigger('click') : null;
            }

            this.$el.find('.h_row.ctrl > i').trigger('click');
        },
        build_report_lines: function () {
            var report_lines = "<div class='r_content'><table class='table_r_content'>";

			if (this.report_data.report_type == 'config') {
				report_lines += this._build_header();
			}

            var report_content = this.report_lines;

            for (var i in report_content) {
                /*loop through report lines*/

                var line_data = report_content[i];

                report_lines += this._build_line(line_data);
            }
            report_lines += "</table></div>";

            return report_lines;
        },
        getJournalName: function (journal) {
            for (var i=0;i<this.journal_ids.length;i++) {
                if (this.journal_ids[i].id == journal) {
                    return this.journal_ids[i].name;
                }
            }

            return "";
        },
        _build_header: function () {
            var result = "<tr class='r_line font_bold' >";
            var report_id = this.report_data.account_report_id[0];

            switch (report_id) {
                case 'journals_audit': {
                    for (var i in journals_audit_fields) {
                        result += "<td name='"+i+"'>" +
                            journals_audit_fields[i] + "</td>";
                    }
                    break;
                }
                default: {
					for (var i in balance_sheet_fields) {
						if (this.report_data.debit_credit == false &&
							['debit', 'credit'].includes(i)) {
							continue;
						}
                        result += "<td name='"+i+"'>" +
                            balance_sheet_fields[i] + "</td>";
                    }
                }
            };

            result += "</tr>";
            return result;
        },
        _build_line: function (r_line) {
            /*based on the report type, we may need to use different
            mechanisms*/

            var line_html, line_stat = 'open';
			if (this.report_data.report_type == 'config') {
				/*P & L and BS*/
				line_html = this._build_type_a(r_line);
				line_stat = r_line.has_child_lines ? 'closed': 'open';
			}
            else {
                /*other reports: journals audit, ...,*/
                var report_id = this.report_data.account_report_id[0];

				if (r_line.line_type == 'root') {
					line_html = this._build_root_line_html(r_line);
				}
                else if (report_id == 'journals_audit') {
                    line_stat = 'closed';
                    line_html = this._build_type_b(r_line);
                }
                else if (report_id == 'partner_ledger') {
                    line_html = this._build_type_c(r_line);
                }
                else if (report_id == 'general_ledger') {
                    line_html = this._build_type_d(r_line);
                }
                else if (report_id == 'trial_balance') {
                    line_html = this._build_type_e(r_line);
                }
                else if (report_id == 'aged_partner') {
                    line_html = this._build_type_f(r_line);
                }
                else if (report_id == 'tax_report') {
                    line_html = this._build_type_g(r_line);
                }
            }

            /*opened or closed the child lines*/
            this.line_status[r_line.id] = line_stat;

            return line_html;
        },
        _build_root_line_html: function (r_line) {
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id='0' level='0' parent='false'>";

            var first_col = true;
            result += this.build_row_col('title',
                                         r_line['title'],
                                         0,
                                         r_line.colspan ? r_line.colspan : 0,
                                         first_col == true ? r_line.id : null, r_line);
            first_col = false;
            var report_id = this.report_data.account_report_id[0];
            if (report_id == 'trial_balance') {
                var cols = ['debit', 'credit', 'balance'];
                for (var i in cols) {
                    result += this.build_row_col(cols[i],
                        r_line[cols[i]],
                        0,
                        1,
                        null, r_line);
                }

            }
            result += "</tr>";

            return result;
        },
        _build_type_a: function (r_line) {
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+ " line_id=" + r_line.active_id +
                " parent='"+r_line.parent+"'";

            if (r_line.line_id)
                result += " res_id=" + r_line.line_id;
            result += ">";

            var first_col = true;
            for (var i in balance_sheet_fields) {
                if (this.check_value(r_line[i])) {
                    result += this.build_row_col(i, r_line[i], r_line.level, 1,
                                                 first_col == true ? r_line.active_id : null, r_line);
                    first_col = false;
                }
            }
            result += "</tr>";

            return result;
        },
        _build_type_b: function (r_line) {
            /*journals audit*/
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+
                " parent='"+r_line.parent+"' res_id='"+r_line.res_id+"'>";

            var first_col = true;
			if (r_line.level == 0) {
				result += this.build_row_col(
                    'move_id',
                    r_line['move_id'],
                    r_line.level, 7, first_col == true ? r_line.id : null, r_line);
                first_col = false;
			}
			else {
	            for (var i in journals_audit_fields) {
	                if (this.check_value(r_line[i])) {
	                    result += this.build_row_col(i,
                        	                         r_line[i],
                        	                         r_line.level, 1,
                        	                         first_col == true ? r_line.id : null,r_line);
                        first_col = false;
	                }
	            }
	        }

            result += "</tr>";

            return result;
        },
        _build_type_c: function (r_line) {
            /*Partner ledger*/
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+
                " parent='"+r_line.parent+"' res_id='"+r_line.res_id+"'>";

            var first_col = true;
			if (r_line.line_type == 'section_heading') {
			    for (var i in p_ledger_fields) {
                    if (this.check_value(r_line[i])) {
                        var colspan = i == 'date' ? 4 : 1;
                        result += this.build_row_col(i,
                                                     r_line[i],
                                                     r_line.level,
                                                     colspan,
                                                     first_col == true ? r_line.id : null, r_line);
                        first_col = false;
                    }
                }
			}
			else {
			    for (var i in p_ledger_fields) {
                    if (this.check_value(r_line[i])) {
                        result += this.build_row_col(i,
                                                     r_line[i],
                                                     r_line.level, 1,
                                                     first_col == true ? r_line.id : null, r_line);
                        first_col = false;
                    }
                }
			}

            result += "</tr>";

            return result;
        },
        _build_type_d: function (r_line) {
            /* GL*/
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+
                " parent='"+r_line.parent+"' res_id='"+r_line.res_id+"'>";

            var first_col = true;
			if (r_line.line_type == 'section_heading') {
			    for (var i in g_ledger_fields) {
                    if (this.check_value(r_line[i])) {
                        var colspan = i == 'ldate' ? 6 : 1;
                        result += this.build_row_col(i,
                                                     r_line[i],
                                                     r_line.level,
                                                     colspan,
                                                     first_col == true ? r_line.id : null, r_line);
                        first_col = false;
                    }
                }
			}
			else {
			    for (var i in g_ledger_fields) {
                    if (this.check_value(r_line[i])) {
                        result += this.build_row_col(i,
                                                     r_line[i],
                                                     r_line.level, 1,
                                                     first_col == true ? r_line.id : null, r_line);
                        first_col = false;
                    }
                }
			}

            result += "</tr>";

            return result;
        },
        _build_type_e: function (r_line) {
			/*trial balance*/
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+
                " parent='"+r_line.parent+"' res_id='"+r_line.res_id+"'>";

            var first_col = true;
			for (var i in trial_balance_fields) {
                if (this.check_value(r_line[i])) {
                    result += this.build_row_col(i,
                                                 r_line[i],
                                                 r_line.level, 1,
                                                 first_col == true ? r_line.id : null,
                                                 r_line);
                    first_col = false;
                }
            }

            result += "</tr>";

            return result;
        },
        _build_type_f: function (r_line) {
			/*aged partner*/
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+
                " parent='"+r_line.parent+"' res_id='-1'>";

			var first_col = true;
			for (var i in aged_partner_fields) {
                if (this.check_value(r_line[i])) {
                    result += this.build_row_col(i,
                                                 r_line[i],
                                                 r_line.level, 1,
                                                 first_col == true ? r_line.id : null, r_line);
                    first_col = false;
                }
            }

            result += "</tr>";

            return result;
        },
        _build_type_g: function (r_line) {
			/*tax report*/
            var row_class = this.build_row_class(r_line);

            var result = "<tr class='"+row_class+
                "' data-id="+r_line.id+" level="+r_line.level+
                " parent='"+r_line.parent+"' res_id='-1'>";

			var first_col = true;
			for (var i in tax_report_fields) {
                if (this.check_value(r_line[i])) {
                    result += this.build_row_col(i,
                                                 r_line[i],
                                                 r_line.level,
                                                 1,
                                                 first_col == true ? r_line.id : null, r_line);
                    first_col = false;
                }
            }

            result += "</tr>";

            return result;
        },
        build_row_col: function (col_key, col_data, level, colspan, row_id, r_line) {
            var col_style = this.build_col_style(col_key, level);
            var col_class = this.build_col_class(col_key);

            var res = "<td class='" + col_class + "' " +
                "level='level_"+ level + "' " +
                "name='" + col_key + "' style='"+col_style + "'";
            res += colspan ? " colspan='" + colspan + "'" : "";
            res += ">";

            var line_type = r_line ? r_line.line_type : '';
            var display_value = line_type != 'section_heading' ? this.formatOutput(col_key, col_data) : col_data;
            res += this.buildIcon(row_id, r_line);
            res += "<span>"+display_value+"</span>";

            res += "</td>";

            return res;
        },
        formatOutput: function (col_key, value) {
            var result;

            if (typeof value == 'number') {
                /*currency formatting needed*/

                /*set decimal places*/
                var decimal_places = this.currency_data && this.currency_data.decimal_places ? this.currency_data.decimal_places : 2;
                value = typeof value == 'number' ? value.toFixed(decimal_places) : value;
                value = this.addSeparatorsNF(parseFloat(value),'.','.',',');
                result = value;

                if (value != '' && this.currency_data) {
                    if (this.currency_data.position == 'after') {
                        result = value + " " + this.currency_data.symbol;
                    }
                    else if (this.currency_data.position == 'before') {
                        result = this.currency_data.symbol + " " + value;
                    }
                }
            }
            else {
                result = value;
            }

            return result;
        },
        build_col_style: function (col_key, level) {
            var style_str = "";
            var report_id = this.report_data.account_report_id[0];

            switch (report_id) {
                case 'journals_audit': {
                    if (col_key == 'move_id') {
                        style_str += 'padding-left:' + (parseInt(level) * 6) + 'px';
                    }
                    break;
                };
                case 'partner_ledger': {
                    if (col_key == 'date') {
                        style_str += 'padding-left:' + (parseInt(level) * 6) + 'px';
                    }
                    break;
                };
                case 'general_ledger': {
                    if (col_key == 'ldate') {
                        style_str += 'padding-left:' + (parseInt(level) * 6) + 'px';
                    }
                    break;
                };
                case 'trial_balance': {
                    if (col_key == 'code') {
                        style_str += 'padding-left:' + (parseInt(level) * 6) + 'px';
                    }
                    break;
                };
                default: {
                    if (col_key == 'name') {
                        style_str += 'padding-left:' + (parseInt(level) * 6) + 'px';
                    }
                }
            };

            return style_str;
        },
        build_col_class: function (col_key) {
            var class_str = "";
            if (col_key == 'name') {
                class_str += 'col_name';
            }
            else if (col_key == 'balance') {
                class_str += 'col_balance';
            }

            return class_str;
        },
        buildIcon: function (parent, r_line) {
            var res = "";
            if (parent != null && this.report_line_ids[parent] != null) {
                res = "<i class='fa fa-caret-down'/>";
            }
            else if (parent != null && r_line.has_child_lines) {
                res = "<i class='fa fa-caret-right'/>";
            }
            return res;
        },
        build_row_class: function (r_line) {
            var r_class = 'r_line';

            if (['font_bold', 'root', 'section_heading'].includes(r_line.line_type)) {
                r_class += " " + r_line.line_type;
            }
            return r_class;
        },
        check_value: function (value) {
            return value == null ? false : true;
        },
        updateResizable: function () {
			$(".panel-top").resizable({
				handleSelector: ".splitter-horizontal",
				resizeWidth: false
			});
        },
        addSeparatorsNF: function (nStr, inD, outD, sep){
            nStr += '';
            var dpos = nStr.indexOf(inD);
            var nStrEnd = '';
            if (dpos != -1) {
            nStrEnd = outD + nStr.substring(dpos + 1, nStr.length);
            nStr = nStr.substring(0, dpos);
            }
            var rgx = /(\d+)(\d{3})/;
            while (rgx.test(nStr)) {
            nStr = nStr.replace(rgx, '$1' + sep + '$2');
            }
            return nStr + nStrEnd;
        }
    });

    core.action_registry.add('dynamic_reports_view', DynamicReportAction);

    return DynamicReportAction;
});
