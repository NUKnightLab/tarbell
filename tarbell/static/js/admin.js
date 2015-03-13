var _s3_bucket_template = _.template($('#s3_bucket_template').html());
var _select_bucket_template = _.template($('#select_bucket_template').html());
var _error_alert_template = _.template($('#error_alert_template').html());


function debug() {
    if(console && console.log) {
        // converts arguments to real array
        var args = Array.prototype.slice.call(arguments);
        args.unshift('**');
        console.log.apply(console, args); // call the function
    }
}

function error_hide() {
    var $tab = $('div.tab-pane').find('div[role="alert"]').remove();   
}

function error_alert(message) {
    error_hide();
    $('div.tab-pane.active').prepend(_error_alert_template({message: message}));    
}


function noop() {}
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
            } else {
                on_success(data);
            }
        },
        complete: function() {
            on_complete(_error);
        }
    });
}

function ajax_get(url, data, on_error, on_success, on_complete) {
    _ajax(url, 'GET', data, on_error, on_success || noop, on_complete || noop);
}

function ajax_post(url, data, on_error, on_success, on_complete) {
    _ajax(url, 'POST', data, on_error, on_success || noop, on_complete || noop);
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

//
// project
//

$(function() {
    // Clear error alerts as we switch from tab to tab
    $('a[data-toggle="tab"]').on('hide.bs.tab', function(event) {
        error_hide();
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
// projects tab
// ------------------------------------------------------------
    $('.project-details').click(function(event) {
        console.log('details');    
    });
    
    $('.project-update').click(function(event) {
        console.log('update');    
    });
    
    $('.project-generate').click(function(event) {
        console.log('generate');    
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
    
    $('#newproject_modal').on('show.bs.modal', function(event) {
        $('#newproject_info_name, #newproject_info_title').val('');
 
        $("input[name='newproject_spreadsheet'][value='']").prop('checked', true);
        $('#newproject_spreadsheet_details').hide();
        $('#newproject_spreadsheet_emails').val(config.google_account);
        
        $("input[name='newproject_repo'][value='']").prop('checked', true);
        $('#newproject_repo_details').hide();
        $('#newproject_repo_username, #newproject_repo_password').val('');
        
        $('#newproject_modal .modal-body > div').hide();
        $('#newproject_info_pane').show();   
        
        $('#newproject_back_button').attr('disabled', 'disabled'); 
        $('#newproject_next_button').removeAttr('disabled'); 
    });  
    
// ------------------------------------------------------------
// unpublish/publish modal
// ------------------------------------------------------------
 
    $('#unpublish_modal').on('show.bs.modal', function(event) {
        var html = '';
        for(key in config.default_s3_buckets) {
            html += _select_bucket_template({
                name: key, 
                bucket: config.default_s3_buckets[key]
            });
        }
        $('#unpublish_bucket').html(html).val('staging');
    });

   
    $('#publish_modal').on('show.bs.modal', function(event) {
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
// runproject modal
// ------------------------------------------------------------

    /*
    $('.project-run').click(function(event) {
        console.log('project run');
        var $parent = $(this).closest('td');
        console.log($parent);
        var project = $parent.attr('data-project');
        console.log(project);
        
        ajax_get('/project/run/'+project, {}, 
            function(error) {
                error_alert(error);
            },
            function(data) {
                window.open("http://127.0.0.1:5000");
                
                $parent.find('.project-run').hide();
                $parent.find('.project-stop').show();
            }
        );
    });
    
    $('.project-stop').click(function(event) {
        console.log('project stop');
        var $parent = $(this).closest('td');
        
        var project = $parent.attr('data-project');
        console.log(project);
        
        ajax_get('/project/stop/', {}, 
            function(error) {
                alert(error);   // temp
            },
            function(data) {
                $parent.find('.project-stop').hide();
                $parent.find('.project-run').show();
            }
        );
    });
    */

    $('#runproject_modal').on('reset', function(event) {
        $('#runproject_stop_button')
            .attr('disabled', 'disabled');
        $('#runproject_address, #runproject_done_button, #runproject_run_button')
            .removeAttr('disabled');    
    });

    $('#runproject_run_button').click(function(event) {
        var $address = $('#runproject_address');
        var address = $address.val().trim();
        if(!address) {
            $address.focus()
                .closest('.form-group').addClass('has-error');
            return;
        }
        
        $address.closest('.form-group').removeClass('has-error');
        
        $('#runproject_address, #runproject_done_button, #runproject_run_button')
            .attr('disabled', 'disabled');
        $('#runproject_stop_button')
            .removeAttr('disabled');
    });
    
    $('#runproject_stop_button').click(function(event) {
        $('#runproject_modal').trigger('reset');
    });
     
    $('#runproject_modal').on('show.bs.modal', function(event) {
        $('#runproject_address').val('127.0.0.1:5000')
            .closest('.form-group').removeClass('has-error');

        $(this).trigger('reset');
    });  
});