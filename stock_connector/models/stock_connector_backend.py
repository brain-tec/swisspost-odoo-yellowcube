# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.connector \
    import ConnectorUnit, ConnectorEnvironment
from .constants import SQL_RELEASE, SQL_ROLLBACK, SQL_SAVEPOINT
import logging
_logger = logging.getLogger(__name__)


class StockConnectorBackend(models.Model):
    _name = 'stock_connector.backend'
    _description = 'Warehouse Backend'
    _inherit = 'connector.backend'

    _backend_type = 'stock'

    @api.model
    def select_versions(self):
        return [('0.1', '0.1')]

    name = fields.Char(required=True)

    version = fields.Selection(selection='select_versions',
                               required=True, default='0.1')

    input_path = fields.Char('Transport Input Path')
    output_path = fields.Char('Transport Output Path')
    file_regex = fields.Char('Transport File filter', default='.*')
    remove_remote_files = fields.Boolean(
        'Remove Remote Files, if already on system', default=False)

    output_for_debug = fields.Text(readonly=True, default='')
    file_ids = fields.One2many('stock_connector.file', 'backend_id',
                               'Files', readonly=True)
    file_count = fields.Char(compute='_get_file_count', store=False)

    binding_ids = fields.One2many('stock_connector.binding',
                                  'backend_id')

    transport_id = fields.Many2one('stock_connector.transport', 'Transport',
                                   required=False)

    action_rule_ids = fields.One2many(
        'base.action.rule', string='Automated Actions',
        compute='compute_action_rule_ids'
    )

    date_last_backend_sync = fields.Datetime(
        readonly=False, required=True, default=fields.Datetime.now())
    date_last_file_process = fields.Datetime(
        readonly=False, required=True, default=fields.Datetime.now())
    date_last_event_process = fields.Datetime(
        readonly=False, required=True, default=fields.Datetime.now())
    date_action_last = fields.Datetime(
        string="Last automated action",
        readonly=False, required=False)

    @api.one
    def compute_action_rule_ids(self):
        models = self.env['ir.model'].search([
            ('name', 'in', [
                'stock_connector.backend',
                'stock_connector.event',
                'stock_connector.file',
            ])]
        )
        self.action_rule_ids = self.env['base.action.rule'].search([
            ('model_id', 'in', models.ids),
            '|',
            ('active', '=', True),
            ('active', '=', False),
        ])
        _logger.info(self.action_rule_ids.mapped('name'))

    @api.one
    def _get_file_count(self):
        file_count_in = 0
        file_count_out = 0
        file_count = 0
        errors = False
        for file_ in self.file_ids:
            file_count += 1
            if file_.state == 'error':
                errors = True
            if file_.state == 'ready':
                if file_.transmit == 'in':
                    file_count_in += 1
                elif file_.transmit == 'out':
                    file_count_out += 1
        if file_count_in > 0 or file_count_out > 0:
            file_count = '%s / %s / %s' % (file_count_in,
                                           file_count,
                                           file_count_out)
        if errors:
            file_count = '%s !' % file_count
        self.file_count = file_count

    @api.multi
    def open_files(self):
        """
        This method is called from the interface when pressing
         the top-right side button.
        """
        self.ensure_one()
        kanban_view_id = self.env.ref('stock_connector.'
                                      'stock_connector_file_view_kanban').id
        tree_view_id = self.env.ref('stock_connector.'
                                    'stock_connector_file_view_tree').id
        form_view_id = self.env.ref('stock_connector.'
                                    'stock_connector_file_view_form').id
        return {
            'name': 'Files',
            'type': 'ir.actions.act_window',
            'res_model': 'stock_connector.file',
            'views': [[kanban_view_id, 'kanban'],
                      [tree_view_id, 'tree'],
                      [form_view_id, 'form']
                      ],
            'domain': [('id', 'in', self.file_ids.ids)],
            'context': {
                'default_backend_id': self.id,
            },
        }

    @api.multi
    def get_processor(self, model=None):
        self.ensure_one()
        if model is None:
            model = self
        backend = self.get_backend()
        session = ConnectorSession.from_env(self.env)
        processor_class = backend.get_class(ConnectorUnit, session, model)
        environment = ConnectorEnvironment(self, session, model)
        return processor_class(environment)

    @api.multi
    def notify_new_event(self, event):
        """
        This method gets notified of new events pending events
        """
        return self.get_processor('stock_connector.backend')\
                   .notify_new_event(event) or True

    @api.multi
    def process_event(self, event):
        """
        This method gets notified of new events pending events
        """
        self.date_last_event_process = fields.Datetime.now()
        return self.get_processor('stock_connector.event')\
            .process_event(event) or True

    @api.multi
    def process_events(self, auto=False):
        """
        This method processes pending events
        """
        self.date_last_event_process = fields.Datetime.now()
        if not auto:
            self.output_for_debug = ''
        return self.get_processor('stock_connector.event')\
                   .process_events() or True

    @api.multi
    def synchronize_backend(self, auto=False):
        """
        This method synchronizes the warehouse and the external warehouse
        """
        self.ensure_one()
        self.date_last_backend_sync = fields.Datetime.now()
        if not auto:
            self.output_for_debug = ''
        try:
            return self.get_processor().synchronize() or True
        except:
            _logger.error(self.output_for_debug)
            raise

    @api.multi
    def find_binding(self, binding, group):
        self.ensure_one()
        return self.env['stock_connector.binding'].search([
            ('group', '=', group),
            ('binding', '=', binding),
            ('backend_id', '=', self.id)
        ], limit=1)

    @api.multi
    def get_binding(self, record, group, missing=None):
        self.ensure_one()
        if isinstance(record, tuple):
            res_model = record[0]
            res_id = record[1]
        else:
            res_model = record._name
            res_id = record.id
        domain = [
            ('backend_id', '=', self.id),
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
            ('group', '=', group or res_model),
        ]
        res = self.env['stock_connector.binding'].search(domain)
        if res:
            return res[0].binding
        elif missing is None:
            return None

        value = missing(record) if callable(missing) else missing
        if value:
            vals = {
                'backend_id': self.id,
                'res_model': res_model,
                'res_id': res_id,
                'binding': value,
                'group': group or False,
            }
            self.env['stock_connector.binding'].create(vals)
        return value or None

    @api.multi
    def test_connection(self):
        self.ensure_one()
        self.output_for_debug = ''
        try:
            return self.get_processor().test_connection() or True
        except Exception as e:
            _logger.error(str(e))
            _logger.error(self.output_for_debug)
            raise

    @api.multi
    def synchronize_files(self, auto=False):
        self.ensure_one()
        self.date_last_file_process = fields.Datetime.now()
        if not auto:
            self.output_for_debug = ''
        try:
            return self.get_processor().synchronize_files() or True
        except Exception as e:
            _logger.error(str(e))
            _logger.error(self.output_for_debug)
            raise

    @api.multi
    def automatize(self):
        self.ensure_one()
        methods = [
            'process_events',
            'synchronize_backend',
            'synchronize_files',
        ]
        for method_name in methods:
            savepoint_name = "stock_connector_backend_automatize_%s_%s" % (
                self.id, method_name)
            try:
                self.env.cr.execute(SQL_SAVEPOINT % savepoint_name)
                with api.Environment.manage():
                    method = getattr(self, method_name)
                    method(auto=True)
            except Exception as e:
                _logger.error('%s: %s' % (method_name, str(e)))
                self.env.cr.execute(SQL_ROLLBACK % savepoint_name)
                self.env.invalidate_all()
            else:
                self.env.cr.execute(SQL_RELEASE % savepoint_name)
