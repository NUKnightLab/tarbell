//
// templates
//

var _s3_bucket_template = _.template($('#s3_bucket_template').html());
var _select_bucket_template = _.template($('#select_bucket_template').html());
var _error_alert_template = _.template($('#error_alert_template').html());

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

modal_progress_show = function(event, msg) {
    $(this).find('.modal-progress .modal-msg').html(msg);
    $(this).find('.modal-progress').show();    
};

modal_progress_hide = function(event) {
    $(this).find('.modal-progress').hide(); 
};

function modal_init($modal) {
    return $modal
        .on('error_show', modal_error_show)
        .on('error_hide', modal_error_hide)
        .on('progress_show', modal_progress_show)
        .on('progress_hide', modal_progress_hide);
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
// error
//

function error_hide() {
    var $tab = $('div.tab-pane').find('div[role="alert"]').remove();   
}

function error_alert(message) {
    error_hide();
    $('div.tab-pane.active').prepend(_error_alert_template({message: message}));    
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
// modals
//

function progress_show(msg) {
    $('#progress_modal .modal-msg').html(msg);
    $('#progress_modal').modal('show');
}

function progress_hide() {
    $('#progress_modal').modal('hide');
}


//
// config
//

function config_dirty() {
    $('#config_save').removeAttr('disabled');
}

function config_disable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').attr('disabled', 'disabled');
    $group.find('.config-remove-bucket').hide();
    $group.find('.config-add-bucket').show();
    config_dirty();
}

function config_enable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').removeAttr('disabled');
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
        error_hide();
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
        // TODO: save configuration
    });
 
// ------------------------------------------------------------
// blueprints
// ------------------------------------------------------------
  
    $('#blueprint_install').click(function(event) {
        var url = $('#blueprint_url').val().trim();
        if(!url) {
            $(this).closest('.input-group').addClass('has-error');
            return;
        }
        
        $(this).closest('.input-group').removeClass('has-error');        
        progress_show('Installing blueprint'); 
             
        ajax_get('/blueprint/install', {url: url},
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
            $('#newproject_next_button').removeAttr('disabled');
            $('#newproject_create_button').attr('disabled', 'disabled'); 
            
            if($prev_pane.prev().length) {
                $('#newproject_back_button').removeAttr('disabled');  
            } else {
                $('#newproject_back_button').attr('disabled', 'disabled');  
            }
        }
    });
       
    $('#newproject_next_button').click(function(event) {
        var $cur_pane = $('#newproject_modal .modal-body > div').filter(':visible');        
        var $next_pane = $cur_pane.next();
         
        if($next_pane.length) {
            $cur_pane.hide();
            $next_pane.show();
            $('#newproject_back_button').removeAttr('disabled');
           
            if($next_pane.next().length) {
                $('#newproject_next_button').removeAttr('disabled');  
                $('#newproject_create_button').attr('disabled', 'disabled');   
            } else {
                $('#newproject_next_button').attr('disabled', 'disabled');  
                $('#newproject_create_button').removeAttr('disabled');  
            }
        }       
    });
    
    $("#newproject_info_pane input[type='text']").change(function(event) {
        console.log('change');
        
        if($('#newproject_info_name').val().trim()
        && $('#newproject_info_title').val().trim()) {
            $('#newproject_next_button').removeAttr('disabled');            
        } else {
            $('#newproject_next_button').attr('disabled', 'disabled');         
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
                .attr('disabled', 'disabled'); 
        });  
 
// ------------------------------------------------------------
// generate modal
// ------------------------------------------------------------

    $('#generate_button').click(function(event) {
        var $modal = $('#generate_modal')
            .trigger('error_hide')
            .trigger('progress_show', 'Generating project');
        
        ajax_get('/project/generate/', {},
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
      
    modal_init($('#generate_modal'))
        .on('show.bs.modal', function(event) {
            $(this).trigger('error_hide').trigger('progress_hide');
            
            $('#generate_dir').val('').focus();
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
            
            $('#run_stop_button')
                .attr('disabled', 'disabled');
            $('#run_address, #run_done_button, #run_button')
                .removeAttr('disabled');    
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
                
        var $address = $('#run_address');
        var address = $address.val().trim();
        if(!address) {
            $address.focus()
                .closest('.form-group').addClass('has-error');
            return;
        }       
        $address.closest('.form-group').removeClass('has-error');
        
        var project = $('#run_modal').data('data-project');
    
        $modal.trigger('progress_show', 'Starting preview server');
        
        ajax_get('/project/run/', 
            {
                project: project,
                address: address
            }, 
            function(error) {
                $modal.trigger('error_show', error);
            },
            function(data) {
                window.open('http://'+address);
                
                $('#run_address, #run_done_button, #run_button')
                    .attr('disabled', 'disabled');
                $('#run_stop_button')
                    .removeAttr('disabled');
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
    
    $('#run_modal, #publish_modal').on('show.bs.modal', function(event) {
        var directory = $(event.relatedTarget).closest('tr').attr('data-project');
        $(this).data('data-project', directory);      
        $('.project-name').html(directory);
    });
    
});