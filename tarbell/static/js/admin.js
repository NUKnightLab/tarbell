function progress_show(msg) {
    $('#progress_modal .modal-msg').html(msg);
    $('#progress_modal').modal('show');
}

function progress_hide() {
    $('#progress_modal').modal('hide');
}

function confirm_show(msg, callback) {
    $('#confirm_modal .modal-msg').html(msg);
    $('#confirm_modal .btn-primary').one('click.confirm', function(event) {
        $('#confirm_modal').modal('hide');
        if(callback) {
            callback();
        }
    });
    $('#confirm_modal').modal('show');
}

function config_disable_bucket(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').attr('disabled', 'disabled');
    $group.find('.config-remove-bucket').hide();
    $group.find('.config-add-bucket').show();
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
    var s3_bucket_template = _.template($('#s3_bucket_template').html());
    
    //
    // config
    //
    
    $('#config_add_bucket').click(function(event) {
        $(this).closest('.form-group').after(s3_bucket_template());
    });
               
    $('#config_save').click(function(event) {
        // fakin in
        progress_show('Saving configuration');
    });
 
    //
    // project
    //
    
    $('.project-preview').click(function(event) {
        console.log('generate');    
    });
    
    $('.project-update').click(function(event) {
        console.log('update');    
    });
    
    $('.project-generate').click(function(event) {
        console.log('generate');    
    });

    $('.project-publish').click(function(event) {
        console.log('publish');    
    });
     
    $('.project-unpublish').click(function(event) {
        console.log('unpublish');    
    });

 
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
        console.log('newproject_spreadsheet', $(this).val());
        
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
});