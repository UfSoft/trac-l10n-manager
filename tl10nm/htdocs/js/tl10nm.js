(function($){

    /*
     * Helper function to hijack the link request and make it through AJAX
     */
    $.fn.hijaxLinkRequest = function(params) {

        var options = {
            progress: false,
            output: null
        };

        var loading_element = '<div class="progress">&nbsp;</div>';

        var params = params || {};
        var op = $.extend(options, params);
        var messages = $.extend({}, $.fn.hijaxLinkRequest.messages, params.messages)

        return this.each( function() {
            // Make sure elements are hijax'ed only once
            if ( $.data(this, 'hijaxed') ) { return /* break out of each loop */ };
            // Mark element as hijaxed
            $.data(this, 'hijaxed', true);

            var output_element = op.output || findOutputDivParent(this);

            jQuery(this).bind("click", function() {
                $.removeData(this); // Clear this element out of jQ's data cache
                $(output_element).animate(
                   {opacity: 0.0},
                   { queue: false, speed: "fast" }
                );
                if ( op.progress ) { $.blockUI({ message: loading_element }); };
                $.ajax({
                    async: true,
                    url: this.href,
                    type: 'GET',
                    cache: false,
                    error: function() {
                        if ( op.progress ) { $.unblockUI(); };
                        $(output_element).append("<em>"+ messages.ajaxError +"</em>")
                    },
                    success: function(data) {
                        if ( op.progress ) { $.unblockUI(); };
                        $(output_element).html(data).animate(
                            { opacity: 1.0 },
                            { queue: false, speed: "fast" }
                        );
                    },
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

    $.fn.hijaxLinkRequest.messages = {
        ajaxError: "An error ocurred",
    };

    function findOutputDivParent(elem) {
        var parent_output_div = elem;
        while ( $(parent_output_div).get(0).tagName != 'DIV' ) {
            parent_output_div = $(parent_output_div).parent().get(0);
        };
        return parent_output_div;
    };

})(jQuery);
