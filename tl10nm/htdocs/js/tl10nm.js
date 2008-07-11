(function($){

    /*
     * Helper function to hijack the link request and make it through AJAX
     */
    $.fn.hijax_link_request = function(oe) {
        return this.each( function() {

            var output_element = oe || "#contents-" + $(this).attr('tid');

            jQuery(this).click( function() {
                $(output_element).fadeOut("fast");
                $.ajax({
                    url: this.href,
                    type: 'POST',
                    cache: false,
                    error: function() {
                        $(output_element).append("<em>An error ocurred</em>")
                    },
                    success: function(data) {
                        $(output_element).html(data).fadeIn("fast");
                    }
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

})(jQuery);
