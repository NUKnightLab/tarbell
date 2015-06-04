// admin.js, admin GUI functions
// required jquery, json2

//
// templates
//

var _error_alert_template = _.template($('#error_alert_template').html());
var _success_alert_template = _.template($('#success_alert_template').html());

var _google_msg_template = _.template($('#google_msg_template').html());

var _edit_bucket_template = _.template($('#edit_bucket_template').html());
var _add_bucket_template = _.template($('#add_bucket_template').html());

var _project_template = _.template($('#project_template').html());

var _select_blueprint_template = _.template($('#select_blueprint_template').html());


//
// progress modal
//

function progress_show(msg) {
    $('#progress_modal .modal-msg').html(msg);
    $('#progress_modal').modal('show');
}

function progress_hide() {
    $('#progress_modal').modal('hide');
}

//
// input modal
//

function input_show(msg, callback) {
    var $input = $('#input_modal').find('input[type="text"]');
    
    var $input_modal = $('#input_modal')
        .on('show.bs.modal', function(event) {
            $input_modal.find('.modal-msg').html(msg);   
            $input.val('');       
        })
        .on('click', '.btn-default', function(event) {
            $input_modal.modal('hide');
            callback(false);
        })
        .on('click', '.btn-primary', function(event) {
            var value = $input.trimmed();
            if(!value) {
                $input.focus()
                    .closest('.form-group').addClass('has-error');
                return;
            }
 
            $input_modal.modal('hide');
            callback(true, value);       
        });
        
    $input_modal.modal('show');
}

function input_hide() {
    $('#input_modal').modal('hide');
}

//
// alerts
//

function alert_hide() {
    $('div.tab-pane').find('div[role="alert"].alert-danger, div[role="alert"].alert-success').remove(); 
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
// projects
//

function show_projects() {
    ajax_get('/projects/list/', {},
        function(error) {
            $('#projects_alert').hide();
            $('#projects_table').hide();
            error_alert('Error listing projects ('+error+')');
        },
        function(data) {    
            var projects = data.projects;    
            var html = '';
    
            for(var i = 0; i < projects.length; i++) {
                html += _project_template({d: projects[i]});
            }    
            if(projects.length) {
                $('#projects_alert').hide();
                $('#projects_table tbody').html(html);
                $('#projects_table').show();
            } else {
                $('#projects_alert').show();
                $('#projects_table').hide();        
            }
        });
}


//
// settings
//

function settings_dirty() {
    $('#settings_save').enable();
}

// Disable row of S3 bucket controls
function bucket_disable(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').disable();
    $group.find('.bucket-disable').hide();
    $group.find('.bucket-enable').show();
    $group.addClass('disabled');
    settings_dirty();
}

// Enable row of S3 bucket controls
function bucket_enable(target) {
    var $group = $(target).closest('.form-group');
    $group.find('input').enable();
    $group.find('.bucket-enable').hide();
    $group.find('.bucket-disable').show();
    $group.removeClass('disabled');
}

// Remove set of S3 bucket controls
function bucket_remove(target) {
    $(target).closest('.form-group').remove();
}

// Add set of S3 bucket controls
function bucket_add(target, data, tmpl) {
    var d = $.extend(
        {name: '', access_key_id: '', secret_access_key: ''},
        data || {}
    );
    var $group = $(target).closest('.form-group');  
    var tmpl = tmpl || _add_bucket_template;
    $(tmpl(d)).insertBefore($group);
}


// Get and validate S3 defaults
function get_s3_defaults(cfg) {
    var key = $('#default_s3_access_key_id').trimmed();
    var secret = $('#default_s3_secret_access_key').trimmed();
    var staging = $('#default_s3_buckets_staging').trimmed();
    var production = $('#default_s3_buckets_production').trimmed();
    
    if(!(key && secret) && (staging || production)) {
        return 'You must enter keys to specify default staging and production buckets';
    }
    
    $.extend(cfg, {
        default_s3_access_key_id: key,
        default_s3_secret_access_key: secret,
        default_s3_buckets: {
            staging: staging,
            production: production
        }
    });
}

// Get and validate S3 credentials
function get_s3_credentials(cfg) {
    var error = '';
    var data = {};
    var has_defaults = cfg.default_s3_access_key_id && cfg.default_s3_secret_access_key;

    $('#s3').find('.bucket-group').not('.disabled').each(function(i, el) {    
        var $el = $(el);
        var url = $el.find('.bucket-url').trimmed();
        var key = $el.find('.bucket-key').trimmed(); 
        var secret = $el.find('.bucket-secret').trimmed(); 
        
        if(url) {
            if(key && secret) {         // entered both
                data[url] = {
                    access_key_id: key,
                    secret_access_key: secret
                };             
            } else if(key || secret) {  // entered only one
                if(has_defaults) {
                    error = 'You must enter an access key ID and a secret access key for each bucket (or leave both blank to use defaults)';
                } else {
                    error = 'You must enter an access key ID and a secret access key for each bucket';                
                }
            } else {                    // entered neither
                if(has_defaults) {  
                    data[url] = {
                        access_key_id: settings.default_s3_access_key_id,
                        secret_access_key: settings.default_s3_secret_access_key
                    };              
                } else {
                    error = 'You must enter an access key ID and a secret access key for each bucket';
                }
            }
        } else if(key || secret) {
            error = 'You must enter a name for each S3 bucket';
        }
        if(error) {
            return false;
        }
    });     
    
    if(error) {
        return error;
    }
    
    $.extend(cfg.s3_credentials, data);
}

//
// Initialize controls in settings tab
//

function show_s3_credentials() {
    $('#s3_credentials').find('.bucket-group').remove();
    
    var $el = $('#s3_credentials').find('.bucket-add');
    for(var name in _config.s3_credentials) {
        bucket_add($el, $.extend({name: name}, _config.s3_credentials[name]), _edit_bucket_template);
    }
    if(!Object.keys(_config.s3_credentials).length) {
        $el.click();
    }  
}

function show_settings() {     
    // Use Google?   
    if(_settings.client_secrets) {
        $('#use_google').prop('checked', true);
        $('#google').addClass('in');
        $('.google-secrets-exists').show();
        $('#google_authenticate').enable();
    
    } else {
        $('#use_google').prop('checked', false);
        $('#google').removeClass('in');
        $('.google-secrets-exists').hide();
        $('#google_authenticate').disable();
    }
    
    // Google Emails
    $('#google_emails').enable().val(_config.google_account || '');
           
    // Use S3?
    if(_config.default_s3_access_key_id || _config.default_s3_secret_access_key) {
        $('#use_s3').prop('checked', true);
        $('#s3').addClass('in');    
    } else {
        $('#use_s3').prop('checked', false);
        $('#s3').removeClass('in');
    } 

    // S3 defaults
    $('#default_s3_access_key_id').val(_config.default_s3_access_key_id || '');
    $('#default_s3_secret_access_key').val(_config.default_s3_secret_access_key || '');
    $('#default_s3_buckets_staging').val(_config.default_s3_buckets.staging || '');
    $('#default_s3_buckets_production').val(_config.default_s3_buckets.production || '');
    
    // Additional S3 credentials
    show_s3_credentials(); 

    // Projects path
    $('#projects_path').val(_config.projects_path);
}

// Verify authorization code
function handle_google_auth_code($context, code) {
    $context.trigger('progress_show', 'Verifying code');
      
    ajax_get('/google/auth/code/', {code: code},
        function(error) {
            $context.trigger('error_show', error);
        },
        function(data) {
            $context.trigger('success_show', 'Authentication successful');               
        },
        function() {
            $context.trigger('progress_hide');
        });  
}

// Handle new client_secrets file selection
function handle_google_auth_secrets($context, file) {
     if(file) {
        var reader = new FileReader();
        
        reader.onerror = function() {
            $context.trigger('error_show', 'Error loading file');
        };
       
        reader.onload = function() {
            $context.trigger('progress_show', 'Copying file');
        
            ajax_post('/google/auth/secrets/', {content: reader.result},
                function(error) {
                    $context.trigger('error_show', 'Error copying file ('+error+')');
                },
                function(data) {
                    _settings = data.settings;
                    _config = _settings.config;
                    $('#google_authenticate, #google_emails').enable();
                },
                function() {
                    $context.trigger('progress_hide');
                });                
        };

        $context.trigger('progress_show', 'Loading file');
        reader.readAsDataURL(file);  
    }
}


$(function() {
        
    // Clear alerts/states when switching from tab to tab
    $('a[data-toggle="tab"]').on('hide.bs.tab', function(event) {      
        alert_hide();
        $('.form-group, .input-group').removeClass('has-error');        
    });
   
// ------------------------------------------------------------
// settings tab
// ------------------------------------------------------------
     
    var $settings_tab = $('#settings_tab')
        // mimic modal functions so we can re-use core routines
        .on('error_hide', error_hide)
        .on('error_show', function(event, msg) { 
            error_alert(msg); 
        })
        .on('progress_hide', progress_hide)
        .on('progress_show', function(event, msg) {
            progress_show(msg);
        })  
        .on('success_show', function(event, msg) {
            success_alert(msg);
        })
        .on('change', 'input[type="text"]', settings_dirty)
        .on('click', 'input[type="checkbox"]', settings_dirty)
        .on('change', '#google_secrets_file', function(event) {
            handle_google_auth_secrets($settings_tab, event.target.files[0]);
        })
        .on('click', '#google_authenticate', function(event) {
            ajax_get('/google/auth/url/', {},
                function(error) {
                    error_alert(error);
                },
                function(data) {
                    input_show(_google_msg_template(data), function(yes, code) {
                        if(yes) {
                            handle_google_auth_code($settings_tab, code);
                        }
                    });
                });                    
        });

    // Save settings
    $('#settings_save').click(function(event) {  
        var error = null;   
        var data = $.extend(true, {}, _defaults);

        if($('#use_google').is(':checked')) {
            data.google_account = $('#google_emails').trimmed();
        }
        
        if($('#use_s3').is(':checked')) {        
            error = get_s3_defaults(data) || get_s3_credentials(data);               
            if(error) {
                error_alert(error);
                return;
            }
        }
        
        data.projects_path = $('#projects_path').val();
                                     
        progress_show('Saving configuration');
         
        ajax_post('/config/save/', {
                config: JSON.stringify(data)
            },
            function(error) {
                error_alert('Error saving settings ('+error+')');
            },
            function(unused) {
                _settings.config = data;
                _config = _settings.config;
                                
                $('#settings_save').disable()
                success_alert('Settings saved!');
                
                show_s3_credentials();
            },
            function() {
                progress_hide();
            });
    });

// ------------------------------------------------------------
// new modal
// ------------------------------------------------------------

    var $new_modal = modal_init($('#new_modal'))
        .on('show.bs.modal', function(event) {
            $new_modal
                .trigger('all_hide')
                .find('.form-group').removeClass('has-error');
            
            $('#new_name, #new_title').val("");
            $('#new_emails').val(_config.google_account);
            
            var html = '';            
            for(var i = 0; i < _config.project_templates.length; i++) {
                html += _select_blueprint_template({d: _config.project_templates[i]});
            }
            $('#new_blueprint').html(html);
            
            $new_modal.find('.new-project').show();
            $new_modal.find('.new-spreadsheet').hide();
        })
        .on('hide.bs.modal', function(event) {
            show_projects();
        })
        .on('change', '#new_name, #new_title', function(event) {
            if($(this).val().trim()) {
                $(this).closest('.form-group').removeClass('has-error'); 
            }
        })
        .on('click', '#new_project_button', function(event) {        
            $new_modal.trigger('all_hide');
            
            var name = $('#new_name').val().trim();
            if(!name) {
                $('#new_name').closest('.form-group').addClass('has-error');
            }
            
            var title = $('#new_title').val().trim();
            if(!title) {
                $('#new_title').closest('.form-group').addClass('has-error');
            }
            
            if(!(name && title)) {
                return;
            }

            $new_modal.trigger('progress_show', 'Creating project');
            
            ajax_get('/project/create/', {
                    name: name,
                    title: title,
                    blueprint: $('#new_blueprint').val()
                },
                function(error) {
                    $new_modal.trigger('error_show', error);
                },
                function(data) {
                    if(data.spreadsheet) {
                        $new_modal.find('.new-project').hide();
                        $new_modal.find('.new-spreadsheet').show();  
                    } else {
                        $new_modal.modal('hide');
                    }   
                },
                function() {
                    $new_modal.trigger('progress_hide');
                });
        })
        .on('click', '#new_spreadsheet_button', function(event) {
            $new_modal.trigger('progress_show', 'Creating spreadsheet');
            
            ajax_get('/spreadsheet/create/', {
                    name: $('#new_name').val().trim(),
                    emails: $('#new_emails').val().trim()
                },
                function(error) {
                    $new_modal.trigger('error_show', error);
                },
                function(data) {
                    $new_modal.modal('hide');
                },
                function() {
                    $new_modal.trigger('progress_hide');           
                });      
        });

// ------------------------------------------------------------
// run modal
// ------------------------------------------------------------

    var $run_modal = modal_init($('#run_modal'))
        .on('show.bs.modal', function(event) {
            $run_modal.trigger('all_hide');
            
            $(this).data('data-project', 
                $(event.relatedTarget).closest('tr').attr('data-project'));  
            
            $('#run_address').val('127.0.0.1:5000').enable();
            $('#run_done_button, #run_button').show();              
            $('#run_stop_button').hide();
        })
        .on('click', '#run_button', function(event) {   
            $run_modal.trigger('all_hide');
            
            var project = $run_modal.data('data-project');
           
            var $address = $('#run_address');
            var address = $address.val().trim();
            if(!address) {
                $address.focus().closest('.form-group').addClass('has-error');
                return;
            }
            $address.closest('.form-group').removeClass('has-error');
            
            $run_modal.trigger('progress_show', 'Starting preview server');
    
            ajax_get('/project/run/', {
                    project: project,
                    address: address
                }, 
                function(error) {
                    $run_modal.trigger('error_show', error);
                },
                function(data) {
                    if(data.warning) {
                        $run_modal.trigger('error_show', data.warning);
                    }
                    window.open('http://'+address);
            
                    $('#run_address').disable();
                    $('#run_done_button, #run_button').hide();   
                },
                function() {
                    $run_modal.trigger('progress_hide');
                }
            );
        }); 
           
// ------------------------------------------------------------
// Main
// ------------------------------------------------------------

    show_settings();
    
    if(_settings.file_missing) {
        $('#tab_list a[href="#settings_tab"]').tab('show')
    } else {
        show_projects();
        $('#tab_list a[href="#projects_tab"]').tab('show')
    }
    $('#tab_content').show();
    
});