function progress_show(msg) {
    $('#progress_modal .modal-msg').html(msg);
    $('#progress_modal').modal('show');
}

function progress_hide() {
    $('#progress_modal').modal('hide');
}

$(function() {

    var s3_bucket_template = _.template($('#s3_bucket_template').html());
    
     
    $('#config_add_bucket').click(function(event) {
        $(this).closest('.form-group').after(s3_bucket_template());
    });
        
        
    $('#config_save').click(function(event) {
        console.log('config_save');
        progress_show('Saving configuration');
        //$('#progress_modal').modal('show');
    });
 
    $('#newproject_back_button').click(function(event) {
        var $cur_pane = $('#newproject_modal .modal-body > div').filter(':visible');
        var $prev_pane = $cur_pane.prev();
        
        if($prev_pane.length) {
            $cur_pane.hide();
            $prev_pane.show();
            $('#newproject_next_button').removeAttr('disabled');
            
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
            } else {
                $('#newproject_next_button').attr('disabled', 'disabled');  
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
 
        $("input[name='newproject_spreadsheet'][value='0']").prop('checked', true);
        $('#newproject_spreadsheet_details').hide();
        $('#newproject_spreadsheet_emails').val('{{ config.google_account }}');
        
        $("input[name='newproject_repo'][value='0']").prop('checked', true);
        $('#newproject_repo_details').hide();
        $('#newproject_repo_username, #newproject_repo_password').val('');
        
        $('#newproject_modal .modal-body > div').hide();
        $('#newproject_info_pane').show();   
        
        $('#newproject_back_button').attr('disabled', 'disabled'); 
        $('#newproject_next_button').removeAttr('disabled'); 
    });
    
});