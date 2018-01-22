# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from osv import fields, osv
from openerp.tools.translate import _
from openerp.osv import expression
from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')


class workflow_update(osv.osv):
    _name = 'workflow_update'
    _description = 'Workflow update'

    _columns = {
        'name': fields.text('Name'),
        'workflow_id': fields.many2one('workflow', 'Workflow', required=True),
        'workflow_row_update_ids': fields.one2many('bt_helper.workflow_row_update', 'workflow_update_id',
                                                   'Row to update'),
        'conditions': fields.text('Conditions', help="Conditions"),
        'id_to_check': fields.integer('Id to search', help="To check the stage value of the given id")
    }

    _defaults = {
        'conditions': '',
    }

    def do_give_activity_name(self, cr, uid, ids, context={}):
        os_object = self.browse(cr, uid, ids[0], context)
        workflow_id_class_obj = self.pool.get(os_object.workflow_id.osv)
        workflow_instance_obj = self.pool.get('workflow.instance')
        workflow_workitem_obj = self.pool.get('workflow.workitem')
        workflow_activity_obj = self.pool.get('workflow.activity')

        if not os_object.id_to_check or not os_object.workflow_id:
            raise osv.except_osv(_('Some fields are missing!'), _('Add missing information to perform this operation: workflow and id'))

        workflow_id_object = workflow_id_class_obj.search(cr, uid, [('id', '=', os_object.id_to_check)])
        if not workflow_id_object:
            raise osv.except_osv(_('Missing object!'), _('In {0} there is not object with id {1}'.format(os_object.workflow_id.osv, os_object.id_to_check)))

        wkf_instance_id = workflow_instance_obj.search(cr, uid, [('wkf_id', '=', os_object.workflow_id.id), ('res_id', '=', os_object.id_to_check)])

        if len(wkf_instance_id) == 0:
            raise osv.except_osv(_('Missing instance!'), _('In {0} there is not instance for id {1}'.format(os_object.workflow_id.osv, os_object.id_to_check)))
        elif len(wkf_instance_id) > 1:
            raise osv.except_osv(_('Many instances!'), _('In {0} there is many instances for the id {1}'.format(os_object.workflow_id.osv, os_object.id_to_check)))
        else:
            wkf_instance_state = workflow_instance_obj.browse(cr, uid, wkf_instance_id[0]).state
            work_item_id = workflow_workitem_obj.search(cr, uid, [('inst_id', 'in', wkf_instance_id)])

            if not work_item_id:
                raise osv.except_osv(_('Missing work item!'), _('In {0} there is not any work item for the id {1}'.format(os_object.workflow_id.osv, os_object.id_to_check)))
            work_item = workflow_workitem_obj.browse(cr, uid, work_item_id[0])
            work_item_state = work_item.state
            activity = workflow_activity_obj.browse(cr, uid, [work_item.act_id.id])
            if not activity:
                raise osv.except_osv(_('Missing activity!'), _('In {0} there is not activity for the id {1}'.format(os_object.workflow_id.osv, os_object.id_to_check)))
            activity = activity[0]
            logger.debug('The instance {0}  :: workitem {1} :: activity {2}'.format(wkf_instance_state, work_item_state, activity.name))
            raise osv.except_osv(_('State!'), _('Activity {0}'.format(activity.name)))

    def do_update_workflow(self, cr, uid, ids, context={}):
        """
        Generic function to update workflows
        """
        logger.info("Updating Workflow")
        # #
        # # Choose the workflow
        # #
        logger.info(" 1.- Check if the workflow exists")
        os_object = self.browse(cr, uid, ids[0], context)
        workflow_id = os_object.workflow_id.id

        workflow_workitem_obj = self.pool.get('workflow.workitem')
        workflow_instance_obj = self.pool.get('workflow.instance')
        workflow_id_class_obj = self.pool.get(os_object.workflow_id.osv)

        if not os_object.workflow_id:
            raise osv.except_osv(_('Workflow name!'), _('There is not any workflow with this name'))
        # #
        # #   Pairs state of the object <--> state of the workflow
        # #

        logger.info(" 2.- To define the relationship among states and workflow states")
        conditions = expression.normalize_domain(eval(os_object.conditions, {}))
        workflow_id_class_ids = workflow_id_class_obj.search(cr, uid, conditions)

        for workflow_row_update in os_object.workflow_row_update_ids:
            logger.info(" a)  Check if exists the activity")
            status = workflow_row_update.status
            activity_id = workflow_row_update.activity_id.id
            logger.info(" b)  For each element with state = {0}".format(workflow_row_update.state))
            cond = ['&', ('state', '=', workflow_row_update.state), ('id', 'in', workflow_id_class_ids)]
            logger.debug("Cond {0}".format(cond))

            for var_id in workflow_id_class_obj.search(cr, uid, cond):

                wkf_instance_ids = workflow_instance_obj.search(cr, uid, [('wkf_id', '=', workflow_id), ('res_id', '=', var_id)])

                if len(wkf_instance_ids) == 0:
                    # #
                    # # If there is not any instance in this state then. create it
                    wkf_instance_id = int(workflow_instance_obj.create(cr, uid, {'wkf_id': workflow_id,
                                                                                 'res_id': var_id,
                                                                                 'res_type': os_object.workflow_id.name,
                                                                                 'uid': uid
                                                                                        }))
                    logger.info("Creating wkf_instance {0}".format(wkf_instance_id))
                    workflow_workitem_obj.create(cr, uid, {'act_id': activity_id,
                                                            'inst_id': wkf_instance_id,
                                                            'state': status})
                else:
                    workflow_instance_obj.write(cr, uid, wkf_instance_ids, {'state': status}, context)
                    work_item_id = workflow_workitem_obj.search(cr, uid, [('inst_id', 'in', wkf_instance_ids)])

                    if len(work_item_id) == 0:
                        for wkf_instance_id in wkf_instance_ids:
                            work_item_id = workflow_workitem_obj.create(cr, uid, {'act_id': activity_id,
                                                                                  'inst_id': wkf_instance_id,
                                                                                  'state': status
                                                                                  })
                        logger.info("Creating work item {0} ## activity {1} ".format(work_item_id, {'act_id': activity_id}))
                    else:
                        logger.info("Updating in {0} ## activity {1} ".format(work_item_id, {'act_id': activity_id}))
                        workflow_workitem_obj.write(cr, uid, work_item_id, {'act_id': activity_id,
                                                                            'state': status}, context)
        return True


class workflow_row_update(osv.osv):
    _name = 'bt_helper.workflow_row_update'
    _description = 'Workflow row update'

    _columns = {
        'workflow_update_id': fields.many2one('workflow_update', 'Associated Workflow'),
        'workflow_id': fields.related('workflow_update_id', 'workflow_id', type="many2one", relation="workflow"),
        'state': fields.text('State', required=True),
        'activity_id': fields.many2one('workflow.activity', 'Workflow Atvitiy', required=True),
        'status': fields.selection([('active', 'Active'), ('complete', 'Complete')], 'Status', required=True),
    }

    _defaults = {
        'status': 'active',
    }
