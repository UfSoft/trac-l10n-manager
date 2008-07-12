(function($){

    var loading_element = '<h1 class="loading">Just a moment...</h1>';

    /*
     * Helper function to hijack the link request and make it through AJAX
     */
    $.fn.hijax_link_request = function(oe) {
        return this.each( function() {

            var output_element = oe || "#contents-" + $(this).attr('tid');

            jQuery(this).click( function() {
                $.blockUI({ message: loading_element });
                $(output_element).fadeOut("fast");
                $.ajax({
                    url: this.href,
                    type: 'POST',
                    cache: false,
                    error: function() {
                        $.unblockUI();
                        $(output_element).append("<em>An error ocurred</em>")
                    },
                    success: function(data) {
                        $.unblockUI();
                        $(output_element).html(data).fadeIn("fast");
                    }
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

})(jQuery);
