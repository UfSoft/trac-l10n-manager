(function($){

    var loading_element = '<div class="progress">&nbsp;</div>';

    /*
     * Helper function to hijack the link request and make it through AJAX
     */
    $.fn.hijax_link_request = function(params) {

        var options = {
            progress: false,
            output: null
        };

        op = $.extend(options, params);

        return this.each( function() {

            var output_element = op.output || "#contents-" + $(this).attr('tid');

            jQuery(this).click( function() {
                $(output_element).fadeOut("fast");
                if ( op.progress ) { $.blockUI({ message: loading_element }); };
                $.ajax({
                    url: this.href,
                    type: 'POST',
                    cache: false,
                    error: function() {
                        if ( op.progress ) { $.unblockUI(); };
                        $(output_element).append("<em>An error ocurred</em>")
                    },
                    success: function(data) {
                        if ( op.progress ) { $.unblockUI(); };
                        $(output_element).html(data).fadeIn("fast");
                    }
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

})(jQuery);
