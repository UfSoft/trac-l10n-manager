(function($){

    function replace_html(div_id, data) { $(div_id).html(data).fadeIn("fast"); };
    function insert_error(div_id) { $(div_id).append("<b>An error ocurred</b>"); };

    /*
     * Helper function to hijack the form request and make it through AJAX
     */
    $.fn.hijax_vote_form = function() {
        return this.each( function() {
            var url_array = this.action.split("/");
            var div_id = "#vote-" + url_array[url_array.length-1] + "-contents";

            jQuery(this).submit( function() {
                $(div_id).fadeOut("fast");
                $.ajax({
                    url: this.action,
                    type: 'POST',
                    cache: false,
                    error: function() { insert_error(div_id) },
                    success: function(data) { replace_html(div_id, data) },
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

    /*
     * Helper function to hijack the link request and make it through AJAX
     */
    $.fn.hijax_vote_link = function() {
        return this.each( function() {
            var url_array = this.href.split("/");
            var div_id = "#vote-" + url_array[url_array.length-1] + "-contents";

            jQuery(this).click( function() {
                $(div_id).fadeOut("fast");
                $.ajax({
                    url: this.href,
                    type: 'POST',
                    cache: false,
                    error: function() { insert_error(div_id) },
                    success: function(data) { replace_html(div_id, data) },
                });
                // Don't send request twice, first was by the ajax call
                return false;
            });
        });
    };

})(jQuery);
