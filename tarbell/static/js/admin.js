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

var _s3_bucket_template = _.template($('#s3_bucket_template').html());
var _select_bucket_template = _.template($('#select_bucket_template').html());
var _error_alert_template = _.template($('#error_alert_template').html());
var _success_alert_template = _.template($('#success_alert_template').html());
var _blueprint_template = _.template($('#blueprint_template').html());

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
    
    $.ajax({
        url: url,
        type: type,
        data: data,
        dataType: 'json',
        timeout: 45000, // ms
        error: function(xhr, status, err) { 
            _error = err || status;
            debug('ajax error', _error)           
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

function config_disable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').disable();
    $group.find('.config-remove-bucket').hide();
    $group.find('.config-add-bucket').show();
    config_dirty();
}

function config_enable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').enable();
    $group.find('.config-add-bucket').hide();
    $group.find('.config-remove-bucket').show();
}

function config_remove_bucket(target) {
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
        $(_s3_bucket_template())
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
        var url = $('#project_url').val().trim();
        if(!url) {
            $(this).closest('.input-group').addClass('has-error');
            return;
        }
        
        $(this).closest('.input-group').removeClass('has-error');
        progress_show('Installing project'); 
             
        ajax_get('/project/install', {url: url},
            function(error) {
                error_alert(error);
            },
            function(data) {
                console.log(data);
            },
            function() {
                progress_hide();
            });
    });

    $('.project-details').click(function(event) {
        error_alert('not implemented');
    });
    
    $('.project-update').click(function(event) {
        error_alert('not implemented');
    });
    
// ------------------------------------------------------------
// newproject modal
// ------------------------------------------------------------

    $('#newproject_back_button').click(function(event) {
        var $cur_pane = $('#newproject_modal .modal-body > div').filter(':visible');
        var $prev_pane = $cur_pane.prev();
        
        if($prev_pane.length) {
            $cur_pane.hide();
            $prev_pane.show();
            
            $('#newproject_next_button').enable();
            $('#newproject_create_button').disable();
            
            if($prev_pane.prev().length) {
                $('#newproject_back_button').enable(); 
            } else {
                $('#newproject_back_button').disable(); 
            }
        }
    });
       
    $('#newproject_next_button').click(function(event) {
        var $cur_pane = $('#newproject_modal .modal-body > div').filter(':visible');        
        var $next_pane = $cur_pane.next();
         
        if($next_pane.length) {
            $cur_pane.hide();
            $next_pane.show();
            $('#newproject_back_button').enable();
           
            if($next_pane.next().length) {
                $('#newproject_next_button').enable();
                $('#newproject_create_button').disable();  
            } else {
                $('#newproject_next_button').disable();  
                $('#newproject_create_button').enable();
            }
        }       
    });
    
    $("#newproject_info_pane input[type='text']").change(function(event) {
        console.log('change');
        
        if($('#newproject_info_name').val().trim()
        && $('#newproject_info_title').val().trim()) {
            $('#newproject_next_button').enable();          
        } else {
            $('#newproject_next_button').disable();        
        }  
    });
    
    $("input[name='newproject_spreadsheet']").click(function(event) {
        if($(this).val()) {
            $('#newproject_spreadsheet_details').show();
        } else {
            $('#newproject_spreadsheet_details').hide();
        }
    });

    $("input[name='newproject_repo']").click(function(event) {
        if($(this).val()) {
            $('#newproject_repo_details').show();
        } else {
            $('#newproject_repo_details').hide();
        }
    });
    
    modal_init($('#newproject_modal'))
        .on('show.bs.modal', function(event) {
            $(this).trigger('error_hide').trigger('progress_hide');
            
            $('#newproject_info_name, #newproject_info_title').val('');
 
            $("input[name='newproject_spreadsheet'][value='']").prop('checked', true);
            $('#newproject_spreadsheet_details').hide();
            $('#newproject_spreadsheet_emails').val(config.google_account);
        
            $("input[name='newproject_repo'][value='']").prop('checked', true);
            $('#newproject_repo_details').hide();
            $('#newproject_repo_username, #newproject_repo_password').val('');
        
            $('#newproject_modal .modal-body > div').hide();
            $('#newproject_info_pane').show();   
        
            $('#newproject_back_button, #newproject_next_button, #newproject_create_button')
                .disable(); 
        });  
 
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
        
        ajax_get('/project/publish/', {},
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
            for(key in config.default_s3_buckets) {
                html += _select_bucket_template({
                    name: key, 
                    bucket: config.default_s3_buckets[key]
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
        
    //
    // Common
    //
    
    $('#run_modal, #generate_modal, #publish_modal').on('show.bs.modal', function(event) {
        var directory = $(event.relatedTarget).closest('tr').attr('data-project');
        $(this).data('data-project', directory);      
        $('.project-name').html(directory);
    });
    
});