
openerp.export_to_xml = function(session) {
    var _t = session.web._t;
    var has_action_id = false;

    function launch_wizard(self, view, invite) {
        var action = view.getParent().action;
        
        var Export = new session.web.DataSet(self, 'export.wizard', view.dataset.get_context());
        var domain = new session.web.CompoundDomain(view.dataset.domain);
        var get_selected_ids = self.getParent().get_selected_ids();
        
        if (view.fields_view.type == 'form') rec_name = view.datarecord.name;
        else rec_name = '';
        session.web.pyeval.eval_domains_and_contexts({
            domains: [domain],
            contexts: [Export.get_context()]
        }).done(function (result) {
        	
            Export.create({
                name: action.name,
                record_name: rec_name,
                get_selected_ids: get_selected_ids ,
                action_id: action.id,
                view_type: view.fields_view.type,
                invite: invite || false,
                context:self.context
            }).done(function(share_id) {
                var step1 = Export.call('go_step_1', [[share_id], Export.get_context()]).done(function(result) {
                    var action = result;
                    self.do_action(action);
                });
            });
        });
    }

    function has_share(yes, no) {
        if (!session.session.share_flag) {
            session.session.share_flag = $.Deferred(function() {
            	session.session.share_flag.resolve();
            });
        }
        session.session.share_flag.done(yes).fail(no);
    }

    /* Extend the Sidebar to add Export XML Embed link in the 'More' menu */
    session.web.Sidebar = session.web.Sidebar.extend({

        start: function() {
            var self = this;
            this._super(this);
            has_share(function() {
                self.add_items('other', [
                    {   label: _t('From / TO XML'),
                        callback: self.on_click_share,
                        classname: 'oe_share' },
                ]);
            });
        },

        on_click_share: function(item) {
            var view = this.getParent()
            launch_wizard(this, view, false);
        },

       
    });

   
};

