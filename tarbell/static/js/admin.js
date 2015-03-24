// required jquery, json2

//
// extend jquery
//

(function($) {

$.fn.extend({
    // enable UI element
    enable: function() {
        return this.removeAttr('disabled');
    },
    // disable UI element
    disable: function() {
        return this.attr('disabled', 'disabled'); 
    }
});

})(jQuery);


//
// templates
//

var _config_s3_bucket_template = _.template($('#config_s3_bucket_template').html());
var _select_bucket_template = _.template($('#select_bucket_template').html());
var _select_blueprint_template = _.template($('#select_blueprint_template').html());
var _error_alert_template = _.template($('#error_alert_template').html());
var _success_alert_template = _.template($('#success_alert_template').html());
var _blueprint_template = _.template($('#blueprint_template').html());
var _project_template = _.template($('#project_template').html());
var _detail_s3_bucket_template = _.template($('#detail_s3_bucket_template').html());

//
// generic modal event handlers
//

modal_error_show = function(event, msg) {
    $(this).find('.modal-error .modal-msg').html(msg);
    $(this).find('.modal-error').show();    
};
modal_error_hide = function(event, msg) {
    $(this).find('.modal-error .modal-msg').html('');
    $(this).find('.modal-error').hide();         
};

modal_success_show = function(event, msg) {
    if(msg) {
        $(this).find('.modal-success .modal-msg').html(msg);
    }
    $(this).find('.modal-success').show();    
};

modal_success_hide = function(event) {
    $(this).find('.modal-success').hide();         
};

modal_progress_show = function(event, msg) {
    $(this).find('.modal-progress .modal-msg').html(msg);
    $(this).find('.modal-progress').show();    
};

modal_progress_hide = function(event) {
    $(this).find('.modal-progress').hide(); 
};

modal_confirm_show = function(event, msg, callback) { 
    console.log('modal_confirm_show');
       
    var $panel = $(this).find('.modal-confirm');
    console.log(callback);
    
    $panel.find('.modal-msg').html(msg);
    
    $panel.find('.btn').bind('click.confirm', function(event) {
        $(this).unbind('click.confirm'); 
        $panel.hide();         
        callback($(this).hasClass('btn-primary'));
    });
    
    $panel.show();    
};

modal_confirm_hide = function(event) {
    $(this).find('.modal-confirm').hide(); 
};

function modal_init($modal) {
    return $modal
        .on('error_show', modal_error_show)
        .on('error_hide', modal_error_hide)
        .on('success_show', modal_success_show)
        .on('success_hide', modal_success_hide)
        .on('progress_show', modal_progress_show)
        .on('progress_hide', modal_progress_hide)
        .on('confirm_show', modal_confirm_show)
        .on('confirm_hide', modal_confirm_hide);
}


//
// debug
//

function debug() {
    if(console && console.log) {
        // converts arguments to real array
        var args = Array.prototype.slice.call(arguments);
        args.unshift('**');
        console.log.apply(console, args); // call the function
    }
}

//
// alerts
//

function alert_hide() {
    $('div.tab-pane').find('div[role="alert"]').remove(); // all
}

function error_hide() {
    $('div.tab-pane').find('div[role="alert"].alert-danger').remove();   
}

function error_alert(message) {
    error_hide();
    $('div.tab-pane.active').prepend(_error_alert_template({message: message}));    
}

function success_hide() {
    $('div.tab-pane').find('div[role="alert"].alert-success').remove();   
}

function success_alert(message) {
    success_hide();
    $('div.tab-pane.active').prepend(_success_alert_template({message: message}));    
}

//
// progress
//

function progress_show(msg) {
    $('#progress_modal .modal-msg').html(msg);
    $('#progress_modal').modal('show');
}

function progress_hide() {
    $('#progress_modal').modal('hide');
}

//
// ajax
//

function _ajax(url, type, data, on_error, on_success, on_complete) {
    var _error = '';
    
    debug('ajax params', data);
    
    $.ajax({
        url: url,
        type: type,
        data: data,
        dataType: 'json',
        timeout: 45000, // ms
        error: function(xhr, status, err) { 
            _error = err || status;
            debug('ajax error', _error);           
            on_error(_error);
        },
        success: function(data) {
            debug('ajax data', data);
            if(data.error) {
                _error = data.error;
                on_error(_error);
            } else if (on_success) {
                on_success(data);
            }
        },
        complete: function() {
            if(on_complete) {
                on_complete(_error);
            }
        }
    });
}

function ajax_get(url, data, on_error, on_success, on_complete) {
    _ajax(url, 'GET', data, on_error, on_success, on_complete);
}

function ajax_post(url, data, on_error, on_success, on_complete) {
    _ajax(url, 'POST', data, on_error, on_success, on_complete);
}

//
// config
//

function config_dirty() {
    $('#config_save').enable();
}

function disable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').disable();
    $group.find('.remove-bucket').hide();
    $group.find('.add-bucket').show();
    config_dirty();
}

function enable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').enable();
    $group.find('.add-bucket').hide();
    $group.find('.remove-bucket').show();
}

function remove_bucket(target) {
    $(target).closest('.form-group').remove();
}


$(function() {

    //
    // Clear alerts/states when switching from tab to tab
    //
    $('a[data-toggle="tab"]').on('hide.bs.tab', function(event) {      
        alert_hide();
        $('.form-group, .input-group').removeClass('has-error');        
        $('#blueprint_url, #project_url').val('');
    });
     
// ------------------------------------------------------------
// configuration tab
// ------------------------------------------------------------
     
    $('#configuration_tab input').change(config_dirty);
        
    $('#config_add_bucket').click(function(event) {
        var $group = $(this).closest('.form-group');
        $(_config_s3_bucket_template())
            .insertAfter($group)
            .find('input')
                .change(config_dirty);
    });
             
      
    $('#config_save').click(function(event) {
         progress_show('Saving configuration');
         
         ajax_get('/configuration/save/', {},// TODO: add data
            function(error) {
                error_alert(error);
            },
            function(data) {
                // TODO: update cached config
            },
            function() {
                progress_hide();
            });
    });
 
// ------------------------------------------------------------
// blueprints
// ------------------------------------------------------------
  
    $('#blueprint_install').click(function(event) {
        alert_hide();
        
        var url = $('#blueprint_url').val().trim();
        if(!url) {
            $(this).closest('.input-group').addClass('has-error');
            return;
        }
        
        $(this).closest('.input-group').removeClass('has-error');           
        progress_show('Installing blueprint'); 
             
        ajax_get('/blueprint/install/', {url: url},
            function(error) {
                error_alert(error);
            },
            function(data) {
                // Add to cached config!
                _config['project_templates'].push(data);
                
                $('#blueprints_table tbody').append(_blueprint_template(data));
                $('#blueprint_url').val('');
                success_alert('Successfully installed blueprint <strong>'+data.name+'</strong>');                               
            },
            function() {
                progress_hide();
            });
    });
    
// ------------------------------------------------------------
// projects tab
// ------------------------------------------------------------

    $('#project_install').click(function(event) {
        alert_hide();

        var url = $('#project_url').val().trim();
        if(!url) {
            $(this).closest('.input-group').addClass('has-error');
            return;
        }
        
        $(this).closest('.input-group').removeClass('has-error');
        progress_show('Installing project'); 
             
        ajax_get('/project/install/', {url: url},
            function(error) {
                error_alert(error);
            },
            function(data) {
                $('#projects_table tbody').append(_project_template(data));
                $('#project_url').val('');
                success_alert('Successfully installed project <strong>'+data.title+'</strong>');                               
            },
            function() {
                progress_hide();
            });
    });

    $('.project-update').click(function(event) {
        alert_hide();
        
        var project = $(this).closest('tr').attr('data-project');
        console.log('project', $(this).closest('tr'));

        progress_show('Updating project blueprint'); 

        ajax_get('/project/update/', {project: project},
            function(error) {
                error_alert(error);
            },
            function(data) {
                success_alert('Updated <strong>'+project+'</strong> blueprint ('+data.msg+')');                               
            },
            function() {
                progress_hide();
            });
    });
 
   
// ------------------------------------------------------------
// newproject modal
// ------------------------------------------------------------
    
    $('#newproject_name, #newproject_title').change(function(event) {
        if($('#newproject_name').val().trim() 
        && $('#newproject_title').val().trim()) {
            $('#newproject_button').enable(); 
        } else {
            $('#newproject_button').disable();                
        }    
    });
  
    $('#newproject_button').click(function(event) {
        var $modal = $('#newproject_modal')
            .trigger('error_hide')
            .trigger('progress_show', 'Creating project');
        
        var emails = $("#newproject_spreadsheet").is(':checked') ? 
            $('#newproject_spreadsheet_emails').val().trim() : '';
        
        ajax_get('/project/create/', {  
                name: $('#newproject_name').val().trim(),
                title: $('#newproject_title').val().trim(),
                blueprint: $('#newproject_blueprint').val(),
                spreadsheet_emails: emails
            },
            function(error) {
                $modal.trigger('error_show', error);
            },
            function(data) {
                $('#projects_table tbody').append(_project_template(data));
                success_alert('Successfully created project <strong>'+data.title+'</strong>');   
                $modal.modal('hide');                           
            },
            function() {
                $modal.trigger('progress_hide');
            });            
    });
    
    modal_init($('#newproject_modal'))
        .on('show.bs.modal', function(event) {
            $(this)
                .trigger('error_hide')
                .trigger('progress_hide');
            
            $('#newproject_name, #newproject_title').val('');
            
            var html = '';
            for(var i = 0; i < _config.project_templates.length; i++) {
                html += _select_blueprint_template({
                    value: i+1,
                    name: _config.project_templates[i].name
                });
            }
            $('#newproject_blueprint').html(html).val(1);
 
            $("#newproject_spreadsheet").prop('checked', false);
            $('#newproject_emails').removeClass('in');  
            $('#newproject_spreadsheet_emails').val(_config.google_account)
                
            $('#newproject_create_button').disable(); 
        });  

// ------------------------------------------------------------
// common modal
// ------------------------------------------------------------
    
    $('#run_modal, #detail_modal, #generate_modal, #publish_modal')
        .on('show.bs.modal', function(event) {
            var directory = $(event.relatedTarget).closest('tr').attr('data-project');
            $(this).data('data-project', directory);      
            $('.project-name').html(directory);
        });


// ------------------------------------------------------------
// detail modal
// ------------------------------------------------------------

    $('#detail_button').click(function(event) {
        var $modal = $('#detail_modal');
        var project = $modal.data('data-project');
                
        var title = $('#detail_title').val().trim();
        if(!title) {
            $modal.trigger('error_show', 'You must enter a title');
            return;
        }

        var error = '';
        var s3_buckets = [];
        $('#detail_bucket_form .form-group').each(function(i, el) {
            var $el = $(el);
            var name = $el.find('.bucket-name').val().trim();
            var url = $el.find('.bucket-url').val().trim();
            
            if((name || url) && !(name && url)) {
                error = 'You specify a name and URL for each bucket';
                return;
            }           
            s3_buckets.push({name: name, url: url});
        });
        if(error) {
            $modal.trigger('error_show', error);
            return false;       
        }             
        
        
        ajax_get('/project/config/save/', {
                project: project,
                title: title,
                context_source_file: $('#detail_context_source_file').val().trim(),
                spreadsheet_key: $('#detail_spreadsheet_key').val().trim(),
                spreadsheet_cache_ttl: $('#detail_spreadsheet_cache_ttl').val().trim(),
                create_json: $("#detail_create_json").prop('checked'),
                excludes: $('#detail_excludes').val().trim(),
                s3_buckets: JSON.stringify(s3_buckets)
            },
            function(error) {
                $modal.trigger('error_show', error);
            },
            function(data) {
                // doit
            },
            function() {
                $modal.trigger('progress_hide');
            });
    });

    $('#detail_add_bucket').click(function(event) {   
        $('#detail_bucket_form').prepend(_detail_s3_bucket_template());
    });


    modal_init($('#detail_modal'))
        .on('init', function(event, config) {            
            $('#detail_title').val((config.DEFAULT_CONTEXT || {}).title);
            $('#detail_context_source_file').val(config.CONTEXT_SOURCE_FILE || '');
            
            $('#detail_spreadsheet_key').val(config.SPREADSHEET_KEY || '');
            $('#details_spreadsheet_cache_ttl').val(config.SPREADSHEET_CACHE_TTL || '');        
            $("#detail_create_json").prop('checked', config.CREATE_JSON);

            $('#detail_excludes').val((config.EXCLUDES || []).join(','));
            
            var html = '';
            for(var name in (config.S3_BUCKETS || {})) {
                html += _detail_s3_bucket_template({
                        name: name, url: config.S3_BUCKETS[name]
                });
            }
            $('#detail_bucket_form').html(html);
        })
        .on('details', function(event) {           
            var $modal = $(this)
                .trigger('progress_show', 'Loading project details');

            var project = $modal.data('data-project');
               
            ajax_get('/project/config/', {project: project},
                function(error) {
                    $modal.trigger('error_show', error);
                },
                function(data) {
                    $modal.trigger('init', data);
                },
                function() {
                    $modal.trigger('progress_hide');
                });
        })
        .on('show.bs.modal', function(event) {
            $(this)
                .trigger('error_hide')
                .trigger('success_hide')
                .trigger('progress_hide')
                .trigger('init', {})
                .trigger('details'); 
            
            console.log('show.bs.modal', $(this).data('data-project'));
        })
 
// ------------------------------------------------------------
// generate modal
// ------------------------------------------------------------
   
    $('#generate_button').click(function(event) {
        var $modal = $('#generate_modal')
            .trigger('error_hide').trigger('success_hide');
            
        var project = $modal.data('data-project');
        var path = $('#generate_path').val().trim();
        
        if(path) {
            ajax_get('/exists/', {path: path},
                function(error) {
                    $modal.trigger('error_show', error);    
                },
                function(data) {
                    if(data.exists) {
                        $modal.trigger('confirm_show', ['Overwrite existing directory?', 
                            function(yes) {
                                if(yes) {
                                    $modal.trigger('generate', [project, path]);  
                                }
                            }
                        ]);
                    } else {
                        $modal.trigger('generate', [project, path]);
                    }
                });
        } else {
            $modal.trigger('generate', [project, path]);        
        }
    });
      
    modal_init($('#generate_modal'))
        .on('show.bs.modal', function(event) {
            $(this)
                .trigger('error_hide')
                .trigger('success_hide')
                .trigger('progress_hide');                           
            $('#generate_path').val('').focus();
        })
        .on('generate', function(event, project, path) {
            var $modal = $(this).trigger('progress_show', 'Generating project');
            
            ajax_get('/project/generate/', {
                    project: project,
                    path: path
                },
                function(error) {
                    $modal.trigger('error_show', error);
                },
                function(data) {
                    $modal.trigger('success_show', 'Static files generated in '+data.path);
                },
                function() {
                    $modal.trigger('progress_hide');
                });
        });
    
// ------------------------------------------------------------
// publish modal
// ------------------------------------------------------------

    $('#publish_button').click(function(event) {   
        var $modal = $('#publish_modal')
            .trigger('error_hide')
            .trigger('progress_show', 'Publishing project');
        
        var project = $modal.data('data-project');
        var bucket = $('#publish_bucket').val();
        
        ajax_get('/project/publish/', {
                project: project,
                bucket: bucket
            },
            function(error) {
                $modal.trigger('error_show', error);
            },
            function(data) {
                // TODO 
            },
            function() {
                $modal.trigger('progress_hide');
            });
    });
 
    modal_init($('#publish_modal'))
        .on('show.bs.modal', function(event) {
            $(this).trigger('error_hide').trigger('progress_hide');

            var html = '';
            for(key in _config.default_s3_buckets) {
                html += _select_bucket_template({
                    name: key, 
                    bucket: _config.default_s3_buckets[key]
                });
            }
            $('#publish_bucket').html(html).val('staging');
        });
    
// ------------------------------------------------------------
// run modal
// ------------------------------------------------------------

    modal_init($('#run_modal'))
        .on('reset', function(event) {
            $('#run_address').closest('.form-group').removeClass('has-error');
            
            $('#run_stop_button').disable();
            $('#run_address, #run_done_button, #run_button').enable();   
        })
        .on('show.bs.modal', function(event) {
            $(this)
                .trigger('error_hide')
                .trigger('progress_hide')
                .trigger('reset');
            $('#run_address').val('127.0.0.1:5000')
                .closest('.form-group').removeClass('has-error');
         });      
        
    $('#run_button').click(function(event) {
        var $modal = $('#run_modal').trigger('error_hide');
        var project = $modal.data('data-project');
               
        var $address = $('#run_address');
        var address = $address.val().trim();
        if(!address) {
            $address.focus().closest('.form-group').addClass('has-error');
            return;
        }
               
        $address.closest('.form-group').removeClass('has-error');
        $modal.trigger('progress_show', 'Starting preview server');
        
        ajax_get('/project/run/', {
                project: project,
                address: address
            }, 
            function(error) {
                $modal.trigger('error_show', error);
            },
            function(data) {
                window.open('http://'+address);
                
                $('#run_address, #run_done_button, #run_button').disable();
                $('#run_stop_button').enable();
            },
            function() {
                $modal.trigger('progress_hide');
            }
        );
    });
    
    $('#run_stop_button').click(function(event) {
        ajax_get('/project/stop/', {}, 
            function(error) {
                $modal.trigger('error_show', error);
            },
            function(data) {
                $('#run_modal').trigger('reset');
            }
        );
    });
        
     
});